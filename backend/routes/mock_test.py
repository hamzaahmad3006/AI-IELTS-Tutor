"""Full mock test routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai.orchestrator import AIOrchestrator
from controllers.mock_test_controller import (
    MockResultOut,
    MockSubmission,
    MockTestController,
    MockTestOut,
)
from db.session import get_db
from dependencies import get_current_user, get_orchestrator
from models.user import User

router = APIRouter(prefix="/mock-tests", tags=["mock-tests"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Orchestrator = Annotated[AIOrchestrator, Depends(get_orchestrator)]


@router.post("", response_model=MockTestOut, status_code=status.HTTP_201_CREATED)
async def start_mock_test(current: CurrentUser, session: DbSession) -> MockTestOut:
    return await MockTestController.start(session, current)


@router.post("/{test_id}/submit", response_model=MockResultOut)
async def submit_mock_test(
    test_id: str,
    payload: MockSubmission,
    current: CurrentUser,
    session: DbSession,
    orchestrator: Orchestrator,
) -> MockResultOut:
    return await MockTestController.submit(
        session, current, test_id, payload, orchestrator
    )


@router.get("", response_model=list[MockResultOut])
async def mock_test_history(
    current: CurrentUser, session: DbSession
) -> list[MockResultOut]:
    return await MockTestController.history(session, current)
