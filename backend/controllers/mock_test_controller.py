"""Full mock test: four timed sections, one overall band, one readiness verdict.

Each section is submitted through its own module controller rather than being
graded here, so a mock test produces real attempts and feeds history, trends and
weakness tracking exactly like ordinary practice. Duplicating the grading would
mean two implementations to keep in step, and the mock test would silently
diverge from the practice it is meant to rehearse.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from core.predictor import round_half
from models.content import AudioClip, Passage
from models.cue_card import CueCard
from models.mock_test import MockTest
from models.profile import LearnerProfile
from models.user import User
from models.writing_prompt import WritingPrompt

from .base import CamelModel
from .listening_controller import ListeningController, ListeningSubmitRequest
from .listening_controller import _ensure_seeded as _ensure_listening_seeded
from .reading_controller import ReadingController, ReadingSubmitRequest
from .reading_controller import _ensure_seeded as _ensure_reading_seeded
from .speaking_controller import SpeakingSubmitRequest, SpeakingController
from .speaking_controller import _ensure_cue_cards_seeded
from .writing_controller import WritingController, WritingSubmitRequest
from .writing_controller import _ensure_prompts_seeded

logger = logging.getLogger("api.mock_test")

MODULES = ("listening", "reading", "writing", "speaking")

#: Real IELTS section allowances, in minutes.
SECTION_MINUTES = {"listening": 30, "reading": 60, "writing": 60, "speaking": 14}

#: How close to target counts as "on track".
ON_TRACK_MARGIN = 0.5


class MockSection(CamelModel):
    module: str
    minutes: int


class MockTestOut(CamelModel):
    id: str
    status: str
    sections: list[MockSection]
    passage_id: str | None
    clip_id: str | None
    writing_prompt_id: str | None
    cue_card_id: str | None
    total_minutes: int


class MockSubmission(CamelModel):
    reading_answers: dict[str, str] = {}
    listening_answers: dict[str, str] = {}
    writing_text: str | None = None
    speaking_text: str | None = None


class ModuleReadiness(CamelModel):
    module: str
    band: float | None
    gap: float | None
    verdict: str


class ReadinessReport(CamelModel):
    overall_band: float | None
    target_band: float
    verdict: str
    headline: str
    modules: list[ModuleReadiness]
    weakest_module: str | None
    advice: str


class MockResultOut(CamelModel):
    id: str
    status: str
    overall_band: float | None
    readiness: ReadinessReport


class MockTestController:
    @staticmethod
    async def start(session: AsyncSession, user: User) -> MockTestOut:
        await _ensure_reading_seeded(session)
        await _ensure_listening_seeded(session)
        await _ensure_prompts_seeded(session)
        await _ensure_cue_cards_seeded(session)

        passage = await session.scalar(
            select(Passage).order_by(func.random()).limit(1)
        )
        clip = await session.scalar(
            select(AudioClip).order_by(func.random()).limit(1)
        )
        prompt = await session.scalar(
            select(WritingPrompt)
            .where(WritingPrompt.task_number == 2)
            .order_by(func.random())
            .limit(1)
        )
        cue_card = await session.scalar(
            select(CueCard).order_by(func.random()).limit(1)
        )
        if passage is None or clip is None or prompt is None or cue_card is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Mock test content is not available yet",
            )

        test = MockTest(
            user_id=user.id,
            passage_id=passage.id,
            clip_id=clip.id,
            writing_prompt_id=prompt.id,
            cue_card_id=cue_card.id,
        )
        session.add(test)
        await session.flush()

        return _to_out(test)

    @staticmethod
    async def submit(
        session: AsyncSession,
        user: User,
        test_id: str,
        payload: MockSubmission,
        orchestrator: AIOrchestrator,
    ) -> MockResultOut:
        test = await session.scalar(
            select(MockTest).where(MockTest.id == test_id)
        )
        if test is None or test.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Mock test not found"
            )
        if test.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This mock test has already been submitted",
            )

        # Each section goes through its own controller, so real attempts are
        # created and everything downstream updates.
        if payload.reading_answers and test.passage_id:
            result = await ReadingController.submit(
                session,
                user,
                ReadingSubmitRequest(
                    passage_id=test.passage_id, answers=payload.reading_answers
                ),
            )
            test.reading_band = result.band

        if payload.listening_answers and test.clip_id:
            result = await ListeningController.submit(
                session,
                user,
                ListeningSubmitRequest(
                    audio_id=test.clip_id, answers=payload.listening_answers
                ),
            )
            test.listening_band = result.band

        if payload.writing_text and payload.writing_text.strip():
            written = await WritingController.submit(
                session,
                user,
                orchestrator,
                WritingSubmitRequest(essay_text=payload.writing_text, task_type=2),
            )
            test.writing_band = written.overall_band

        if payload.speaking_text and payload.speaking_text.strip():
            spoken = await SpeakingController.submit(
                session,
                user,
                orchestrator,
                SpeakingSubmitRequest(transcript=payload.speaking_text, part=2),
            )
            test.speaking_band = spoken.overall_band

        bands = {
            "reading": test.reading_band,
            "listening": test.listening_band,
            "writing": test.writing_band,
            "speaking": test.speaking_band,
        }
        measured = [b for b in bands.values() if b is not None]
        test.overall_band = (
            round_half(sum(measured) / len(measured)) if measured else None
        )

        profile = await session.scalar(
            select(LearnerProfile).where(LearnerProfile.user_id == user.id)
        )
        target = profile.target_band if profile else 7.0

        report = _readiness(bands, test.overall_band, target)
        test.readiness = report.model_dump(by_alias=True)
        test.status = "completed"
        test.completed_at = datetime.now(tz=timezone.utc)

        logger.info(
            "mock test completed",
            extra={
                "userId": user.id,
                "overall": test.overall_band,
                "verdict": report.verdict,
            },
        )
        return MockResultOut(
            id=test.id,
            status=test.status,
            overall_band=test.overall_band,
            readiness=report,
        )

    @staticmethod
    async def history(session: AsyncSession, user: User) -> list[MockResultOut]:
        rows = (
            await session.execute(
                select(MockTest)
                .where(MockTest.user_id == user.id, MockTest.status == "completed")
                .order_by(MockTest.completed_at.desc())
                .limit(10)
            )
        ).scalars().all()
        return [
            MockResultOut(
                id=row.id,
                status=row.status,
                overall_band=row.overall_band,
                readiness=ReadinessReport.model_validate(row.readiness),
            )
            for row in rows
            if isinstance(row.readiness, dict)
        ]


def _to_out(test: MockTest) -> MockTestOut:
    sections = [
        MockSection(module=module, minutes=SECTION_MINUTES[module])
        for module in MODULES
    ]
    return MockTestOut(
        id=test.id,
        status=test.status,
        sections=sections,
        passage_id=test.passage_id,
        clip_id=test.clip_id,
        writing_prompt_id=test.writing_prompt_id,
        cue_card_id=test.cue_card_id,
        total_minutes=sum(SECTION_MINUTES.values()),
    )


def _readiness(
    bands: dict[str, float | None], overall: float | None, target: float
) -> ReadinessReport:
    """Turn four bands into a verdict the learner can act on."""
    modules: list[ModuleReadiness] = []
    for module in MODULES:
        band = bands.get(module)
        if band is None:
            modules.append(
                ModuleReadiness(
                    module=module,
                    band=None,
                    gap=None,
                    verdict="Not attempted",
                )
            )
            continue
        gap = round_half(target - band)
        if gap <= 0:
            verdict = "At or above target"
        elif gap <= ON_TRACK_MARGIN:
            verdict = "Within reach"
        elif gap <= 1.0:
            verdict = "Needs work"
        else:
            verdict = "Priority"
        modules.append(
            ModuleReadiness(module=module, band=band, gap=gap, verdict=verdict)
        )

    scored = [m for m in modules if m.band is not None]
    weakest = min(scored, key=lambda m: m.band or 0).module if scored else None
    skipped = [m.module for m in modules if m.band is None]

    if overall is None:
        return ReadinessReport(
            overall_band=None,
            target_band=target,
            verdict="Not measured",
            headline="Nothing was submitted, so there is no result to report.",
            modules=modules,
            weakest_module=None,
            advice="Complete at least one section to get a readiness estimate.",
        )

    gap = round_half(target - overall)

    # The worst section, not just the average, decides the verdict. Most
    # institutions set a minimum per band as well as an overall, and telling
    # someone they are "Ready" on a 9.0/5.0 split that averages to target would
    # be actively misleading.
    worst_gap = max(
        (round_half(target - m.band) for m in modules if m.band is not None),
        default=0.0,
    )
    effective_gap = max(gap, worst_gap)

    if effective_gap <= 0:
        verdict = "Ready"
    elif effective_gap <= ON_TRACK_MARGIN:
        verdict = "Nearly ready"
    elif effective_gap <= 1.0:
        verdict = "Not yet"
    else:
        verdict = "Early days"

    if gap <= 0:
        headline = (
            f"You scored band {overall:.1f}, at or above your target of "
            f"{target:.1f}."
        )
    else:
        headline = (
            f"Band {overall:.1f}, {gap:.1f} below your {target:.1f} target."
        )
    if worst_gap > gap and weakest is not None:
        # Say why the verdict is harsher than the average suggests.
        headline += (
            f" Your overall is carried by stronger sections — {weakest} is "
            f"{worst_gap:.1f} below target on its own."
        )

    advice = (
        f"Your weakest section is {weakest}. Put your next few sessions there."
        if weakest and effective_gap > 0
        else "Keep practising across all four sections to hold this level."
    )
    if skipped:
        # Stated rather than buried: an overall built from two sections is not
        # comparable to one built from four.
        advice += (
            " Note: "
            + ", ".join(skipped)
            + (" was" if len(skipped) == 1 else " were")
            + " not attempted, so this overall is based on "
            + f"{len(scored)} of 4 sections."
        )

    return ReadinessReport(
        overall_band=overall,
        target_band=target,
        verdict=verdict,
        headline=headline,
        modules=modules,
        weakest_module=weakest,
        advice=advice,
    )
