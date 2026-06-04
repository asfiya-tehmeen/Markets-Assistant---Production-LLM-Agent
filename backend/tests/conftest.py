"""Shared pytest setup.

- Provides a dummy GROQ_API_KEY so importing the app (which constructs an OpenAI client at
  import time) works without real credentials. No test here makes a live LLM call.
- Puts the repo-root ``eval/`` dir on sys.path so ``scoring`` is importable.
"""
import os
import sys
from pathlib import Path

# Must be set before any ``app`` import triggers OpenAI client construction.
os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")
# Force a clean, non-networked default for infra so tests stay hermetic.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "eval"))
