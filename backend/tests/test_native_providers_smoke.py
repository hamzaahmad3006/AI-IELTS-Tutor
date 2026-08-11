"""Smoke test: the Anthropic and Gemini adapters.

These two do not speak the OpenAI wire format, and the differences are exactly
the kind that pass review and fail in production: a system message that must be
lifted out of the list, an assistant role spelled `model`, usage fields under
different names with no total.

Everything runs against a stubbed transport. That is not a compromise here --
it is what lets these assert the cases a live call will not reliably produce
(a safety block, a response with no usage, a thinking block before the answer)
-- and it means the suite never spends anyone's quota.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_native_providers.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import httpx  # noqa: E402

from ai.providers.anthropic_provider import (  # noqa: E402
    API_VERSION,
    AnthropicProvider,
    parse_message,
    split_system,
)
from ai.providers.gemini_provider import (  # noqa: E402
    GeminiProvider,
    parse_generate_content,
    to_contents,
)

MESSAGES = [
    {"role": "system", "content": "You are an IELTS examiner."},
    {"role": "user", "content": "Score this essay."},
    {"role": "assistant", "content": "Understood."},
    {"role": "system", "content": "Return JSON."},
]


def _patch_transport(handler):
    original = httpx.AsyncClient.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = patched
    return original


# --------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------


def check_anthropic_system_split() -> None:
    system, turns = split_system(MESSAGES)

    # Both system messages are kept. Dropping the second would silently lose
    # the instruction that asks for JSON at all.
    assert "IELTS examiner" in system
    assert "Return JSON" in system

    # A role:"system" entry left in the list is a 400 from this API, so the
    # important half of this is what is *not* there.
    assert all(turn["role"] != "system" for turn in turns)
    assert [turn["role"] for turn in turns] == ["user", "assistant"]


def check_anthropic_parsing() -> None:
    body = {
        "model": "claude-sonnet-4-5",
        "content": [{"type": "text", "text": '"overall_band": 6.5}'}],
        "usage": {"input_tokens": 120, "output_tokens": 40},
        "stop_reason": "end_turn",
    }
    result = parse_message(
        body, provider="anthropic", latency_ms=10, json_object=True
    )
    # The prefilled "{" is not echoed by the API, so the parser has to put it
    # back. Without that this is a decode error on every scoring call.
    assert result.data == {"overall_band": 6.5}
    # No total is reported, so it must be derived rather than left at zero on
    # a call that was billed.
    assert result.total_tokens == 160

    # A thinking block before the answer. Indexing content[0] blindly would
    # return reasoning text instead of the score.
    thinking = {
        "content": [
            {"type": "thinking", "thinking": "The candidate uses..."},
            {"type": "text", "text": '{"overall_band": 7.0}'},
        ]
    }
    assert parse_message(
        thinking, provider="a", latency_ms=1, json_object=True
    ).data == {"overall_band": 7.0}

    # Empty and malformed responses resolve to no data rather than raising:
    # the orchestrator turns a missing payload into a ScoringError that says
    # what was being scored, which beats a KeyError from in here.
    for empty in ({}, {"content": []}, {"content": [{"type": "text"}]}):
        parsed = parse_message(
            empty, provider="a", latency_ms=1, json_object=True
        )
        assert parsed.content == ""
        assert parsed.data is None
        assert parsed.total_tokens == 0

    refusal = {"content": [{"type": "text", "text": "I can't help with that."}]}
    assert parse_message(
        refusal, provider="a", latency_ms=1, json_object=True
    ).data is None


async def check_anthropic_request_shape() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        seen["version"] = request.headers.get("anthropic-version")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "claude-sonnet-4-5",
                "content": [{"type": "text", "text": '"overall_band": 6.0}'}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        )

    original = _patch_transport(handler)
    try:
        provider = AnthropicProvider(api_key="sk-ant-test")
        result = await provider.complete(
            messages=MESSAGES, json_object=True, temperature=0.3, max_tokens=900
        )
        assert result.data == {"overall_band": 6.0}
        assert result.provider == "anthropic"

        # Authenticated by header, not bearer token -- the one thing that makes
        # this API look OpenAI-shaped and behave differently.
        assert seen["key"] == "sk-ant-test"
        assert seen["version"] == API_VERSION

        body = seen["body"]
        assert body["system"].startswith("You are an IELTS examiner")
        assert body["max_tokens"] == 900
        assert body["temperature"] == 0.3
        assert all(turn["role"] != "system" for turn in body["messages"])
        # The prefill that holds the model to an object.
        assert body["messages"][-1] == {"role": "assistant", "content": "{"}
        # No response_format on this API; sending one is an error.
        assert "response_format" not in body
    finally:
        httpx.AsyncClient.__init__ = original


# --------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------


def check_gemini_content_conversion() -> None:
    system, contents = to_contents(MESSAGES)

    assert "IELTS examiner" in system and "Return JSON" in system
    # `assistant` is spelled `model` here. Sent as "assistant" it is rejected.
    assert [c["role"] for c in contents] == ["user", "model"]
    assert contents[0]["parts"] == [{"text": "Score this essay."}]


def check_gemini_parsing() -> None:
    body = {
        "candidates": [
            {
                "content": {"parts": [{"text": '{"overall_band": 6.5}'}]},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 40,
            "totalTokenCount": 160,
        },
        "modelVersion": "gemini-2.0-flash",
    }
    result = parse_generate_content(
        body, provider="gemini", latency_ms=10, json_object=True
    )
    assert result.data == {"overall_band": 6.5}
    assert result.total_tokens == 160
    assert result.model == "gemini-2.0-flash"

    # A safety block: candidates present, `content` absent entirely. This is
    # Gemini's own empty shape and the one that raises if reached for blindly.
    blocked = {
        "candidates": [{"finishReason": "SAFETY"}],
        "usageMetadata": {"promptTokenCount": 12},
    }
    parsed = parse_generate_content(
        blocked, provider="g", latency_ms=1, json_object=True
    )
    assert parsed.content == ""
    assert parsed.data is None
    # Kept, because a blocked response is otherwise indistinguishable from an
    # empty one and the two need different handling upstream.
    assert parsed.meta["finish_reason"] == "SAFETY"
    # Prompt tokens are still billed on a blocked call.
    assert parsed.total_tokens == 12

    for empty in ({}, {"candidates": []}, {"candidates": [{"content": {}}]}):
        assert (
            parse_generate_content(
                empty, provider="g", latency_ms=1, json_object=True
            ).data
            is None
        )


async def check_gemini_request_shape() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"overall_band": 5.5}'}]}}
                ],
                "usageMetadata": {"totalTokenCount": 99},
            },
        )

    original = _patch_transport(handler)
    try:
        provider = GeminiProvider(api_key="goog-test", model="gemini-2.0-flash")
        result = await provider.complete(
            messages=MESSAGES, json_object=True, temperature=0.4, max_tokens=800
        )
        assert result.data == {"overall_band": 5.5}
        assert result.total_tokens == 99

        # The model is part of the path, not the body.
        assert seen["url"].endswith("/models/gemini-2.0-flash:generateContent")
        # Header, not a query parameter: a key in a URL ends up in logs and
        # proxy access records.
        assert seen["key"] == "goog-test"
        assert "goog-test" not in str(seen["url"])

        body = seen["body"]
        assert body["systemInstruction"]["parts"][0]["text"].startswith(
            "You are an IELTS examiner"
        )
        config = body["generationConfig"]
        assert config["maxOutputTokens"] == 800
        assert config["temperature"] == 0.4
        # The equivalent of response_format on this API.
        assert config["responseMimeType"] == "application/json"
    finally:
        httpx.AsyncClient.__init__ = original


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------


def check_construction_is_guarded() -> None:
    for factory in (AnthropicProvider, GeminiProvider):
        for kwargs in ({"api_key": ""}, {"api_key": "k", "model": ""}):
            try:
                factory(**kwargs)  # type: ignore[arg-type]
            except ValueError:
                pass
            else:  # pragma: no cover
                raise AssertionError(f"{factory.__name__} built with {kwargs}")


def check_factory_selection() -> None:
    from core.config import Settings

    import ai.providers as providers

    original = providers.get_settings

    def with_settings(**kwargs) -> object:
        # Keys blanked by default: Settings reads the real .env, so an unset
        # key silently picks up the developer's own and the fallback
        # assertions test nothing.
        fields = {"groq_api_key": "", "llm_api_key": "", **kwargs}
        providers.get_settings = lambda: Settings(**fields)  # type: ignore[attr-defined]
        try:
            return providers.build_provider()
        finally:
            providers.get_settings = original

    assert with_settings(ai_provider="anthropic", llm_api_key="k").name == "anthropic"
    assert with_settings(ai_provider="gemini", llm_api_key="k").name == "gemini"

    # Both take the shared LLM_MODEL / LLM_BASE_URL overrides.
    chosen = with_settings(
        ai_provider="gemini",
        llm_api_key="k",
        llm_model="gemini-2.5-pro",
        llm_base_url="https://proxy.internal/v1beta",
    )
    assert chosen._url == (
        "https://proxy.internal/v1beta/models/gemini-2.5-pro:generateContent"
    )

    # Without a key they fall back to the mock rather than raising: a missing
    # key should be a visibly fake score, not a dead endpoint at request time.
    assert with_settings(ai_provider="anthropic").name == "mock"
    assert with_settings(ai_provider="gemini").name == "mock"

    # Adding these must not change what a working Groq deployment already uses.
    assert with_settings(ai_provider="groq", groq_api_key="gsk-x").name == "groq"


def run() -> None:
    check_anthropic_system_split()
    check_anthropic_parsing()
    asyncio.run(check_anthropic_request_shape())

    check_gemini_content_conversion()
    check_gemini_parsing()
    asyncio.run(check_gemini_request_shape())

    check_construction_is_guarded()
    check_factory_selection()

    print("NATIVE PROVIDERS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
