# Markets Assistant

A production-grade, tool-using LLM agent that answers finance/markets questions — built to
demonstrate the reliability engineering (caching, tracing, evaluation, deployment) that makes such
an agent trustworthy at scale. The agent grounds every answer in tool output and **escalates
instead of guessing** when it can't.

## Architecture

A [LangGraph](https://langchain-ai.github.io/langgraph/) agent receives a question, routes to one
or more tools, runs them, then synthesises a structured, grounded answer. Deterministic backstops
in the synthesis step force `NEEDS_HUMAN` when there's no grounded data, when retrieval is weak, or
when the question asks for regulated/personalised advice — regardless of what the model claims.

```json
{ "answer": "...", "sources": ["..."], "confidence": "high|medium|low", "verdict": "ANSWERED|NEEDS_HUMAN" }
```

```
question ─▶ router (LLM + tool schemas) ─▶ tools ─▶ router … ─▶ synthesise ─▶ structured JSON
                                            │
              ┌─────────────────────────────┼─────────────────────────────┐
   search_knowledge_base(query)      get_price(symbol)              calculate(...)
   RAG over ChromaDB seed docs       CoinGecko, Redis-cached        deterministic, no LLM
```

**Tools**
1. `search_knowledge_base(query)` — RAG over seed finance/markets docs in ChromaDB (local ONNX
   embeddings; self-seeds on first use). Flags weak retrieval so the agent can escalate.
2. `get_price(symbol)` — current crypto price from CoinGecko, cached in Redis (fail-open).
3. `calculate(...)` — deterministic P/L, position sizing, unit↔notional conversion (no LLM).

**Request pipeline** (`POST /ask`): per-IP rate limit → identical-question cache → agent →
cache + PostgreSQL persistence → optional LangFuse trace (tool spans, latency, tokens). Every
infra dependency degrades gracefully — the endpoint never crashes if Redis/Postgres/LangFuse are
absent.

**Stack:** Python 3.11 · FastAPI · LangGraph · Groq (OpenAI-compatible SDK) · ChromaDB · Redis ·
PostgreSQL · LangFuse · React/TypeScript/Vite · nginx · Docker · GitHub Actions.

## Build status

- [x] **Phase 0** — Repo skeleton + `/health`.
- [x] **Phase 1** — Core agent (tools + LangGraph + `POST /ask`).
- [x] **Phase 2** — Redis cache + rate limit, PostgreSQL persistence, optional LangFuse, Docker.
- [x] **Phase 3** — Evaluation harness (`eval/`) + GitHub Actions CI gate.
- [x] **Phase 4** — React/TypeScript/Vite frontend, served by nginx behind Docker Compose.
- [x] **Phase 5** — Unit tests, test CI workflow, docs.

## Quick start (full stack, Docker)

```bash
cp .env.example backend/.env      # then set GROQ_API_KEY (Groq is keyless-free to sign up)
docker compose up --build
```

- **UI:** http://localhost:8080  (nginx serves the SPA and proxies `/ask`, `/health` to the API)
- **API:** http://localhost:8000  (`/health`, `POST /ask`)

The stack is `frontend` + `api` + `postgres` + `redis`. Only `GROQ_API_KEY` is required; LangFuse
keys are optional (leave blank to disable tracing).

## Running pieces individually

**Backend (dev):**
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate    # Windows (use source .venv/bin/activate on *nix)
pip install -r requirements.txt
uvicorn app.main:app --reload                      # -> http://localhost:8000
```

**Frontend (dev):** Vite proxies `/ask` and `/health` to `http://localhost:8000`.
```bash
cd frontend
npm install
npm run dev                                         # -> http://localhost:5173
```

## Tests

Hermetic backend unit suite — no secrets, no live LLM/network calls (a dummy key is injected in
`tests/conftest.py`):
```bash
cd backend && python -m pytest tests -q
```
Covers the calculator math, eval scoring, synthesis backstops (advice detection, source mapping),
and the API smoke tests (health, validation, CORS). The frontend is type-checked via `npm run build`.

## Evaluation & CI gate

`eval/golden_set.jsonl` is a labelled set spanning every path (live prices, RAG, calculator,
advice-refusal, out-of-scope, unknown-KB escalation). The harness runs each case through the real
agent and scores it with **deterministic** checks (verdict, tool selection, confidence bounds,
answer substrings, source presence) — no LLM judge, so it's reproducible.

```bash
python eval/run_eval.py                  # full set, gate threshold 0.85
python eval/run_eval.py --ids price-btc --report eval/report.json
```

Two GitHub Actions workflows:
- **`tests.yml`** — unit tests + frontend build on every push/PR (no secrets).
- **`eval.yml`** — the eval gate runs the real agent and fails below the pass-rate threshold.
  Requires a `GROQ_API_KEY` repo secret (Settings → Secrets and variables → Actions); optionally
  `COINGECKO_API_KEY`. Skips fork PRs, which can't access secrets.

## Configuration

Copy `.env.example` to `backend/.env`. Key variables: `GROQ_API_KEY` (required), `LLM_MODEL`,
`KB_RELEVANCE_THRESHOLD`, `RATE_LIMIT_PER_MINUTE`, `CORS_ALLOW_ORIGINS`, optional `LANGFUSE_*`.

> Educational information only — not financial advice. The agent deliberately refuses buy/sell
> recommendations and price predictions.
