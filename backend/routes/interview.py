"""Spoken speaking test routes.

Answers arrive as text regardless of how they were produced, so the on-device
Android recogniser works today and a server-side streaming provider can be
added later without changing this surface.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from controllers.interview_controller import (
    AnswerRequest,
    InterviewController,
    InterviewSessionOut,
)
from controllers.speaking_controller import SpeakingResultResponse
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
