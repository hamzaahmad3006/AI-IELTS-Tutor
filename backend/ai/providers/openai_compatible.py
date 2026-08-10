"""Adapter for any OpenAI-compatible chat-completions API.

Groq, OpenAI, Together, Fireworks, OpenRouter and most self-hosted gateways
speak the same request and response shape. One adapter parameterised by base URL
and model covers all of them, and each is then a line of configuration rather
than a new file.

That matters here for a specific reason: this project has run out of Groq quota
twice. A provider you cannot switch away from in an afternoon is a single point
of failure, and the fix is not a better Groq key.

Anthropic and Gemini are deliberately not covered. Their APIs differ enough --
system prompts handled separately, different content and usage shapes -- that
folding them in here would mean a wrapper full of branches that is harder to
read than two honest adapters. They are worth writing when someone actually
needs them, against real keys.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ai.provider import LLMProvider, LLMResult, Message


class OpenAICompatibleProvider(LLMProvider):
    """Chat completions over the OpenAI wire format."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        name: str = "openai-compatible",
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError(f"{name} requires an API key")
        if not model:
            raise ValueError(f"{name} requires a model name")
        self._api_key = api_key
        # Trailing slashes are the most common configuration mistake here and
        # produce a 404 that looks like a wrong model name.
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self.name = name
        self._timeout_s = timeout_s

    async def complete(
        self,
        *,
        messages: list[Message],
        json_object: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(
                self._url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)

        return parse_completion(
            body, provider=self.name, latency_ms=latency_ms, json_object=json_object
        )


def parse_completion(
    body: dict,
    *,
    provider: str,
    latency_ms: int,
    json_object: bool,
) -> LLMResult:
    """Read a chat-completions response.

    Split out and tested directly because every field here is optional in
    practice. Providers that claim OpenAI compatibility differ most in what
    they omit: some drop `usage` entirely, some return an empty `choices` list
    on a content filter, and a KeyError in the scoring path reads as our bug.
    """
    choices = body.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    content = message.get("content") or ""

    data: dict[str, Any] | None = None
    if json_object and content:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Left as None rather than raised: the orchestrator already turns a
            # missing payload into a ScoringError with context about what was
            # being scored, which is more useful than a JSONDecodeError here.
            data = None

    usage = body.get("usage") or {}
    prompt_tokens = int(usage.get("prompt_tokens") or 0)
    completion_tokens = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or 0)
    # Some gateways report the parts and omit the total. Deriving it keeps cost
    # reporting honest rather than showing zero for a call that was billed.
    if not total:
        total = prompt_tokens + completion_tokens

    return LLMResult(
        content=content,
        data=data,
        provider=provider,
        model=body.get("model") or "unknown",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        latency_ms=latency_ms,
    )


#: Known endpoints, so configuring one is a name rather than a URL to look up.
PRESETS: dict[str, tuple[str, str]] = {
    # (base URL, default model)
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "together": ("https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct"),
    "fireworks": (
        "https://api.fireworks.ai/inference/v1",
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
    ),
}
