"""search_knowledge_base tool — RAG over seed docs stored in a local, persisted ChromaDB.

Uses ChromaDB's default embedding function (ONNX all-MiniLM-L6-v2), so retrieval is fully
local with no embedding API. The collection is seeded once on first use.
"""
from __future__ import annotations

import chromadb

from app.config import get_settings
from app.tools.seed_docs import SEED_DOCS

_COLLECTION_NAME = "markets_kb"
_collection = None  # lazily initialised singleton


def _get_collection():
    """Return the seeded ChromaDB collection, creating + populating it on first call."""
    global _collection
    if _collection is not None:
        return _collection

    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    # Cosine space so similarity = 1 - distance maps cleanly to a 0..1 relevance score.
    collection = client.get_or_create_collection(
        _COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    if collection.count() == 0:
        collection.add(
            ids=[d["id"] for d in SEED_DOCS],
            documents=[d["text"] for d in SEED_DOCS],
            metadatas=[{"title": d["title"], "category": d["category"]} for d in SEED_DOCS],
        )
    _collection = collection
    return _collection


def search_knowledge_base(query: str, n_results: int = 3) -> dict:
    """Semantic search over the finance/markets knowledge base.

    Args:
        query: Natural-language search query.
        n_results: Number of chunks to return (default 3).

    Returns:
        ``{"ok": True, "results": [...], "best_similarity": float, "weak": bool}`` where
        ``weak`` is True when even the top match is below the configured relevance threshold
        (a signal the agent uses to escalate rather than guess).
    """
    try:
        collection = _get_collection()
        n = max(1, min(int(n_results), 10))
        res = collection.query(query_texts=[query], n_results=n)
    except Exception as exc:
        return {"ok": False, "error": f"knowledge base query failed: {exc}", "results": [],
                "best_similarity": 0.0, "weak": True}

    docs = res["documents"][0]
    dists = res["distances"][0]
    metas = res["metadatas"][0]
    ids = res["ids"][0]

    results = []
    for doc_id, doc, dist, meta in zip(ids, docs, dists, metas):
        similarity = 1.0 - float(dist)  # cosine distance -> similarity
        results.append({
            "id": doc_id,
            "title": meta.get("title", doc_id),
            "category": meta.get("category", ""),
            "text": doc,
            "similarity": round(similarity, 3),
        })

    best = max((r["similarity"] for r in results), default=0.0)
    threshold = get_settings().kb_relevance_threshold
    return {"ok": True, "query": query, "results": results,
            "best_similarity": round(best, 3), "weak": best < threshold}
