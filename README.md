# Markets Assistant

A production-grade, tool-using LLM agent that answers finance and markets questions over a
retrieval knowledge base and **live market data** — with citations, a confidence signal, and an
explicit *"escalate to a human"* path when it isn't sure. Built less as a demo and more as an
exercise in the **last mile**: caching, tracing, evaluation, and deployment that make an agent
trustworthy when it runs thousands of times, not just once.

> Getting an AI to work once is luck. Getting it to work reliably is engineering. This repo is
> about the engineering.

---

## Why this exists

A single prompt can look like magic and still be useless in production: it hallucinates, it's
slow, it has no record of what it did, and nobody can tell whether a change made it better or
worse. Markets Assistant is a small, honest slice of a real customer-facing AI system that takes
those problems seriously:

- **Grounding over guessing** — answers are built from retrieved sources and live data, and the
  agent says *I don't know — escalate* rather than inventing an answer when evidence is thin.
- **Observability** — every run is traced (tools called, latency, token cost) so behaviour is
  inspectable, not a black box.
- **Evaluation as a gate** — a golden test set runs in CI and fails the build if quality drops,
  the same way you'd test any other piece of software.

---

## What it does

Ask it things like:

- *"What's the current price of Bitcoin in USD?"* → calls the live price tool, returns the figure
  with a timestamp.
- *"What does 'leverage' mean and what are the risks?"* → retrieves from the knowledge base,
  answers with citations.
- *"If I buy 0.5 ETH at $3,000 and it rises 8%, what's my profit?"* → routes to the calculation
  tool and shows the working.
- *"Should I put my savings into this coin?"* → recognises this is advice it must not give, and
  returns a `NEEDS_HUMAN` response instead of guessing.

---

## Architecture

```
                         ┌──────────────────────────────┐
   React + TypeScript ──▶│        FastAPI  /ask          │
        chat UI          └──────────────┬───────────────┘
                                        │
                              ┌─────────▼──────────┐
                              │   LangGraph agent  │   ← routes to the right tool(s),
                              │  (router + synth)  │     synthesises a grounded answer
                              └───┬─────┬──────┬───┘
                                  │     │      │
                  ┌───────────────┘     │      └───────────────┐
                  ▼                     ▼                      ▼
        search_knowledge_base     get_price(symbol)       calculate(...)
        (RAG over ChromaDB)      (CoinGecko, cached)     (P/L, position size)
                  │                     │                      │
                  └─────────────────────┴──────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
        PostgreSQL                    Redis                    LangFuse
   (request + result log)     (price + answer cache,      (tracing: latency,
                                  rate limiting)            cost, tool calls)
```

Every response carries a structured payload:

```json
{
  "answer": "Bitcoin is currently trading at ~$X (as of <timestamp>).",
  "sources": ["coingecko:bitcoin", "kb:glossary#leverage"],
  "confidence": "high",
  "verdict": "ANSWERED"
}
```

`verdict` is one of `ANSWERED` or `NEEDS_HUMAN`. The agent returns `NEEDS_HUMAN` when retrieval
is weak, the question is out of scope, or it would otherwise require giving regulated financial
advice.

---

## Tech stack

| Layer            | Choice                                        |
|------------------|-----------------------------------------------|
| Language         | Python 3.11 (backend), TypeScript (frontend)  |
| Agent framework  | LangGraph                                     |
| LLM              | Anthropic / OpenAI API (model set via env)    |
| Retrieval        | ChromaDB (local vector store)                 |
| API              | FastAPI                                        |
| Market data      | CoinGecko Demo API (free)                      |
| Cache / limiting | Redis                                          |
| Persistence      | PostgreSQL                                     |
| Observability    | LangFuse (self-hosted or free Hobby cloud)     |
| Frontend         | React + TypeScript + Vite                      |
| Packaging        | Docker + docker-compose                        |
| CI / eval gate   | GitHub Actions                                 |

---

## Project structure

```
markets-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, /ask endpoint
│   │   ├── agent/             # LangGraph graph + nodes
│   │   ├── tools/             # knowledge_base, price, calculate
│   │   ├── cache.py           # Redis helpers
│   │   ├── db.py              # Postgres logging
│   │   └── observability.py   # LangFuse setup
│   ├── data/                  # knowledge base documents
│   ├── tests/
│   └── Dockerfile
├── eval/
│   ├── golden_set.jsonl       # questions + expected behaviour
│   └── run_eval.py            # scores correctness + groundedness
├── frontend/                  # React + TS chat UI
├── docker-compose.yml         # api + postgres + redis (+ optional langfuse)
└── .github/workflows/eval.yml # runs the eval gate on every push
```

---

## Getting started

### Prerequisites
- Docker and Docker Compose
- An LLM API key (Anthropic or OpenAI). New Anthropic accounts get ~$5 free credit; students can
  apply for more. Use a cheap model (e.g. Haiku) to keep cost negligible.
- A free CoinGecko Demo API key (optional — the public endpoint works keyless at a lower rate
  limit).

### 1. Configure environment
Copy the example and fill in your keys:

```bash
cp .env.example .env
```

```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-4-5-20251001     # cheapest; swap for claude-sonnet-4-6 if needed
COINGECKO_API_KEY=                       # optional
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com # or your self-hosted URL
POSTGRES_URL=postgresql://app:app@postgres:5432/markets
REDIS_URL=redis://redis:6379/0
```

### 2. Run everything
```bash
docker compose up --build
```

API comes up at `http://localhost:8000`, the frontend at `http://localhost:5173`.

### 3. Ask a question
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the current price of bitcoin?"}'
```

---

## Evaluation

The eval suite is the point, not an afterthought. It runs the agent over a hand-labelled golden
set and scores three things:

- **Correctness** — does the answer match the expected answer? (LLM-as-judge against the gold label)
- **Groundedness** — is every factual claim supported by a retrieved source or tool output?
- **Escalation** — does the agent correctly return `NEEDS_HUMAN` on the cases that warrant it?

Run it locally:

```bash
python eval/run_eval.py
```

The same script runs in CI (`.github/workflows/eval.yml`) on every push and **fails the build**
if any score falls below its threshold — turning "did my change break the agent?" into a
question the pipeline answers automatically.

---

## Observability

With LangFuse configured, every request produces a trace showing each tool call, its latency, and
token cost. This is where the production numbers come from — p50/p95 latency, cost per query, and
the distribution of which tools the agent actually reaches for.

---

## Reliability notes (a.k.a. things that broke)

> Keep a short, honest log here as you build — e.g. "the agent over-trusted stale prices, so I
> added a cache TTL and a freshness check," or "vague questions slipped past the escalation
> check until I tightened the confidence threshold." This section is often what a reviewer reads
> most closely.

---

## Roadmap

- [ ] Streaming responses
- [ ] Multi-turn conversation memory
- [ ] Forex tool alongside crypto
- [ ] A metrics dashboard reading from Postgres (queries/day, latency, escalation rate)

---

## Disclaimer

This is a portfolio/educational project. It does **not** provide financial advice and is not
connected to any brokerage or live trading. Market data is illustrative.

