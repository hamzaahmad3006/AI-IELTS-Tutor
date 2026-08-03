"""Study planner routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.base import CamelModel
from controllers.planner_controller import (
    PlannerController,
    PlanTaskOut,
    StudyPlanOut,
)
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/planner", tags=["planner"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


class TaskUpdate(CamelModel):
    is_done: bool


@router.get("/plan", response_model=StudyPlanOut)
async def get_plan(current: CurrentUser, session: DbSession) -> StudyPlanOut:
    plan = await PlannerController.get_active(session, current)
    if plan is None:
        # 404 rather than an empty plan: "you have no plan" and "your plan has
        # no tasks" are different states and the client must tell them apart.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No study plan yet"
        )
    return plan


@router.post("/plan", response_model=StudyPlanOut, status_code=status.HTTP_201_CREATED)
async def generate_plan(current: CurrentUser, session: DbSession) -> StudyPlanOut:
    return await PlannerController.generate(session, current)


@router.patch("/tasks/{task_id}", response_model=PlanTaskOut)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    current: CurrentUser,
    session: DbSession,
) -> PlanTaskOut:
    return await PlannerController.complete_task(
        session, current, task_id, payload.is_done
    )
