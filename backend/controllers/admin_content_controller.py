"""Admin content management: reading passages + questions CRUD (FR-ADM-2).

RBAC-guarded at the route (content_editor/admin/super_admin). Mutations are
written to the audit log. Admin views include the correct answers (unlike the
learner-facing reading endpoints)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from models.content import Passage, Question
from models.user import User

from .base import CamelModel
from .pagination import paginate

_QUESTION_TYPES = {
    "mcq",
    "true_false_notgiven",
    "matching_headings",
    "short_answer",
    "sentence_completion",
    "form_completion",
}


# ---------- Schemas ----------
class QuestionCreate(CamelModel):
    type: str
    prompt: str
    options: list[str] | None = None
    correct_answer: Any
    explanation: str | None = None
    difficulty: str = "medium"
    order_index: int = 0


class QuestionUpdate(CamelModel):
    type: str | None = None
    prompt: str | None = None
    options: list[str] | None = None
    correct_answer: Any | None = None
    explanation: str | None = None
    difficulty: str | None = None
    order_index: int | None = None


class PassageCreate(CamelModel):
    title: str
    body: str
    exam_type: str = "academic"
    difficulty: str = "medium"
    topic: str | None = None
    questions: list[QuestionCreate] = []


class PassageUpdate(CamelModel):
    title: str | None = None
    body: str | None = None
    exam_type: str | None = None
    difficulty: str | None = None
    topic: str | None = None


class QuestionAdmin(CamelModel):
    id: str
    type: str
    prompt: str
    options: list[str] | None
    correct_answer: Any
    explanation: str | None
    difficulty: str
    order_index: int


class PassageAdminItem(CamelModel):
    id: str
    title: str
    exam_type: str
    difficulty: str
    topic: str | None
    word_count: int
    created_at: datetime


class PassageAdmin(CamelModel):
    id: str
    title: str
    body: str
    exam_type: str
    difficulty: str
    topic: str | None
    word_count: int
    questions: list[QuestionAdmin]


class PassageAdminPage(CamelModel):
    items: list[PassageAdminItem]
    next_cursor: str | None


def _validate_type(qtype: str) -> None:
    if qtype not in _QUESTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid question type: {qtype}",
        )


def _q_admin(q: Question) -> QuestionAdmin:
    return QuestionAdmin(
        id=q.id,
        type=q.type,
        prompt=q.prompt,
        options=q.options,
        correct_answer=q.correct_answer,
        explanation=q.explanation,
        difficulty=q.difficulty,
        order_index=q.order_index,
    )


def _audit(session: AsyncSession, actor: User, action: str, entity_id: str, meta: dict[str, Any]) -> None:
    session.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            entity_type="content",
            entity_id=entity_id,
            audit_metadata=meta,
        )
    )


class AdminContentController:
    @staticmethod
    async def _questions(session: AsyncSession, passage_id: str) -> list[Question]:
        rows = await session.scalars(
            select(Question)
            .where(Question.passage_id == passage_id)
            .order_by(Question.order_index)
        )
        return list(rows)

    @classmethod
    async def create_passage(
        cls, session: AsyncSession, actor: User, payload: PassageCreate
    ) -> PassageAdmin:
        passage = Passage(
            title=payload.title,
            body=payload.body,
            exam_type=payload.exam_type,
            difficulty=payload.difficulty,
            topic=payload.topic,
            word_count=len(payload.body.split()),
            source="admin",
        )
        session.add(passage)
        await session.flush()
        for index, q in enumerate(payload.questions):
            _validate_type(q.type)
            session.add(
                Question(
                    passage_id=passage.id,
                    order_index=q.order_index or index + 1,
                    type=q.type,
                    prompt=q.prompt,
                    options=q.options,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                    difficulty=q.difficulty,
                )
            )
        _audit(session, actor, "create_passage", passage.id, {"title": passage.title})
        await session.flush()
        return await cls.get_passage(session, passage.id)

    @classmethod
    async def list_passages(
        cls, session: AsyncSession, cursor: str | None, limit: int
    ) -> PassageAdminPage:
        rows, next_cursor = await paginate(session, Passage, [], cursor, limit)
        return PassageAdminPage(
            items=[
                PassageAdminItem(
                    id=p.id,
                    title=p.title,
                    exam_type=p.exam_type,
                    difficulty=p.difficulty,
                    topic=p.topic,
                    word_count=p.word_count,
                    created_at=p.created_at,
                )
                for p in rows
            ],
            next_cursor=next_cursor,
        )

    @classmethod
    async def get_passage(cls, session: AsyncSession, passage_id: str) -> PassageAdmin:
        passage = await session.get(Passage, passage_id)
        if passage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found"
            )
        questions = await cls._questions(session, passage_id)
        return PassageAdmin(
            id=passage.id,
            title=passage.title,
            body=passage.body,
            exam_type=passage.exam_type,
            difficulty=passage.difficulty,
            topic=passage.topic,
            word_count=passage.word_count,
            questions=[_q_admin(q) for q in questions],
        )

    @classmethod
    async def update_passage(
        cls, session: AsyncSession, actor: User, passage_id: str, patch: PassageUpdate
    ) -> PassageAdmin:
        passage = await session.get(Passage, passage_id)
        if passage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found"
            )
        data = patch.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(passage, field, value)
        if "body" in data:
            passage.word_count = len(passage.body.split())
        _audit(session, actor, "update_passage", passage.id, {"fields": list(data.keys())})
        await session.flush()
        return await cls.get_passage(session, passage_id)

    @classmethod
    async def delete_passage(
        cls, session: AsyncSession, actor: User, passage_id: str
    ) -> None:
        passage = await session.get(Passage, passage_id)
        if passage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found"
            )
        # Explicit child delete (SQLite does not enforce FK cascade by default).
        await session.execute(delete(Question).where(Question.passage_id == passage_id))
        await session.delete(passage)
        _audit(session, actor, "delete_passage", passage_id, {})
        await session.flush()

    @classmethod
    async def add_question(
        cls, session: AsyncSession, actor: User, passage_id: str, payload: QuestionCreate
    ) -> QuestionAdmin:
        passage = await session.get(Passage, passage_id)
        if passage is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Passage not found"
            )
        _validate_type(payload.type)
        if not payload.order_index:
            count = await session.scalar(
                select(func.count())
                .select_from(Question)
                .where(Question.passage_id == passage_id)
            )
            order_index = int(count or 0) + 1
        else:
            order_index = payload.order_index
        question = Question(
            passage_id=passage_id,
            order_index=order_index,
            type=payload.type,
            prompt=payload.prompt,
            options=payload.options,
            correct_answer=payload.correct_answer,
            explanation=payload.explanation,
            difficulty=payload.difficulty,
        )
        session.add(question)
        _audit(session, actor, "add_question", question.id, {"passage_id": passage_id})
        await session.flush()
        return _q_admin(question)

    @classmethod
    async def update_question(
        cls, session: AsyncSession, actor: User, question_id: str, patch: QuestionUpdate
    ) -> QuestionAdmin:
        question = await session.get(Question, question_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
            )
        data = patch.model_dump(exclude_unset=True)
        if "type" in data and data["type"] is not None:
            _validate_type(data["type"])
        for field, value in data.items():
            setattr(question, field, value)
        _audit(session, actor, "update_question", question.id, {"fields": list(data.keys())})
        await session.flush()
        return _q_admin(question)

    @classmethod
    async def delete_question(
        cls, session: AsyncSession, actor: User, question_id: str
    ) -> None:
        question = await session.get(Question, question_id)
        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Question not found"
            )
        await session.delete(question)
        _audit(session, actor, "delete_question", question_id, {})
        await session.flush()
