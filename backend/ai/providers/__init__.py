"""Provider factory: selects the LLM provider from configuration.

Adding OpenAI / Gemini / Claude later is a new adapter + a branch here — no
change to the orchestrator or any domain code."""

from __future__ import annotations

from ai.provider import LLMProvider
from core.config import get_settings

from .groq_provider import GroqProvider
from .mock_provider import MockProvider


def build_provider() -> LLMProvider:
    settings = get_settings()
    if settings.ai_provider == "groq" and settings.groq_api_key:
        return GroqProvider(api_key=settings.groq_api_key)
    # No key (or unknown provider) -> deterministic offline mock.
    return MockProvider()


__all__ = ["build_provider", "GroqProvider", "MockProvider"]
