"""Admin content routes: reading passages + questions CRUD (RBAC-guarded)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.admin_content_controller import (
    AdminContentController,
    PassageAdmin,
    PassageAdminPage,
    PassageCreate,
    PassageUpdate,
    QuestionAdmin,
    QuestionCreate,
    QuestionUpdate,
)
from controllers.pagination import DEFAULT_LIMIT
from db.session import get_db
from dependencies import require_roles
from models.user import User

router = APIRouter(prefix="/admin", tags=["admin-content"])

ContentAdmin = Annotated[
    User, Depends(require_roles("content_editor", "admin", "super_admin"))
]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/passages", response_model=PassageAdmin, status_code=status.HTTP_201_CREATED)
async def create_passage(
    payload: PassageCreate, admin: ContentAdmin, session: DbSession
) -> PassageAdmin:
    return await AdminContentController.create_passage(session, admin, payload)


@router.get("/passages", response_model=PassageAdminPage)
async def list_passages(
    admin: ContentAdmin,
    session: DbSession,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_LIMIT,
) -> PassageAdminPage:
    return await AdminContentController.list_passages(session, cursor, limit)


@router.get("/passages/{passage_id}", response_model=PassageAdmin)
async def get_passage(
    passage_id: str, admin: ContentAdmin, session: DbSession
) -> PassageAdmin:
    return await AdminContentController.get_passage(session, passage_id)


@router.patch("/passages/{passage_id}", response_model=PassageAdmin)
async def update_passage(
    passage_id: str, payload: PassageUpdate, admin: ContentAdmin, session: DbSession
) -> PassageAdmin:
    return await AdminContentController.update_passage(session, admin, passage_id, payload)


@router.delete("/passages/{passage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_passage(
    passage_id: str, admin: ContentAdmin, session: DbSession
) -> None:
    await AdminContentController.delete_passage(session, admin, passage_id)


@router.post(
    "/passages/{passage_id}/questions",
    response_model=QuestionAdmin,
    status_code=status.HTTP_201_CREATED,
)
async def add_question(
    passage_id: str, payload: QuestionCreate, admin: ContentAdmin, session: DbSession
) -> QuestionAdmin:
    return await AdminContentController.add_question(session, admin, passage_id, payload)


@router.patch("/questions/{question_id}", response_model=QuestionAdmin)
async def update_question(
    question_id: str, payload: QuestionUpdate, admin: ContentAdmin, session: DbSession
) -> QuestionAdmin:
    return await AdminContentController.update_question(session, admin, question_id, payload)


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str, admin: ContentAdmin, session: DbSession
) -> None:
    await AdminContentController.delete_question(session, admin, question_id)
