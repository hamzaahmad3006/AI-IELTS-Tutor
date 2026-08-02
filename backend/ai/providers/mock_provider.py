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


def _user_text(messages: list[Message]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def _system_text(messages: list[Message]) -> str:
    for message in messages:
        if message.get("role") == "system":
            return message.get("content", "")
    return ""


def _mock_issues(text: str) -> list[dict[str, str]]:
    """Flag the two longest sentences, quoted verbatim from the input.

    Deliberately trivial: the point is to exercise span resolution end to end
    without a paid provider, not to imitate examiner judgement. Quoting verbatim
    matters — a paraphrase would be silently discarded by the resolver and the
    highlight path would never be tested.
    """
    sentences = [
        part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()
    ]
    if not sentences:
        return []
    tags = ("grammatical_range", "lexical_resource")
    return [
        {
            "quote": sentence,
            "tag": tags[i % len(tags)],
            "note": "Mock note: vary the structure and choose more precise wording.",
        }
        for i, sentence in enumerate(sorted(sentences, key=len, reverse=True)[:2])
    ]


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
        text = _user_text(messages)
        is_speaking = "Speaking examiner" in _system_text(messages)
        words = re.findall(r"[A-Za-z']+", text)
        word_count = len(words)
        unique_ratio = (len(set(w.lower() for w in words)) / word_count) if word_count else 0.0
        sentences = max(1, len(re.findall(r"[.!?]+", text)))
        avg_sentence_len = word_count / sentences

        # Heuristic bands (purely illustrative until real AI scoring is enabled).
        length_band = 5.0 + min(2.5, word_count / 100.0)
        lexical = _clamp_band(4.5 + unique_ratio * 4.0)
        grammar = _clamp_band(length_band - 0.5)
        coherence = _clamp_band(4.5 + min(2.5, avg_sentence_len / 8.0))

        if is_speaking:
            fluency = _clamp_band(4.5 + min(2.5, word_count / 80.0))
            pronunciation = _clamp_band(length_band)
            overall = _clamp_band((fluency + lexical + grammar + pronunciation) / 4.0)
            data = {
                "fluency_coherence": fluency,
                "lexical_resource": lexical,
                "grammatical_range": grammar,
                "pronunciation": pronunciation,
                "overall_band": overall,
                "feedback_summary": (
                    "Mock evaluation: your response is on-topic; reduce hesitation "
                    "and use a wider range of connectives and precise vocabulary to "
                    "lift your band. (Enable a real AI provider for detailed feedback.)"
                ),
                "issues": _mock_issues(text),
            }
        else:
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
                "improved_essay": text.strip(),
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
