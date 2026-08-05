"""Spoken speaking test routes.

Answers arrive as text regardless of how they were produced, so the on-device
Android recogniser works today and a server-side streaming provider can be
added later without changing this surface.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from controllers.interview_controller import (
    AnswerRequest,
    InterviewController,
    InterviewSessionOut,
)
from controllers.speaking_controller import SpeakingResultResponse
from controllers.interview_controller import QuestionAudio
from db.session import get_db
from dependencies import get_current_user, get_orchestrator
from models.user import User

router = APIRouter(prefix="/interview", tags=["interview"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Orchestrator = Annotated[AIOrchestrator, Depends(get_orchestrator)]


@router.post(
    "/sessions",
    response_model=InterviewSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def start(
    session: DbSession, user: CurrentUser, difficulty: str | None = None
) -> InterviewSessionOut:
    return await InterviewController.start(session, user, difficulty)


@router.get("/sessions/{session_id}", response_model=InterviewSessionOut)
async def get_session(
    session_id: str, session: DbSession, user: CurrentUser
) -> InterviewSessionOut:
    """Re-read the current instruction.

    Safe to call repeatedly: it does not advance the exam, so a client that
    dropped mid-question can recover it instead of skipping ahead.
    """
    return await InterviewController.get(session, user, session_id)


@router.post("/sessions/{session_id}/answer", response_model=InterviewSessionOut)
async def answer(
    session_id: str, payload: AnswerRequest, session: DbSession, user: CurrentUser
) -> InterviewSessionOut:
    return await InterviewController.answer(session, user, session_id, payload)


@router.post("/sessions/{session_id}/skip-prep", response_model=InterviewSessionOut)
async def skip_preparation(
    session_id: str, session: DbSession, user: CurrentUser
) -> InterviewSessionOut:
    """Start the long turn before the preparation minute is up."""
    return await InterviewController.skip_preparation(session, user, session_id)


@router.post("/sessions/{session_id}/score", response_model=SpeakingResultResponse)
async def score(
    session_id: str,
    session: DbSession,
    user: CurrentUser,
    orchestrator: Orchestrator,
) -> SpeakingResultResponse:
    return await InterviewController.score(session, user, orchestrator, session_id)


@router.post("/sessions/{session_id}/answer-audio", response_model=InterviewSessionOut)
async def answer_with_audio(
    session_id: str,
    session: DbSession,
    user: CurrentUser,
    audio: UploadFile = File(...),
) -> InterviewSessionOut:
    """Upload a recorded answer; the server transcribes it and advances.

    Separate from the text endpoint rather than one endpoint with an optional
    body: the failure modes are entirely different. This one can fail because
    the audio is unreadable or the provider is down, and a client needs to tell
    that apart from an answer the examiner simply did not accept.
    """
    return await InterviewController.answer_with_audio(
        session, user, session_id, audio
    )


@router.get("/sessions/{session_id}/question-audio")
async def question_audio(
    session_id: str, session: DbSession, user: CurrentUser
) -> Response:
    """Speak the current question.

    Returns audio bytes rather than a URL because the audio is short, already
    cached server-side, and a signed-URL round trip would add a hop for no
    benefit. Cached responses are marked so a client can tell a free replay
    from a billed synthesis.
    """
    result: QuestionAudio = await InterviewController.question_audio(
        session, user, session_id
    )
    return Response(
        content=result.audio,
        media_type=result.mime_type,
        headers={
            "X-TTS-Provider": result.provider,
            # Long-lived: the question bank is fixed, so this byte stream will
            # not change for this text.
            "Cache-Control": "private, max-age=86400",
        },
    )
