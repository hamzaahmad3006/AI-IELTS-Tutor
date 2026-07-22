"""Deterministic mock provider.

Used automatically when no Groq API key is configured, so the AI vertical is
fully runnable and testable offline. It produces plausible, rubric-shaped
scores from lightweight heuristics on the candidate essay."""

from __future__ import annotations

import json
import re

from ai.provider import LLMProvider, LLMResult, Message


def _round_half(value: float) -> float:
    return round(value * 2) / 2


def _clamp_band(value: float) -> float:
    return max(0.0, min(9.0, _round_half(value)))


def _essay_from(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


class MockProvider(LLMProvider):
    name = "mock"

    async def complete(
        self,
        *,
        messages: list[Message],
        json_object: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResult:
        essay = _essay_from(messages)
        words = re.findall(r"[A-Za-z']+", essay)
        word_count = len(words)
        unique_ratio = (len(set(w.lower() for w in words)) / word_count) if word_count else 0.0
        sentences = max(1, len(re.findall(r"[.!?]+", essay)))
        avg_sentence_len = word_count / sentences

        # Heuristic bands (purely illustrative until real AI scoring is enabled).
        length_band = 5.0 + min(2.5, word_count / 100.0)
        lexical = _clamp_band(4.5 + unique_ratio * 4.0)
        grammar = _clamp_band(length_band - 0.5)
        coherence = _clamp_band(4.5 + min(2.5, avg_sentence_len / 8.0))
        task = _clamp_band(length_band if word_count >= 150 else length_band - 1.0)
        overall = _clamp_band((task + coherence + lexical + grammar) / 4.0)

        data = {
            "task_response": task,
            "coherence_cohesion": coherence,
            "lexical_resource": lexical,
            "grammatical_range": grammar,
            "overall_band": overall,
            "feedback_summary": (
                "Mock evaluation: your response is on-topic; focus on a wider "
                "range of complex structures and more precise vocabulary to lift "
                "your band. (Enable a real AI provider for detailed feedback.)"
            ),
            "improved_essay": essay.strip(),
        }
        content = json.dumps(data)
        approx_tokens = word_count + 60
        return LLMResult(
            content=content,
            data=data,
            provider=self.name,
            model="mock-heuristic",
            prompt_tokens=approx_tokens,
            completion_tokens=80,
            total_tokens=approx_tokens + 80,
            latency_ms=1,
        )
