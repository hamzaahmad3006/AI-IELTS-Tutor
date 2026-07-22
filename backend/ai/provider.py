"""Provider-agnostic LLM port.

All AI inference in the app flows through `LLMProvider`. No business/domain code
calls a specific vendor directly, so Groq can be swapped for OpenAI / Gemini /
Claude — or wrapped by LangGraph / CrewAI / AutoGen — by adding an adapter and a
config value, with no change to the orchestrator or services (SRS section 19)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# A chat message: {"role": "system" | "user" | "assistant", "content": "..."}
Message = dict[str, str]


@dataclass(slots=True)
class LLMResult:
    """Normalized result returned by every provider."""

    content: str
    data: dict[str, Any] | None = None
    provider: str = "unknown"
    model: str = "unknown"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Port implemented by every model provider adapter."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        *,
        messages: list[Message],
        json_object: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        """Run a completion. When `json_object` is True the provider must return
        `LLMResult.data` populated with the parsed JSON object."""
        raise NotImplementedError
