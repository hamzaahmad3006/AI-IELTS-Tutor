"""Google Gemini (generateContent) adapter.

The furthest of the three from the OpenAI shape, which is why it is its own
file:

  - messages are `contents`, each with `parts: [{"text": ...}]`, and the
    assistant role is spelled `model`.
  - the system prompt is `systemInstruction`, shaped like a content block
    rather than a string.
  - generation settings live under `generationConfig`, and `max_tokens` is
    `maxOutputTokens`.
  - the key goes in a header, and JSON is requested with a response *mime
    type* rather than a response format.

Usage is `usageMetadata`, and unlike Anthropic it does report a total.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ai.provider import LLMProvider, LLMResult, Message

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.0-flash",
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("gemini requires an API key")
        if not model:
            raise ValueError("gemini requires a model name")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    @property
    def _url(self) -> str:
        return f"{self._base_url}/models/{self._model}:generateContent"

    async def complete(
        self,
        *,
        messages: list[Message],
        json_object: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        system, contents = to_contents(messages)

        generation_config: dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if json_object:
            # The equivalent of response_format here. Without it the model
            # returns prose that then fails to parse and looks like a provider
            # fault rather than a missing parameter.
            generation_config["responseMimeType"] = "application/json"

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(
                self._url,
                # Header rather than a query parameter: a key in a URL ends up
                # in logs, proxies and error reports.
                headers={
                    "x-goog-api-key": self._api_key,
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)

        return parse_generate_content(
            body,
            provider=self.name,
            latency_ms=latency_ms,
            json_object=json_object,
            fallback_model=self._model,
        )


def to_contents(messages: list[Message]) -> tuple[str, list[dict[str, Any]]]:
    """Convert OpenAI-shaped messages into Gemini `contents`.

    Two renames that are easy to miss and fail loudly: `assistant` is `model`
    here, and system messages move out into `systemInstruction` entirely.
    """
    system_parts = [
        m["content"] for m in messages if m.get("role") == "system" and m.get("content")
    ]
    contents = [
        {
            "role": "model" if m.get("role") == "assistant" else "user",
            "parts": [{"text": m.get("content") or ""}],
        }
        for m in messages
        if m.get("role") != "system"
    ]
    return "\n\n".join(system_parts), contents


def parse_generate_content(
    body: dict,
    *,
    provider: str,
    latency_ms: int,
    json_object: bool,
    fallback_model: str = "unknown",
) -> LLMResult:
    """Read a generateContent response.

    Gemini's empty case is its own shape: a safety block returns `candidates`
    with no `content` at all rather than an empty string, so reaching for
    `parts` unguarded raises on exactly the responses that most need handling.
    """
    candidates = body.get("candidates") or []
    first = candidates[0] if candidates else {}
    parts = ((first.get("content") or {}).get("parts")) or []
    content = "".join(
        part.get("text") or "" for part in parts if isinstance(part, dict)
    )

    data: dict[str, Any] | None = None
    if json_object and content:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = None

    usage = body.get("usageMetadata") or {}
    prompt_tokens = int(usage.get("promptTokenCount") or 0)
    completion_tokens = int(usage.get("candidatesTokenCount") or 0)
    total = int(usage.get("totalTokenCount") or 0)
    if not total:
        total = prompt_tokens + completion_tokens

    return LLMResult(
        content=content,
        data=data,
        provider=provider,
        model=body.get("modelVersion") or fallback_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        latency_ms=latency_ms,
        # Kept because a blocked response is otherwise indistinguishable from
        # an empty one, and the two need different handling upstream.
        meta={"finish_reason": first.get("finishReason") or ""},
    )
