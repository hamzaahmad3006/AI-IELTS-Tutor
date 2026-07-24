"""Writing routes: submit an essay for AI scoring and fetch the result."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from controllers.history_controller import HistoryController, WritingHistoryPage
from controllers.pagination import DEFAULT_LIMIT
from controllers.writing_controller import (
    WritingController,
    WritingResultResponse,
    WritingSubmitRequest,
)
from core.config import get_settings
from core.rate_limit import limit_by_user
from db.session import get_db
from dependencies import get_current_user, get_orchestrator
from models.user import User

router = APIRouter(prefix="/writing", tags=["writing"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Orchestrator = Annotated[AIOrchestrator, Depends(get_orchestrator)]
_ai_limit = get_settings().rate_limit_ai_per_min


@router.post(
    "/attempts",
    response_model=WritingResultResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user("ai_writing", _ai_limit))],
)
async def submit_attempt(
    payload: WritingSubmitRequest,
    current: CurrentUser,
    session: DbSession,
    orchestrator: Orchestrator,
) -> WritingResultResponse:
    return await WritingController.submit(session, current, orchestrator, payload)


@router.get("/history", response_model=WritingHistoryPage)
async def history(
    current: CurrentUser,
    session: DbSession,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_LIMIT,
) -> WritingHistoryPage:
    return await HistoryController.writing(session, current, cursor, limit)


@router.get("/attempts/{attempt_id}", response_model=WritingResultResponse)
async def get_attempt(
    attempt_id: str, current: CurrentUser, session: DbSession
) -> WritingResultResponse:
    return await WritingController.get(session, current, attempt_id)
