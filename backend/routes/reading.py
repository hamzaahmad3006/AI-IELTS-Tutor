"""Reading routes: passage delivery, answer submission, result retrieval."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.history_controller import HistoryController, ReadingHistoryPage
from controllers.pagination import DEFAULT_LIMIT
from controllers.reading_controller import (
    PassageResponse,
    ReadingController,
    ReadingResultResponse,
    ReadingSubmitRequest,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/reading", tags=["reading"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/passages", response_model=PassageResponse)
async def get_passage(
    current: CurrentUser,
    session: DbSession,
    difficulty: Annotated[str | None, Query()] = None,
    exam_type: Annotated[str, Query(alias="examType")] = "academic",
) -> PassageResponse:
    return await ReadingController.get_passage(session, current.id, difficulty, exam_type)


@router.post(
    "/attempts",
    response_model=ReadingResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_attempt(
    payload: ReadingSubmitRequest, current: CurrentUser, session: DbSession
) -> ReadingResultResponse:
    return await ReadingController.submit(session, current, payload)


@router.get("/history", response_model=ReadingHistoryPage)
async def history(
    current: CurrentUser,
    session: DbSession,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_LIMIT,
) -> ReadingHistoryPage:
    return await HistoryController.reading(session, current, cursor, limit)


@router.get("/attempts/{attempt_id}", response_model=ReadingResultResponse)
async def get_attempt(
    attempt_id: str, current: CurrentUser, session: DbSession
) -> ReadingResultResponse:
    return await ReadingController.get_attempt(session, current, attempt_id)
