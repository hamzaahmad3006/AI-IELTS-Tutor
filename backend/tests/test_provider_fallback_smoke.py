"""Smoke test: the OpenAI-compatible provider and the factory that selects it.

This exists because the project has run out of Groq quota twice. A provider you
cannot switch away from in an afternoon is a single point of failure, and the
fix is not a better key.

Run against a stubbed transport, which lets these assert things a live call
cannot -- what happens when a gateway omits `usage`, or returns no choices at
all -- and means the suite never spends anyone's quota.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_provider_fallback.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import httpx  # noqa: E402

from ai.providers import PRESETS, build_provider  # noqa: E402
from ai.providers.openai_compatible import (  # noqa: E402
    OpenAICompatibleProvider,
    parse_completion,
)

OK_BODY = {
    "model": "gpt-4o-mini",
    "choices": [{"message": {"role": "assistant", "content": '{"overall_band": 6.5}'}}],
    "usage": {"prompt_tokens": 120, "completion_tokens": 40, "total_tokens": 160},
}


def _patch_transport(handler):
    original = httpx.AsyncClient.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = patched
    return original


def check_parsing() -> None:
    result = parse_completion(
        OK_BODY, provider="openai", latency_ms=250, json_object=True
    )
    assert result.data == {"overall_band": 6.5}
    assert result.total_tokens == 160
    assert result.model == "gpt-4o-mini"

    # A gateway that reports the parts and omits the total. Deriving it keeps
    # cost reporting honest rather than showing zero for a billed call.
    partial = {
        **OK_BODY,
        "usage": {"prompt_tokens": 100, "completion_tokens": 25},
    }
    assert parse_completion(
        partial, provider="x", latency_ms=1, json_object=False
    ).total_tokens == 125

    # No usage at all. Some compatible endpoints simply omit it.
    none_usage = {k: v for k, v in OK_BODY.items() if k != "usage"}
    assert parse_completion(
        none_usage, provider="x", latency_ms=1, json_object=False
    ).total_tokens == 0

    # Empty choices -- what a content filter returns. A KeyError here would
    # surface in the scoring path and read as our bug.
    for empty in ({}, {"choices": []}, {"choices": [{}]}):
        parsed = parse_completion(
            empty, provider="x", latency_ms=1, json_object=True
        )
        assert parsed.content == ""
        assert parsed.data is None

    # Content that is not JSON when JSON was asked for. Left as None rather
    # than raised: the orchestrator turns a missing payload into a ScoringError
    # that says what was being scored, which is more useful than a decode error.
    bad_json = {
        "choices": [{"message": {"content": "I'm sorry, I can't help with that."}}]
    }
    assert parse_completion(
        bad_json, provider="x", latency_ms=1, json_object=True
    ).data is None


async def check_request_shape() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        import json as _json

        seen["body"] = _json.loads(request.content)
        return httpx.Response(200, json=OK_BODY)

    original = _patch_transport(handler)
    try:
        provider = OpenAICompatibleProvider(
            api_key="sk-test",
            # Trailing slash on purpose: it is the most common configuration
            # mistake here and produces a 404 that looks like a wrong model.
            base_url="https://api.openai.com/v1/",
            model="gpt-4o-mini",
            name="openai",
        )
        result = await provider.complete(
            messages=[{"role": "user", "content": "score this"}],
            json_object=True,
            temperature=0.3,
            max_tokens=900,
        )
        assert result.data == {"overall_band": 6.5}
        assert result.provider == "openai"

        assert seen["url"] == "https://api.openai.com/v1/chat/completions"
        assert seen["auth"] == "Bearer sk-test"
        body = seen["body"]
        assert body["model"] == "gpt-4o-mini"
        assert body["temperature"] == 0.3
        assert body["max_tokens"] == 900
        # Requested explicitly, because without it a model returns prose that
        # then fails to parse and looks like a provider fault.
        assert body["response_format"] == {"type": "json_object"}
    finally:
        httpx.AsyncClient.__init__ = original


def check_construction_is_guarded() -> None:
    for kwargs in (
        {"api_key": "", "base_url": "https://x/v1", "model": "m"},
        {"api_key": "k", "base_url": "https://x/v1", "model": ""},
    ):
        try:
            OpenAICompatibleProvider(**kwargs)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"constructed with {kwargs}")


def check_factory_selection() -> None:
    from core.config import Settings

    import ai.providers as providers

    original = providers.get_settings

    def with_settings(**kwargs) -> object:
        # Keys defaulted to empty rather than left unset: Settings reads the
        # real .env, so an unset groq_api_key silently picks up the developer's
        # actual key and the fallback assertions test nothing.
        fields = {"groq_api_key": "", "llm_api_key": "", **kwargs}
        providers.get_settings = lambda: Settings(**fields)  # type: ignore[attr-defined]
        try:
            return build_provider()
        finally:
            providers.get_settings = original

    # A preset needs only a key: the URL and model come with the name.
    for preset in PRESETS:
        chosen = with_settings(ai_provider=preset, llm_api_key="sk-test")
        assert chosen.name == preset, preset

    # An explicit endpoint needs all three.
    custom = with_settings(
        ai_provider="openai-compatible",
        llm_api_key="k",
        llm_base_url="https://gateway.internal/v1",
        llm_model="local-70b",
    )
    assert custom.name == "openai-compatible"

    # Missing pieces fall back to the mock rather than raising. A missing key
    # should be a visibly fake score, not a dead endpoint at request time.
    assert with_settings(ai_provider="openai").name == "mock"
    assert with_settings(ai_provider="openai-compatible", llm_api_key="k").name == "mock"
    assert with_settings(ai_provider="groq").name == "mock"
    assert with_settings(ai_provider="nonsense", llm_api_key="k").name == "mock"

    # Groq still wins when it is configured: this adds a fallback, it does not
    # change what a working deployment already uses.
    assert with_settings(ai_provider="groq", groq_api_key="gsk-x").name == "groq"


def run() -> None:
    check_parsing()
    asyncio.run(check_request_shape())
    check_construction_is_guarded()
    check_factory_selection()

    print("PROVIDER FALLBACK SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
