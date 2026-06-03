"""Thin, provider-swappable chat client.

Currently targets Groq via its OpenAI-compatible endpoint, so the official ``openai`` SDK is
reused. Swapping to Anthropic later means adding a branch here only — callers are unaffected.
"""
from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import get_settings


class LLMClient:
    """Minimal chat wrapper exposing a single ``chat()`` method."""

    def __init__(self) -> None:
        settings = get_settings()
        if settings.llm_provider != "groq":
            raise NotImplementedError(
                f"LLM_PROVIDER='{settings.llm_provider}' not wired yet; only 'groq' is implemented."
            )
        self._client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
        self._model = settings.llm_model

    @property
    def model(self) -> str:
        return self._model

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        response_format: dict | None = None,
        temperature: float = 0.0,
    ):
        """Call chat completions. Returns the raw SDK response (caller reads usage/choices)."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        if response_format:
            kwargs["response_format"] = response_format
        return self._client.chat.completions.create(**kwargs)
