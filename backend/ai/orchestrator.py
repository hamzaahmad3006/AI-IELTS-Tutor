"""AI orchestrator: routes scoring/generation tasks to the active provider,
validates structured output, and returns typed results plus usage metadata."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ai.provider import LLMProvider, LLMResult
from ai.rubrics.speaking_rubric import build_speaking_messages
from ai.rubrics.writing_rubric import build_writing_messages, round_ielts


class WritingScore(BaseModel):
    task_response: float = Field(ge=0, le=9)
    coherence_cohesion: float = Field(ge=0, le=9)
    lexical_resource: float = Field(ge=0, le=9)
    grammatical_range: float = Field(ge=0, le=9)
    overall_band: float = Field(ge=0, le=9)
    feedback_summary: str
    improved_essay: str


class SpeakingScore(BaseModel):
    fluency_coherence: float = Field(ge=0, le=9)
    lexical_resource: float = Field(ge=0, le=9)
    grammatical_range: float = Field(ge=0, le=9)
    pronunciation: float = Field(ge=0, le=9)
    overall_band: float = Field(ge=0, le=9)
    feedback_summary: str


class ScoringError(Exception):
    """Raised when the provider output cannot be parsed into a valid score."""


class AIOrchestrator:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def score_writing(
        self, *, essay: str, task_type: int, weakness_summary: str = ""
    ) -> tuple[WritingScore, LLMResult]:
        messages = build_writing_messages(essay, task_type, weakness_summary)
        result = await self._provider.complete(
            messages=messages, json_object=True, temperature=0.2, max_tokens=1200
        )
        if result.data is None:
            raise ScoringError("Provider did not return a JSON object")

        try:
            score = WritingScore.model_validate(result.data)
        except Exception as exc:  # noqa: BLE001 - normalize to domain error
            raise ScoringError(f"Invalid score payload: {exc}") from exc

        # Enforce IELTS rounding on every band + recompute overall authoritatively.
        score.task_response = round_ielts(score.task_response)
        score.coherence_cohesion = round_ielts(score.coherence_cohesion)
        score.lexical_resource = round_ielts(score.lexical_resource)
        score.grammatical_range = round_ielts(score.grammatical_range)
        score.overall_band = round_ielts(
            (
                score.task_response
                + score.coherence_cohesion
                + score.lexical_resource
                + score.grammatical_range
            )
            / 4.0
        )
        return score, result

    async def score_speaking(
        self, *, transcript: str, part: int | None = None, weakness_summary: str = ""
    ) -> tuple[SpeakingScore, LLMResult]:
        messages = build_speaking_messages(transcript, part, weakness_summary)
        result = await self._provider.complete(
            messages=messages, json_object=True, temperature=0.2, max_tokens=800
        )
        if result.data is None:
            raise ScoringError("Provider did not return a JSON object")

        try:
            score = SpeakingScore.model_validate(result.data)
        except Exception as exc:  # noqa: BLE001 - normalize to domain error
            raise ScoringError(f"Invalid score payload: {exc}") from exc

        score.fluency_coherence = round_ielts(score.fluency_coherence)
        score.lexical_resource = round_ielts(score.lexical_resource)
        score.grammatical_range = round_ielts(score.grammatical_range)
        score.pronunciation = round_ielts(score.pronunciation)
        score.overall_band = round_ielts(
            (
                score.fluency_coherence
                + score.lexical_resource
                + score.grammatical_range
                + score.pronunciation
            )
            / 4.0
        )
        return score, result
