"""Spoken speaking test: session orchestration.

Holds the exam together but owns none of its rules. The sequence lives in
`core.interview`, scoring lives in the speaking controller, and the questions
come from the existing bank. This layer only persists what happened and hands
the finished transcript to the scorer that already exists.

Deliberately transport-agnostic. Answers arrive as text, whether the phone's own
recogniser produced them or a server-side model did, so the on-device path works
today and a streaming provider can be added without this file changing.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataclasses import dataclass

from fastapi import UploadFile

from ai.orchestrator import AIOrchestrator
from ai.voice_providers import SpendLimitExceeded, build_stt, build_tts
from core.errors import AppError, NotFoundError, ValidationError
from core.interview import (
    CueCard as ScriptCueCard,
    Interview,
    InterviewScript,
    Phase,
    Speaker,
    Turn,
)
from db.repository import OwnedRepository
from models.cue_card import CueCard
from models.interview import InterviewSession
from models.speaking_question import SpeakingQuestion
from models.user import User

from .base import CamelModel
from .speaking_controller import (
    SpeakingController,
    SpeakingSubmitRequest,
    _ensure_cue_cards_seeded,
)
from .speaking_questions import ensure_seeded

_sessions = OwnedRepository(InterviewSession, label="Interview session")

#: How many questions each part draws. Part 1 is deliberately longer: it is
#: several short exchanges across a few topics, not one long answer.
PART1_COUNT = 8
PART3_COUNT = 5

#: Recognised transcript sources. Recorded rather than inferred so a poor score
#: can be traced to a poor transcription.
TRANSCRIPT_SOURCES = ("android-device", "server-stt", "typed", "unknown")

#: Refused above this. A 12-minute exam answer is well under a megabyte at any
#: sane bitrate, so anything larger is a misconfigured recorder -- and an
#: unbounded upload is both a transcription bill and a denial-of-service.
MAX_AUDIO_BYTES = 10 * 1024 * 1024


# ---------- Schemas ----------
class ActionOut(CamelModel):
    kind: str
    phase: str
    text: str
    duration_seconds: int | None
    bullets: list[str]


class InterviewProgress(CamelModel):
    phase: str
    phase_index: int
    phase_count: int
    question_index: int
    answered: int


class InterviewSessionOut(CamelModel):
    id: str
    phase: str
    action: ActionOut
    progress: InterviewProgress
    is_complete: bool
    speaking_attempt_id: str | None = None


@dataclass
class QuestionAudio:
    audio: bytes
    mime_type: str
    provider: str


class VoiceUnavailableError(AppError):
    """The audio path failed for a reason the learner can act on.

    Distinct from a generic 500: "the transcription service is down" and "your
    recording was empty" need different responses from the app, and neither is
    a bug the learner can do anything about if it is reported as a crash.
    """

    status = 503
    code = "voice_unavailable"
    title = "Voice service unavailable"


class AnswerRequest(CamelModel):
    #: The candidate's words. Empty is valid -- saying nothing is an answer,
    #: and a poor one the scorer should see.
    text: str = ""
    #: Where the text came from. Rejected if unknown rather than stored blindly,
    #: because this field's whole purpose is to be trustworthy later.
    source: str = "android-device"


# ---------- Script construction ----------
async def _build_script(
    session: AsyncSession, difficulty: str | None
) -> InterviewScript:
    """Draw a full exam from the question bank.

    Part 1 and Part 3 questions are drawn per part, never mixed: a Part 3
    question asked in Part 1 would be scored against the wrong expectations.
    """
    # Both banks, because an interview needs Part 1/3 questions *and* a cue
    # card. Seeding used to happen only when their own endpoints were hit, so
    # an interview was the first thing that could ask for a cue card before
    # anything had created one.
    await ensure_seeded(session)
    await _ensure_cue_cards_seeded(session)

    async def draw(part: int, count: int) -> tuple[str, ...]:
        query = select(SpeakingQuestion).where(SpeakingQuestion.part == part)
        if difficulty and difficulty != "adaptive":
            query = query.where(SpeakingQuestion.difficulty == difficulty)
        rows = list(await session.scalars(query))
        if not rows:
            # Relax difficulty, never the part.
            rows = list(
                await session.scalars(
                    select(SpeakingQuestion).where(SpeakingQuestion.part == part)
                )
            )
        if not rows:
            raise NotFoundError(f"No Part {part} questions available")

        # Grouped by topic and drawn topic-first, because a real Part 1 works
        # through a few subjects rather than hopping between eight of them.
        by_topic: dict[str, list[SpeakingQuestion]] = {}
        for row in rows:
            by_topic.setdefault(row.topic, []).append(row)

        picked: list[str] = []
        for topic in random.sample(list(by_topic), k=len(by_topic)):
            for question in sorted(by_topic[topic], key=lambda q: q.order_index):
                picked.append(question.question)
                if len(picked) >= count:
                    return tuple(picked)
        return tuple(picked)

    cards = list(await session.scalars(select(CueCard)))
    if not cards:
        raise NotFoundError("No cue cards available")
    card = random.choice(cards)
    bullets = tuple(str(b) for b in (card.bullet_points or ()))
    if not bullets:
        raise NotFoundError("The selected cue card has no bullet points")

    return InterviewScript(
        part1=await draw(1, PART1_COUNT),
        cue_card=ScriptCueCard(
            topic=card.topic, prompt=card.prompt, bullets=bullets
        ),
        part2_followup=f"Thank you. Do you often think about {card.topic}?",
        part3=await draw(3, PART3_COUNT),
    )


def _script_to_json(script: InterviewScript) -> dict[str, object]:
    return {
        "part1": list(script.part1),
        "cueCard": {
            "topic": script.cue_card.topic,
            "prompt": script.cue_card.prompt,
            "bullets": list(script.cue_card.bullets),
        },
        "part2Followup": script.part2_followup,
        "part3": list(script.part3),
    }


def _script_from_json(raw: dict) -> InterviewScript:
    card = raw["cueCard"]
    return InterviewScript(
        part1=tuple(raw["part1"]),
        cue_card=ScriptCueCard(
            topic=card["topic"],
            prompt=card["prompt"],
            bullets=tuple(card["bullets"]),
        ),
        part2_followup=raw["part2Followup"],
        part3=tuple(raw["part3"]),
    )


def _load(row: InterviewSession) -> Interview:
    """Rebuild the machine from a stored row.

    The row is state, not behaviour: the rules are re-applied from
    core.interview every time, so a rule change takes effect on sessions that
    are already in progress rather than only on new ones.
    """
    exam = Interview(script=_script_from_json(row.script))
    exam.phase = Phase(row.phase)
    exam.turns = [
        Turn(speaker=Speaker(t["speaker"]), text=t["text"], phase=Phase(t["phase"]))
        for t in (row.turns or [])
    ]
    exam._cursor = row.cursor
    return exam


def _save(row: InterviewSession, exam: Interview) -> None:
    row.phase = exam.phase.value
    row.turns = [
        {"speaker": t.speaker.value, "text": t.text, "phase": t.phase.value}
        for t in exam.turns
    ]
    row.cursor = exam._cursor


def _to_out(row: InterviewSession, exam: Interview) -> InterviewSessionOut:
    action = exam.current_action()
    return InterviewSessionOut(
        id=row.id,
        phase=exam.phase.value,
        action=ActionOut(**action.to_dict()),
        progress=InterviewProgress(**exam.progress()),
        is_complete=exam.is_complete,
        speaking_attempt_id=row.speaking_attempt_id,
    )


class InterviewController:
    @staticmethod
    async def start(
        session: AsyncSession, user: User, difficulty: str | None = None
    ) -> InterviewSessionOut:
        script = await _build_script(session, difficulty)
        exam = Interview(script=script)

        row = InterviewSession(
            user_id=user.id,
            phase=exam.phase.value,
            script=_script_to_json(script),
            turns=[],
            cursor=0,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _to_out(row, exam)

    @staticmethod
    async def get(
        session: AsyncSession, user: User, session_id: str
    ) -> InterviewSessionOut:
        row = await _sessions.get_owned(session, session_id, user.id)
        return _to_out(row, _load(row))

    @staticmethod
    async def answer(
        session: AsyncSession, user: User, session_id: str, payload: AnswerRequest
    ) -> InterviewSessionOut:
        if payload.source not in TRANSCRIPT_SOURCES:
            raise ValidationError(
                f"Unknown transcript source '{payload.source}'; "
                f"expected one of {', '.join(TRANSCRIPT_SOURCES)}"
            )

        row = await _sessions.get_owned(session, session_id, user.id)
        exam = _load(row)
        if exam.is_complete:
            raise ValidationError("This interview has already finished")

        exam.answer(payload.text)
        _save(row, exam)
        row.transcript_source = payload.source
        await session.commit()
        await session.refresh(row)
        return _to_out(row, exam)

    @staticmethod
    async def skip_preparation(
        session: AsyncSession, user: User, session_id: str
    ) -> InterviewSessionOut:
        row = await _sessions.get_owned(session, session_id, user.id)
        exam = _load(row)
        try:
            exam.skip_preparation()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        _save(row, exam)
        await session.commit()
        await session.refresh(row)
        return _to_out(row, exam)

    @staticmethod
    async def score(
        session: AsyncSession,
        user: User,
        orchestrator: AIOrchestrator,
        session_id: str,
    ):
        """Score the finished exam through the existing speaking scorer.

        Part 2 is submitted rather than the whole conversation: the long turn is
        the sustained, uninterrupted speech the band descriptors are written
        about, and concatenating three parts would blur eight short Part 1
        answers into it.
        """
        row = await _sessions.get_owned(session, session_id, user.id)
        exam = _load(row)

        if exam.phase not in (Phase.SCORING, Phase.COMPLETE):
            raise ValidationError(
                "The interview is not finished yet; answer the remaining questions first"
            )
        if row.speaking_attempt_id:
            raise ValidationError("This interview has already been scored")

        transcript = exam.transcript_for(2).strip() or exam.full_transcript().strip()
        if not transcript:
            raise ValidationError(
                "Nothing was said during the interview, so there is nothing to score"
            )

        result = await SpeakingController.submit(
            session,
            user,
            orchestrator,
            SpeakingSubmitRequest(transcript=transcript, part=2),
        )

        row.speaking_attempt_id = result.attempt_id
        row.phase = Phase.COMPLETE.value
        row.completed_at = datetime.now(tz=timezone.utc)
        await session.commit()
        return result

    @staticmethod
    async def answer_with_audio(
        session: AsyncSession, user: User, session_id: str, upload: UploadFile
    ) -> InterviewSessionOut:
        """Transcribe an uploaded answer, then advance the exam."""
        row = await _sessions.get_owned(session, session_id, user.id)
        exam = _load(row)
        if exam.is_complete:
            raise ValidationError("This interview has already finished")

        audio = await upload.read()
        if not audio:
            raise ValidationError("The recording was empty")
        if len(audio) > MAX_AUDIO_BYTES:
            raise ValidationError(
                f"Recording is too large ({len(audio) // 1024} KB); "
                f"the limit is {MAX_AUDIO_BYTES // 1024} KB"
            )

        stt = build_stt()
        try:
            transcript = await stt.transcribe(
                audio, mime_type=upload.content_type or "audio/wav"
            )
        except Exception as exc:  # noqa: BLE001 - normalise to a domain error
            raise VoiceUnavailableError(
                f"Could not transcribe the recording ({type(exc).__name__})"
            ) from exc

        # An unrecognisable recording still advances the exam. The alternative
        # is a candidate stuck on one question with no way forward, which on a
        # timed test is worse than a turn scored as silence.
        exam.answer(transcript.text)
        _save(row, exam)
        row.transcript_source = (
            "server-stt" if stt.name != "mock" else "unknown"
        )
        await session.commit()
        await session.refresh(row)
        return _to_out(row, exam)

    @staticmethod
    async def question_audio(
        session: AsyncSession, user: User, session_id: str
    ) -> QuestionAudio:
        """Synthesise whatever the examiner should say right now."""
        row = await _sessions.get_owned(session, session_id, user.id)
        exam = _load(row)
        action = exam.current_action()

        text = action.text.strip()
        if not text:
            raise ValidationError("There is nothing for the examiner to say")

        tts = build_tts()
        try:
            speech = await tts.synthesize(text)
        except SpendLimitExceeded as exc:
            # Surfaced rather than swallowed. The exam can still be taken by
            # reading the question on screen, and a silent failure here would
            # look like a broken app instead of an exhausted budget.
            raise VoiceUnavailableError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise VoiceUnavailableError(
                f"Could not synthesise the question ({type(exc).__name__})"
            ) from exc

        return QuestionAudio(
            audio=speech.audio, mime_type=speech.mime_type, provider=speech.provider
        )
