"""LangFuse tracing for agent runs. Entirely optional and fully guarded.

If the LangFuse SDK isn't installed or keys are absent/invalid, every function here is a no-op,
so the app runs unchanged. Uses the LangFuse v2 client API.
"""
from __future__ import annotations

import logging

from app.config import get_settings

_log = logging.getLogger("markets.observability")

_client = None
_initialised = False


def _get_client():
    """Return a LangFuse client if configured + importable, else None (cached)."""
    global _client, _initialised
    if _initialised:
        return _client
    _initialised = True

    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None  # keys absent -> tracing disabled, no warning
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as exc:
        _log.warning("LangFuse disabled (init failed): %s", exc)
        _client = None
    return _client


def observe_run(*, question: str, response: dict, tool_outputs: list[dict],
                tokens: dict, latency_ms: float, model: str) -> None:
    """Record one agent run as a trace with a span per tool call. Never raises."""
    client = _get_client()
    if client is None:
        return
    try:
        trace = client.trace(
            name="markets-assistant.ask",
            input={"question": question},
            output=response,
            metadata={"latency_ms": latency_ms, "verdict": response.get("verdict"),
                      "confidence": response.get("confidence")},
        )
        for out in tool_outputs:
            trace.span(name=f"tool.{out['tool']}", input=out.get("args"),
                       output=out.get("result"))
        trace.generation(
            name="synthesis", model=model,
            usage={"input": tokens.get("prompt", 0), "output": tokens.get("completion", 0),
                   "total": tokens.get("total", 0)},
        )
        client.flush()
    except Exception as exc:
        _log.warning("LangFuse trace failed: %s", exc)
