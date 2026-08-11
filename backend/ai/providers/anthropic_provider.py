"""Anthropic Messages API adapter.

Deliberately not folded into `openai_compatible`. Three things differ enough
that branching on them inside one adapter would be harder to read than this
file is:

  - the system prompt is a top-level `system` parameter, not a message with
    `role: "system"`. Left in the messages list it is rejected outright.
  - `max_tokens` is required rather than optional.
  - usage comes back as `input_tokens` / `output_tokens`, with no total.

There is also no `response_format` parameter. JSON is asked for in the prompt
and, more reliably, by prefilling the assistant turn with an opening brace so
the model has already committed to an object -- which means the brace has to be
put back on the front of the response before parsing.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ai.provider import LLMProvider, LLMResult, Message

DEFAULT_URL = "https://api.anthropic.com/v1/messages"

#: Pinned. Anthropic dates its API, and an unpinned version means a response
#: shape can change under a deployment that changed nothing.
API_VERSION = "2023-06-01"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-5",
        base_url: str = DEFAULT_URL,
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("anthropic requires an API key")
        if not model:
            raise ValueError("anthropic requires a model name")
        self._api_key = api_key
        self._model = model
        self._url = base_url
        self._timeout_s = timeout_s

    async def complete(
        self,
        *,
        messages: list[Message],
        json_object: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        system, turns = split_system(messages)

        if json_object:
            # Prefilling the assistant turn with "{" is what actually holds the
            # model to an object, more so than asking in the prompt. The cost is
            # that the brace is not echoed back, so it is restored below.
            turns = [*turns, {"role": "assistant", "content": "{"}]

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": turns,
            # Required here, unlike the OpenAI shape where it is optional.
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["system"] = system

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(
                self._url,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)

        return parse_message(
            body,
            provider=self.name,
            latency_ms=latency_ms,
            json_object=json_object,
            fallback_model=self._model,
        )


def split_system(messages: list[Message]) -> tuple[str, list[Message]]:
    """Lift system messages out of the list into one system string.

    A `role: "system"` entry left in `messages` is a 400 from this API, so the
    orchestrator's message list -- written for the OpenAI shape -- has to be
    reshaped rather than passed through. Multiple system messages are joined
    rather than dropped, since the orchestrator does emit more than one.
    """
    system_parts = [
        m["content"] for m in messages if m.get("role") == "system" and m.get("content")
    ]
    turns = [dict(m) for m in messages if m.get("role") != "system"]
    return "\n\n".join(system_parts), turns


def parse_message(
    body: dict,
    *,
    provider: str,
    latency_ms: int,
    json_object: bool,
    fallback_model: str = "unknown",
) -> LLMResult:
    """Read a Messages API response.

    Split out and tested directly, for the same reason as the OpenAI one: every
    field here is optional in practice, and a KeyError in the scoring path
    reads as our bug rather than the gateway's.
    """
    # `content` is a list of typed blocks. Only text blocks carry the answer;
    # a response can also open with a thinking block, and indexing [0] blindly
    # would return reasoning instead of the score.
    blocks = body.get("content") or []
    content = "".join(
        block.get("text") or ""
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    )

    data: dict[str, Any] | None = None
    if json_object and content:
        # Put back the brace that was prefilled and therefore not echoed.
        candidate = content if content.lstrip().startswith("{") else "{" + content
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            data = None

    usage = body.get("usage") or {}
    prompt_tokens = int(usage.get("input_tokens") or 0)
    completion_tokens = int(usage.get("output_tokens") or 0)

    return LLMResult(
        content=content,
        data=data,
        provider=provider,
        model=body.get("model") or fallback_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        # No total is reported, so it is derived. Zero would misreport a call
        # that was billed.
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        meta={"stop_reason": body.get("stop_reason") or ""},
    )
