"""Grammar routes: lesson library and lesson detail."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.grammar_controller import (
    GrammarController,
    GrammarLessonDetail,
    GrammarLessonList,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/grammar", tags=["grammar"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/lessons", response_model=GrammarLessonList)
async def list_lessons(
    current: CurrentUser,
    session: DbSession,
    tag: Annotated[str | None, Query()] = None,
) -> GrammarLessonList:
    return await GrammarController.list_lessons(session, current, tag)


@router.get("/lessons/{lesson_id}", response_model=GrammarLessonDetail)
async def get_lesson(
    lesson_id: str, current: CurrentUser, session: DbSession
) -> GrammarLessonDetail:
    return await GrammarController.get_lesson(session, lesson_id)
