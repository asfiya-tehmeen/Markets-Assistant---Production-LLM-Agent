# Demo Guide — Markets Assistant

A step-by-step script for running the project live (e.g. in an interview) and the talking points
that show off the engineering behind it.

---

## 0. One-time prerequisites

- **Docker Desktop** installed and running.
- **`backend/.env`** exists with a valid `GROQ_API_KEY` (the only required secret).
  Copy `.env.example` → `backend/.env` and fill it in if needed.
- Internet access (the agent calls Groq for the LLM and CoinGecko for prices).

---

## 1. Start everything (one command)

```powershell
cd C:\Users\exube\OneDrive\Desktop\markets-assistant
docker compose up --build -d        # -d runs it in the background
```

First build takes ~2–3 min; subsequent starts ~10 sec. This brings up four services:
`frontend` + `api` + `postgres` + `redis`.

**Open the UI → http://localhost:8080**

Stop later with:
```powershell
docker compose down                 # add -v to also wipe the database volume
```

---

## 2. Pre-flight check (do this right before presenting)

```powershell
curl http://localhost:8000/health
# -> {"status":"ok"}
```

Then **ask one throwaway question in the UI to warm it up** — the first request after startup is
the slowest (model + vector store are cold). The live demo question will then be snappy.

Have these windows ready:
- The **UI** (http://localhost:8080)
- The **GitHub repo** + this README
- *Optional:* the **LangFuse dashboard** (https://cloud.langfuse.com) to show live traces

---

## 3. The 30-second opener

> "Markets Assistant is a tool-using LLM agent for finance questions. The interesting part isn't
> that it answers — it's the reliability engineering around it: every answer is grounded in tool
> output, it escalates instead of guessing on things like investment advice, and it's wrapped in
> caching, tracing, a deterministic eval gate in CI, and a full Docker deployment."

---

## 4. The demo flow

Use the four example chips on the page — each one showcases a different capability. Click them in
this order and narrate:

### a) "What is the current price of Bitcoin?"  → live tools + caching
- Routes to the `get_price` tool (CoinGecko), cached in Redis.
- **Ask it a second time** → the answer comes back with a **`cached`** badge and lower latency.
- Say: *"Live tool call, then served from a Redis cache on repeat — note the latency drop."*

### b) "Explain impermanent loss in DeFi."  → RAG / grounding
- Hits a ChromaDB vector search over a seeded finance knowledge base.
- Point at the **Sources** list under the answer.
- Say: *"Every answer is grounded in retrieved docs, not the model's memory. The sources are cited."*

### c) "If I went long 0.5 BTC at $30000 and sold at $35000, what's my profit?"  → deterministic math
- Math goes to a deterministic `calculate` tool, not the LLM.
- Say: *"Financial math is never left to the model — it's a pure function, so P/L is always correct."*

### d) "Should I buy Ethereum right now?"  → the key reliability story
- Returns **Needs Human** with low confidence.
- Say: *"This is the important one. It refuses to give regulated investment advice — it escalates
  instead of guessing. That guardrail is deterministic, enforced in code, not just a prompt."*

**On every answer, point at the badges:** verdict (Answered / Needs Human), confidence, the tools
called, latency, and token count — *"the response is fully observable."*

---

## 5. Engineering talking points (what actually wins the room)

- **Grounding over guessing** — deterministic backstops in `backend/app/agent/synthesize.py`
  *force* `NEEDS_HUMAN` for empty/weak retrieval or advice requests, regardless of the model's
  output.
- **Eval as a CI gate** — `eval/golden_set.jsonl` + `eval/run_eval.py` score the agent on every
  path with deterministic checks and **fail the build** below a pass-rate threshold.
  *"I treat the agent like software — it has regression tests."*
- **Graceful degradation** — Redis / Postgres / LangFuse are all fail-open; the app never crashes
  if infra is down (`backend/app/cache.py`).
- **Observability** — LangFuse traces every run with a span per tool call, latency, and token
  usage.
- **Provider-swappable LLM** — `backend/app/agent/llm.py` isolates the provider, so Groq →
  Anthropic is a one-file change.
- **LangGraph orchestration** — a router node decides which tools to call, a tools node executes
  them, and a synthesis node produces the structured JSON, with a bounded tool-calling loop.

---

## 6. (Optional) Show the tests and eval gate live

Fast, and very convincing:

```powershell
# 36 hermetic unit tests (~2 sec, no secrets/network needed)
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q

# The real eval gate against the running agent
cd ..
.\backend\.venv\Scripts\python.exe eval\run_eval.py
```

The eval prints a per-case pass/fail table, a category breakdown, and a final gate verdict.

---

## 7. Risk management (read this before the interview)

- **It needs internet.** On flaky wifi the LLM/price calls can stall. **Record a 60-second screen
  capture of the demo working** as a fallback so you're never stuck on a spinner.
- **Warm it up first** (see step 2). Don't let the cold first-request latency be the live one.
- **Have the repo open** as plan B — if the live app misbehaves, walk through the architecture,
  `synthesize.py` guardrails, and the eval harness instead. The code tells the story just as well.

---

## Quick reference

| What | Where |
|------|-------|
| UI | http://localhost:8080 |
| API health | http://localhost:8000/health |
| Ask endpoint | `POST http://localhost:8000/ask` body `{"question": "..."}` |
| Start | `docker compose up --build -d` |
| Stop | `docker compose down` |
| Logs | `docker compose logs -f api` |
| Unit tests | `cd backend && .\.venv\Scripts\python.exe -m pytest tests -q` |
| Eval gate | `.\backend\.venv\Scripts\python.exe eval\run_eval.py` |
