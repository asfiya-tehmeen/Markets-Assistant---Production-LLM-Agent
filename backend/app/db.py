"""PostgreSQL persistence via SQLAlchemy: one row per /ask request.

Fail-open: if the database is unreachable at startup or on write, logging is skipped and the
request still succeeds. Connection details come from ``DATABASE_URL``.
"""
from __future__ import annotations

import datetime as _dt
import logging

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings

_log = logging.getLogger("markets.db")


class Base(DeclarativeBase):
    pass


class RequestLog(Base):
    """A single answered (or escalated) question with its metrics."""

    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[_dt.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: _dt.datetime.now(_dt.timezone.utc)
    )
    question: Mapped[str] = mapped_column(Text)
    tools_called: Mapped[list] = mapped_column(JSON, default=list)
    answer: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16))
    verdict: Mapped[str] = mapped_column(String(16))
    latency_ms: Mapped[float] = mapped_column(Float)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_hit: Mapped[bool] = mapped_column(Integer, default=0)


_engine = None
_Session: "sessionmaker | None" = None
_ready = False


def init_db() -> bool:
    """Create the engine and tables. Returns True on success; never raises."""
    global _engine, _Session, _ready
    try:
        # connect_timeout keeps startup fast when Postgres is absent (e.g. local dev without
        # docker): a dropped SYN otherwise blocks on a full TCP timeout.
        _engine = create_engine(
            get_settings().database_url, pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
        Base.metadata.create_all(_engine)
        _Session = sessionmaker(bind=_engine)
        _ready = True
        _log.info("Postgres persistence ready.")
    except Exception as exc:
        _ready = False
        _log.warning("Postgres unavailable, persistence disabled: %s", exc)
    return _ready


def log_request(*, question: str, response: dict, cache_hit: bool = False) -> None:
    """Persist one request from a structured response (with its ``meta`` block). Fail-open."""
    if not _ready or _Session is None:
        return
    meta = response.get("meta", {})
    tokens = meta.get("tokens", {})
    try:
        with _Session() as session:
            session.add(RequestLog(
                question=question,
                tools_called=meta.get("tools_called", []),
                answer=response.get("answer", ""),
                confidence=response.get("confidence", ""),
                verdict=response.get("verdict", ""),
                latency_ms=meta.get("latency_ms", 0.0),
                prompt_tokens=tokens.get("prompt", 0),
                completion_tokens=tokens.get("completion", 0),
                total_tokens=tokens.get("total", 0),
                cache_hit=1 if cache_hit else 0,
            ))
            session.commit()
    except Exception as exc:
        _log.warning("Failed to persist request: %s", exc)
