"""AI orchestrator: routes scoring/generation tasks to the active provider,
validates structured output, and returns typed results plus usage metadata."""

from __future__ import annotations

from pydantic import BaseModel, Field

import ai.prompts  # noqa: F401  (registers the templates)
from ai.prompts.registry import PromptTemplate, build as build_prompt
from ai.provider import LLMProvider, LLMResult
from ai.rubrics.writing_rubric import round_ielts


class WritingScore(BaseModel):
    task_response: float = Field(ge=0, le=9)
    coherence_cohesion: float = Field(ge=0, le=9)
    lexical_resource: float = Field(ge=0, le=9)
    grammatical_range: float = Field(ge=0, le=9)
    overall_band: float = Field(ge=0, le=9)
    feedback_summary: str
    improved_essay: str


class ScoreIssue(BaseModel):
    """One flagged stretch of the learner's own words.

    `quote` must be copied verbatim from the response; the API drops any quote
    it cannot find, so a model that paraphrases produces no highlight rather
    than a highlight pointing at the wrong words.
    """

    quote: str
    tag: str
    note: str


class SpeakingScore(BaseModel):
    fluency_coherence: float = Field(ge=0, le=9)
    lexical_resource: float = Field(ge=0, le=9)
    grammatical_range: float = Field(ge=0, le=9)
    pronunciation: float = Field(ge=0, le=9)
    overall_band: float = Field(ge=0, le=9)
    feedback_summary: str
    #: Optional: older providers and stricter models may omit it entirely.
    issues: list[ScoreIssue] = Field(default_factory=list)


def _stamp(result: LLMResult, template: PromptTemplate) -> None:
    """Record which prompt produced this call, alongside provider and model."""
    result.meta["promptId"] = template.id
    result.meta["promptVersion"] = template.version


class ScoringError(Exception):
    """Raised when the provider output cannot be parsed into a valid score."""


class AIOrchestrator:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def score_writing(
        self, *, essay: str, task_type: int, weakness_summary: str = ""
    ) -> tuple[WritingScore, LLMResult]:
        messages, template = build_prompt(
            "writing.score",
            essay=essay,
            task_type=task_type,
            weakness_summary=weakness_summary,
        )
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
        _stamp(result, template)
        return score, result

    async def score_speaking(
        self, *, transcript: str, part: int | None = None, weakness_summary: str = ""
    ) -> tuple[SpeakingScore, LLMResult]:
        messages, template = build_prompt(
            "speaking.score",
            transcript=transcript,
            part=part,
            weakness_summary=weakness_summary,
        )
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
        _stamp(result, template)
        return score, result

    async def generate_content(
        self, *, kind: str, **kwargs: object
    ) -> tuple[BaseModel, LLMResult]:
        """Generate one practice item and validate it against its schema.

        A malformed item is a ScoringError like any other parse failure. The
        alternative -- storing whatever came back -- means a reviewer opens a
        draft with a missing answer field and cannot tell whether the model
        failed or the code did.
        """
        from ai.generation import PROMPT_IDS, SCHEMAS  # noqa: PLC0415

        if kind not in SCHEMAS:
            raise ScoringError(f"Unknown generation kind: {kind}")

        messages, template = build_prompt(PROMPT_IDS[kind], **kwargs)
        result = await self._provider.complete(
            messages=messages,
            json_object=True,
            # Higher than scoring, deliberately. Scoring wants the same answer
            # every time; content generation wants variety, and 0.2 produces
            # ten passages about renewable energy.
            temperature=0.8,
            max_tokens=1600,
        )
        if result.data is None:
            raise ScoringError("Provider did not return a JSON object")

        try:
            item = SCHEMAS[kind].model_validate(result.data)
        except Exception as exc:  # noqa: BLE001 - normalise to domain error
            raise ScoringError(f"Invalid generated {kind}: {exc}") from exc

        _stamp(result, template)
        return item, result
