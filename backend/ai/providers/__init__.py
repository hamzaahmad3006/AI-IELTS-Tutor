"""Provider factory: selects the LLM provider from configuration.

Adding OpenAI / Gemini / Claude later is a new adapter + a branch here — no
change to the orchestrator or any domain code."""

from __future__ import annotations

from ai.provider import LLMProvider
from core.config import get_settings

from .groq_provider import GroqProvider
from .mock_provider import MockProvider
from .openai_compatible import PRESETS, OpenAICompatibleProvider


def build_provider() -> LLMProvider:
    settings = get_settings()
    choice = (settings.ai_provider or "").strip().lower()

    if choice == "groq" and settings.groq_api_key:
        return GroqProvider(api_key=settings.groq_api_key)

    if choice in PRESETS and settings.llm_api_key:
        base_url, default_model = PRESETS[choice]
        return OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or base_url,
            model=settings.llm_model or default_model,
            name=choice,
        )

    if (
        choice == "openai-compatible"
        and settings.llm_api_key
        and settings.llm_base_url
        and settings.llm_model
    ):
        return OpenAICompatibleProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            name="openai-compatible",
        )

    # No key, or a provider nobody configured -> the deterministic offline
    # mock. Failing to the mock rather than raising means a missing key is a
    # visibly fake score rather than a dead endpoint.
    return MockProvider()


__all__ = [
    "build_provider",
    "GroqProvider",
    "MockProvider",
    "OpenAICompatibleProvider",
    "PRESETS",
]
