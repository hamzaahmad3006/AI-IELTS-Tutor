"""AI subsystem: provider-agnostic orchestration for scoring & generation."""

from ai.orchestrator import AIOrchestrator, ScoringError, WritingScore
from ai.provider import LLMProvider, LLMResult
from ai.providers import build_provider

__all__ = [
    "AIOrchestrator",
    "ScoringError",
    "WritingScore",
    "LLMProvider",
    "LLMResult",
    "build_provider",
]
