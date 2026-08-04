"""Adaptive placement diagnostic: a short sitting that sets the baselines.

Reading and Listening are graded deterministically from the answer key, so they
cost nothing and are exact. Writing and Speaking need the AI, and both are
optional: a learner who skips them gets a null baseline for that module rather
than a number invented from nothing. A fabricated starting band would poison
every prediction and recommendation built on top of it.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator, ScoringError
from core.band_mapping import listening_band, reading_band
from core.cefr import band_to_cefr, cefr_description
from core.errors import ContentUnavailableError
from core.predictor import round_half
from models.content import AudioClip, ListeningQuestion, Passage, Question
from models.profile import LearnerProfile
from models.user import User
from models.writing_prompt import WritingPrompt

from .base import CamelModel
from .grading import is_correct
from .listening_controller import _ensure_seeded as _ensure_listening_seeded
from .reading_controller import _ensure_seeded as _ensure_reading_seeded
from .writing_controller import _ensure_prompts_seeded

logger = logging.getLogger("api.diagnostic")

#: Kept short on purpose. A placement test people abandon halfway measures
#: nothing, so this is sized to be finished in one sitting.
READING_QUESTIONS = 3
LISTENING_QUESTIONS = 3
MIN_WRITING_WORDS = 40
MIN_SPEAKING_WORDS = 30


class DiagnosticQuestion(CamelModel):
    id: str
    type: str
    prompt: str
    options: list[str] | None


class DiagnosticReading(CamelModel):
    passage_id: str
    title: str
    body: str
    questions: list[DiagnosticQuestion]


class DiagnosticListening(CamelModel):
    clip_id: str
    title: str
    audio_url: str
    duration_sec: int
    questions: list[DiagnosticQuestion]


class DiagnosticWriting(CamelModel):
    prompt_id: str
    prompt: str
    min_words: int


class DiagnosticSpeaking(CamelModel):
    prompt: str
    min_words: int


class DiagnosticSet(CamelModel):
    reading: DiagnosticReading
    listening: DiagnosticListening
    writing: DiagnosticWriting
    speaking: DiagnosticSpeaking
    note: str


class DiagnosticSubmission(CamelModel):
    reading_answers: dict[str, str] = {}
    listening_answers: dict[str, str] = {}
    #: Optional. Omitted or blank means "not attempted", not "scored zero".
    writing_text: str | None = None
    speaking_text: str | None = None


class ModuleBaseline(CamelModel):
    module: str
    band: float | None
    #: Why this number exists, or why it does not.
    detail: str


class DiagnosticResult(CamelModel):
    baselines: list[ModuleBaseline]
    overall_band: float | None
    cefr_level: str | None
    cefr_description: str
    summary: str


def _public(question: Question | ListeningQuestion) -> DiagnosticQuestion:
    return DiagnosticQuestion(
        id=question.id,
        type=question.type,
        prompt=question.prompt,
        options=list(question.options) if question.options else None,
    )


class DiagnosticController:
    @staticmethod
    async def get_set(session: AsyncSession) -> DiagnosticSet:
        """Assemble one short sitting across all four modules."""
        # The content banks seed lazily when their own endpoints are first hit,
        # and the diagnostic reads the tables directly - so a learner who starts
        # here before practising anything would otherwise find them empty.
        await _ensure_reading_seeded(session)
        await _ensure_listening_seeded(session)
        await _ensure_prompts_seeded(session)

        # Medium content: a placement test should start at the middle of the
        # scale, since starting easy or hard biases the first measurement.
        passage = await session.scalar(
            select(Passage)
            .where(Passage.difficulty == "medium")
            .order_by(func.random())
            .limit(1)
        )
        clip = await session.scalar(
            select(AudioClip)
            .where(AudioClip.difficulty == "medium")
            .order_by(func.random())
            .limit(1)
        )
        prompt = await session.scalar(
            select(WritingPrompt)
            .where(WritingPrompt.task_number == 2)
            .order_by(func.random())
            .limit(1)
        )
        if passage is None or clip is None or prompt is None:
            raise ContentUnavailableError("Diagnostic content is not available yet")

        reading_questions = (
            await session.execute(
                select(Question)
                .where(Question.passage_id == passage.id)
                .order_by(Question.order_index)
                .limit(READING_QUESTIONS)
            )
        ).scalars().all()
        listening_questions = (
            await session.execute(
                select(ListeningQuestion)
                .where(ListeningQuestion.audio_id == clip.id)
                .order_by(ListeningQuestion.order_index)
                .limit(LISTENING_QUESTIONS)
            )
        ).scalars().all()

        return DiagnosticSet(
            reading=DiagnosticReading(
                passage_id=passage.id,
                title=passage.title,
                body=passage.body,
                questions=[_public(q) for q in reading_questions],
            ),
            listening=DiagnosticListening(
                clip_id=clip.id,
                title=clip.title,
                audio_url=f"/media/{clip.object_key}",
                duration_sec=clip.duration_sec,
                questions=[_public(q) for q in listening_questions],
            ),
            writing=DiagnosticWriting(
                prompt_id=prompt.id,
                prompt=prompt.prompt,
                min_words=MIN_WRITING_WORDS,
            ),
            speaking=DiagnosticSpeaking(
                prompt="Describe a place you enjoy spending time in, and explain why.",
                min_words=MIN_SPEAKING_WORDS,
            ),
            note=(
                "Reading and Listening are marked instantly. Writing and Speaking "
                "are optional — skip them and we simply will not estimate those "
                "two yet."
            ),
        )

    @staticmethod
    async def submit(
        session: AsyncSession,
        user: User,
        payload: DiagnosticSubmission,
        orchestrator: AIOrchestrator,
    ) -> DiagnosticResult:
        baselines: list[ModuleBaseline] = []

        reading = await _grade_objective(
            session,
            Question,
            payload.reading_answers,
            lambda raw, total: reading_band(raw, total, "academic"),
        )
        listening = await _grade_objective(
            session, ListeningQuestion, payload.listening_answers, listening_band
        )

        baselines.append(
            ModuleBaseline(
                module="reading",
                band=reading[0],
                detail=reading[1],
            )
        )
        baselines.append(
            ModuleBaseline(
                module="listening",
                band=listening[0],
                detail=listening[1],
            )
        )

        writing_band = await _score_free_text(
            orchestrator, payload.writing_text, MIN_WRITING_WORDS, "writing"
        )
        speaking_band = await _score_free_text(
            orchestrator, payload.speaking_text, MIN_SPEAKING_WORDS, "speaking"
        )
        baselines.append(
            ModuleBaseline(
                module="writing",
                band=writing_band[0],
                detail=writing_band[1],
            )
        )
        baselines.append(
            ModuleBaseline(
                module="speaking",
                band=speaking_band[0],
                detail=speaking_band[1],
            )
        )

        measured = [b.band for b in baselines if b.band is not None]
        overall = round_half(sum(measured) / len(measured)) if measured else None
        level = band_to_cefr(overall)

        # Persist so the rest of the app can use the starting point.
        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == user.id)
        )
        if profile is not None:
            profile.baseline_reading = baselines[0].band
            profile.baseline_listening = baselines[1].band
            profile.baseline_writing = baselines[2].band
            profile.baseline_speaking = baselines[3].band
            profile.cefr_level = level

        logger.info(
            "diagnostic completed",
            extra={"userId": user.id, "overall": overall, "cefr": level},
        )

        if overall is None:
            summary = (
                "Nothing was answered, so there is no starting point yet. "
                "Complete a practice in any module to begin."
            )
        else:
            skipped = [b.module for b in baselines if b.band is None]
            summary = f"Your starting point is around band {overall:.1f}."
            if skipped:
                summary += (
                    " "
                    + ", ".join(m.capitalize() for m in skipped)
                    + (" was" if len(skipped) == 1 else " were")
                    + " not attempted, so "
                    + ("it is" if len(skipped) == 1 else "they are")
                    + " excluded rather than guessed."
                )

        return DiagnosticResult(
            baselines=baselines,
            overall_band=overall,
            cefr_level=level,
            cefr_description=cefr_description(level),
            summary=summary,
        )


async def _grade_objective(
    session: AsyncSession,
    model: type[Question] | type[ListeningQuestion],
    answers: dict[str, str],
    to_band: object,
) -> tuple[float | None, str]:
    """Grade a submitted answer map against the stored key."""
    if not answers:
        return None, "Not attempted."

    rows = (
        await session.execute(select(model).where(model.id.in_(list(answers))))
    ).scalars().all()
    if not rows:
        return None, "Not attempted."

    raw = sum(1 for row in rows if is_correct(answers.get(row.id), row.correct_answer))
    total = len(rows)
    band = round_half(to_band(raw, total))  # type: ignore[operator]
    return band, f"{raw} of {total} correct."


async def _score_free_text(
    orchestrator: AIOrchestrator,
    text: str | None,
    min_words: int,
    module: str,
) -> tuple[float | None, str]:
    """Score a written or spoken response, or report why it was not scored."""
    if not text or not text.strip():
        return None, "Skipped — no estimate made."

    words = len(text.split())
    if words < min_words:
        # Too short to judge. Scoring it anyway would record a low baseline the
        # learner never really earned, and everything downstream inherits it.
        return None, f"Too short to score ({words} of {min_words} words)."

    try:
        if module == "writing":
            score, _ = await orchestrator.score_writing(essay=text, task_type=2)
        else:
            score, _ = await orchestrator.score_speaking(transcript=text, part=2)
    except ScoringError:
        logger.warning("diagnostic scoring failed", extra={"module": module})
        return None, "Could not be scored automatically."

    return round_half(score.overall_band), "Scored by the AI examiner."
