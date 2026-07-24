"""Adaptive difficulty + recommendations (SRS section 25).

Resolves the `adaptive` difficulty per module from recent performance and turns
the top weaknesses (from the weakness memory) into concrete next-actions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

from .analytics_controller import MODULES, _module_points
from .base import CamelModel
from .weakness_controller import WeaknessService

CONCRETE_DIFFICULTIES = ("easy", "medium", "hard")

# Human guidance for a weakness tag -> (title, action).
_TAG_GUIDANCE: dict[str, tuple[str, str]] = {
    "grammatical_range": ("Grammatical Range & Accuracy", "Practice complex sentence structures and review common grammar errors."),
    "lexical_resource": ("Lexical Resource", "Build topic vocabulary and practice paraphrasing."),
    "coherence_cohesion": ("Coherence & Cohesion", "Practice linking devices and clear paragraphing."),
    "task_response": ("Task Response", "Practice fully addressing every part of the prompt with developed ideas."),
    "fluency_coherence": ("Fluency & Coherence", "Do timed speaking drills to reduce hesitation and fillers."),
    "pronunciation": ("Pronunciation", "Practice minimal pairs, word stress and intonation."),
    "mcq": ("Multiple Choice", "Practice scanning for detail and eliminating distractors."),
    "true_false_notgiven": ("True/False/Not Given", "Practice distinguishing contradicted vs. absent information."),
    "matching_headings": ("Matching Headings", "Practice identifying paragraph main ideas."),
    "short_answer": ("Short Answer", "Practice locating precise answers and respecting word limits."),
    "sentence_completion": ("Sentence Completion", "Practice grammatical fit and keyword matching."),
    "form_completion": ("Form/Note Completion", "Practice catching numbers, names and spellings while listening."),
}


# ---------- Schemas ----------
class DifficultyItem(CamelModel):
    module: str
    difficulty: str
    recent_band: float | None
    rationale: str


class DifficultyResponse(CamelModel):
    modules: list[DifficultyItem]


class Recommendation(CamelModel):
    module: str
    tag: str
    title: str
    action: str
    severity: float
    difficulty: str


class RecommendationsResponse(CamelModel):
    items: list[Recommendation]
    message: str


async def resolve_difficulty(
    session: AsyncSession, user_id: str, module: str
) -> tuple[str, float | None, str]:
    """Resolve `adaptive` -> concrete difficulty from recent bands.

    Returns (difficulty, recent_band, rationale).
    """
    points = await _module_points(session, user_id, module)
    bands = [b for _, b in points][-5:]
    if not bands:
        return "medium", None, "No history yet; starting at medium."
    avg = sum(bands) / len(bands)
    if avg < 5.0:
        difficulty = "easy"
    elif avg <= 6.5:
        difficulty = "medium"
    else:
        difficulty = "hard"
    return difficulty, round(avg, 1), f"Recent average band {avg:.1f} maps to {difficulty}."


class AdaptiveController:
    @staticmethod
    async def difficulty_overview(
        session: AsyncSession, user: User
    ) -> DifficultyResponse:
        items: list[DifficultyItem] = []
        for module in MODULES:
            difficulty, recent, rationale = await resolve_difficulty(
                session, user.id, module
            )
            items.append(
                DifficultyItem(
                    module=module,
                    difficulty=difficulty,
                    recent_band=recent,
                    rationale=rationale,
                )
            )
        return DifficultyResponse(modules=items)

    @staticmethod
    async def recommendations(
        session: AsyncSession, user: User, limit: int = 5
    ) -> RecommendationsResponse:
        weaknesses = (await WeaknessService.list_for_user(session, user.id)).items
        top = weaknesses[:limit]
        items: list[Recommendation] = []
        for w in top:
            title, action = _TAG_GUIDANCE.get(
                w.tag, (w.tag.replace("_", " ").title(), "Targeted practice recommended.")
            )
            difficulty, _, _ = await resolve_difficulty(session, user.id, w.module)
            items.append(
                Recommendation(
                    module=w.module,
                    tag=w.tag,
                    title=title,
                    action=action,
                    severity=w.severity,
                    difficulty=difficulty,
                )
            )
        if items:
            message = "Focus on these areas to move toward your target band."
        else:
            message = (
                "No weaknesses detected yet. Complete a few practice sessions so we "
                "can personalize your plan."
            )
        return RecommendationsResponse(items=items, message=message)
