"""Centralised settings read from environment / backend/.env.

Kept dependency-light (no pydantic-settings) — a plain object loaded once via lru_cache.
"""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env (this file is backend/app/config.py -> parents[1] == backend/).
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings:
    """Strongly-typed view over the environment variables the app uses."""

    def __init__(self) -> None:
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
        self.llm_model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.groq_api_key: str = os.getenv("GROQ_API_KEY", "")
        self.groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
        self.coingecko_api_key: str = os.getenv("COINGECKO_API_KEY", "")
        self.chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        self.kb_relevance_threshold: float = float(os.getenv("KB_RELEVANCE_THRESHOLD", "0.3"))

        # --- Redis (cache + rate limit) ---
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.price_cache_ttl: int = int(os.getenv("PRICE_CACHE_TTL_SECONDS", "60"))
        self.question_cache_ttl: int = int(os.getenv("QUESTION_CACHE_TTL_SECONDS", "60"))
        self.rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

        # --- PostgreSQL ---
        self.database_url: str = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://markets:markets@localhost:5432/markets"
        )

        # --- LangFuse (optional) ---
        self.langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return Settings()
