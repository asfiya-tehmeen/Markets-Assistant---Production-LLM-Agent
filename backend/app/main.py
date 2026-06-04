"""FastAPI entrypoint for the Markets Assistant backend.

Phase 2: /health plus POST /ask with per-IP rate limiting, an identical-question cache,
PostgreSQL persistence, and (optional) LangFuse tracing. All infra degrades gracefully when
absent, so the endpoint never crashes.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.agent.graph import run_agent
from app.cache import cache_answer, check_rate_limit, get_cached_answer
from app.config import get_settings
from app.db import init_db, log_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on startup (no-op if Postgres is unreachable)."""
    init_db()
    yield


app = FastAPI(title="Markets Assistant", version="0.2.0", lifespan=lifespan)

# Allow the browser frontend (different origin in dev) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="The user's finance/markets question.")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Returns a static OK so orchestrators can check the process is up."""
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest, request: Request):
    """Answer a finance/markets question with a structured, grounded response.

    Pipeline: rate-limit -> question cache -> agent -> cache + persist. Always returns 200
    except for 429 when the per-IP limit is exceeded.
    """
    client_ip = request.client.host if request.client else "unknown"

    allowed, remaining = check_rate_limit(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again in a minute."},
            headers={"Retry-After": "60"},
        )

    cached = get_cached_answer(req.question)
    if cached is not None:
        cached.setdefault("meta", {})["cache_hit"] = True
        log_request(question=req.question, response=cached, cache_hit=True)
        return cached

    response = run_agent(req.question)
    response.setdefault("meta", {})["cache_hit"] = False

    cache_answer(req.question, response)
    log_request(question=req.question, response=response, cache_hit=False)
    return response
