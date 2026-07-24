"""Listening routes: clip delivery, answer submission, result retrieval."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.history_controller import HistoryController, ListeningHistoryPage
from controllers.listening_controller import (
    ClipResponse,
    ListeningController,
    ListeningResultResponse,
    ListeningSubmitRequest,
)
from controllers.pagination import DEFAULT_LIMIT
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/listening", tags=["listening"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/clips", response_model=ClipResponse)
async def get_clip(
    current: CurrentUser,
    session: DbSession,
    difficulty: Annotated[str | None, Query()] = None,
    exam_type: Annotated[str, Query(alias="examType")] = "academic",
) -> ClipResponse:
    return await ListeningController.get_clip(session, current.id, difficulty, exam_type)


@router.post(
    "/attempts",
    response_model=ListeningResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_attempt(
    payload: ListeningSubmitRequest, current: CurrentUser, session: DbSession
) -> ListeningResultResponse:
    return await ListeningController.submit(session, current, payload)


@router.get("/history", response_model=ListeningHistoryPage)
async def history(
    current: CurrentUser,
    session: DbSession,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_LIMIT,
) -> ListeningHistoryPage:
    return await HistoryController.listening(session, current, cursor, limit)


@router.get("/attempts/{attempt_id}", response_model=ListeningResultResponse)
async def get_attempt(
    attempt_id: str, current: CurrentUser, session: DbSession
) -> ListeningResultResponse:
    return await ListeningController.get_attempt(session, current, attempt_id)
