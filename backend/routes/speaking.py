"""Speaking routes: submit a transcript for AI scoring and fetch the result."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from controllers.history_controller import HistoryController, SpeakingHistoryPage
from controllers.pagination import DEFAULT_LIMIT
from controllers.speaking_controller import (
    SpeakingController,
    SpeakingResultResponse,
    SpeakingSubmitRequest,
)
from core.config import get_settings
from core.rate_limit import limit_by_user
from db.session import get_db
from dependencies import get_current_user, get_orchestrator
from models.user import User

router = APIRouter(prefix="/speaking", tags=["speaking"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Orchestrator = Annotated[AIOrchestrator, Depends(get_orchestrator)]
_ai_limit = get_settings().rate_limit_ai_per_min


@router.post(
    "/attempts",
    response_model=SpeakingResultResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user("ai_speaking", _ai_limit))],
)
async def submit_attempt(
    payload: SpeakingSubmitRequest,
    current: CurrentUser,
    session: DbSession,
    orchestrator: Orchestrator,
) -> SpeakingResultResponse:
    return await SpeakingController.submit(session, current, orchestrator, payload)


@router.get("/history", response_model=SpeakingHistoryPage)
async def history(
    current: CurrentUser,
    session: DbSession,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_LIMIT,
) -> SpeakingHistoryPage:
    return await HistoryController.speaking(session, current, cursor, limit)


@router.get("/attempts/{attempt_id}", response_model=SpeakingResultResponse)
async def get_attempt(
    attempt_id: str, current: CurrentUser, session: DbSession
) -> SpeakingResultResponse:
    return await SpeakingController.get(session, current, attempt_id)
