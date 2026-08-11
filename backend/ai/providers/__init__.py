"""Provider factory: selects the LLM provider from configuration.

Every adapter is reachable by name from a single config value, so switching
away from a provider that is down, rate-limited or too expensive is one line in
`.env` rather than a code change. That is the whole point: this project has run
out of Groq quota twice, and each time the scoring path went with it."""

from __future__ import annotations

from ai.provider import LLMProvider
from core.config import get_settings

from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .mock_provider import MockProvider
from .openai_compatible import PRESETS, OpenAICompatibleProvider


def build_provider() -> LLMProvider:
    settings = get_settings()
    choice = (settings.ai_provider or "").strip().lower()

    if choice == "groq" and settings.groq_api_key:
        return GroqProvider(api_key=settings.groq_api_key)

    # Checked before the preset table: these two do not speak the OpenAI wire
    # format and have their own adapters.
    if choice == "anthropic" and settings.llm_api_key:
        kwargs = {"api_key": settings.llm_api_key}
        if settings.llm_model:
            kwargs["model"] = settings.llm_model
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        return AnthropicProvider(**kwargs)

    if choice == "gemini" and settings.llm_api_key:
        kwargs = {"api_key": settings.llm_api_key}
        if settings.llm_model:
            kwargs["model"] = settings.llm_model
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        return GeminiProvider(**kwargs)

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
    "AnthropicProvider",
    "build_provider",
    "GeminiProvider",
    "GroqProvider",
    "MockProvider",
    "OpenAICompatibleProvider",
    "PRESETS",
]
