"""Vocabulary routes: spaced-repetition review queue, grading and stats."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.vocabulary_controller import (
    GradeRequest,
    GradeResponse,
    VocabQueue,
    VocabStats,
    VocabularyController,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/review", response_model=VocabQueue)
async def review_queue(
    current: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> VocabQueue:
    return await VocabularyController.get_queue(session, current, limit)


@router.post("/grade", response_model=GradeResponse)
async def grade(
    payload: GradeRequest, current: CurrentUser, session: DbSession
) -> GradeResponse:
    return await VocabularyController.grade(session, current, payload)


@router.get("/stats", response_model=VocabStats)
async def stats(current: CurrentUser, session: DbSession) -> VocabStats:
    return await VocabularyController.stats(session, current)
