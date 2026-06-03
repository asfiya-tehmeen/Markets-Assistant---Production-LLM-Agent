# Markets Assistant

A production-grade, tool-using LLM agent that answers finance/markets questions — built to
demonstrate the reliability engineering (caching, tracing, evaluation, deployment) that makes such
an agent trustworthy at scale. The agent grounds every answer in tool output and **escalates
instead of guessing** when it can't.

## Architecture (planned)

A [LangGraph](https://langchain-ai.github.io/langgraph/) agent receives a question, routes to one
or more tools, then synthesises a structured, grounded answer:

```json
{ "answer": "...", "sources": ["..."], "confidence": "high|medium|low", "verdict": "ANSWERED|NEEDS_HUMAN" }
```

**Tools**
1. `search_knowledge_base(query)` — RAG over seed finance/markets docs in ChromaDB.
2. `get_price(symbol)` — current crypto price from CoinGecko, cached in Redis.
3. `calculate(...)` — deterministic P/L, position size, conversions (no LLM).

**Stack:** Python 3.11 · FastAPI · LangGraph · Anthropic SDK · ChromaDB · Redis · PostgreSQL ·
LangFuse · React/TypeScript/Vite · Docker · GitHub Actions.

## Build status

- [x] **Phase 0** — Repo skeleton + `/health`.
- [x] **Phase 1** — Core agent (tools + LangGraph + `POST /ask`).
- [x] **Phase 2** — Redis cache + rate limit, PostgreSQL persistence, optional LangFuse, Docker.
- [ ] Phase 3 — Evaluation harness + CI gate.
- [ ] Phase 4 — React/TypeScript frontend.
- [ ] Phase 5 — Polish, tests, docs.

## Running (Phase 0)

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
# -> http://localhost:8000/health  ->  {"status":"ok"}
```

Copy `.env.example` to `.env` and fill in secrets as later phases need them.
