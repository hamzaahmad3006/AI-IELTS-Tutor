"""Speaking routes: submit a transcript for AI scoring and fetch the result."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from controllers.speaking_controller import (
    SpeakingController,
    SpeakingResultResponse,
    SpeakingSubmitRequest,
)
from db.session import get_db
from dependencies import get_current_user, get_orchestrator
from models.user import User

router = APIRouter(prefix="/speaking", tags=["speaking"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Orchestrator = Annotated[AIOrchestrator, Depends(get_orchestrator)]


@router.post(
    "/attempts",
    response_model=SpeakingResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_attempt(
    payload: SpeakingSubmitRequest,
    current: CurrentUser,
    session: DbSession,
    orchestrator: Orchestrator,
) -> SpeakingResultResponse:
    return await SpeakingController.submit(session, current, orchestrator, payload)


@router.get("/attempts/{attempt_id}", response_model=SpeakingResultResponse)
async def get_attempt(
    attempt_id: str, current: CurrentUser, session: DbSession
) -> SpeakingResultResponse:
    return await SpeakingController.get(session, current, attempt_id)
