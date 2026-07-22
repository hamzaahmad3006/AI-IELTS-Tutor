"""Groq provider adapter (OpenAI-compatible chat completions API).

Uses httpx directly so there is no hard SDK dependency. Enabled when
`AI_PROVIDER=groq` and `GROQ_API_KEY` is set."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ai.provider import LLMProvider, LLMResult, Message

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self._api_key = api_key
        self._model = model

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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                _GROQ_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)

        content: str = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        data: dict[str, Any] | None = None
        if json_object:
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = None

        return LLMResult(
            content=content,
            data=data,
            provider=self.name,
            model=self._model,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            total_tokens=int(usage.get("total_tokens", 0)),
            latency_ms=latency_ms,
        )
