"""Placement diagnostic routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.diagnostic_controller import (
    DiagnosticController,
    DiagnosticResult,
    DiagnosticSet,
    DiagnosticSubmission,
)
from db.session import get_db
from ai.orchestrator import AIOrchestrator
from dependencies import get_current_user, get_orchestrator
from models.user import User

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Orchestrator = Annotated[AIOrchestrator, Depends(get_orchestrator)]


@router.get("", response_model=DiagnosticSet)
async def get_diagnostic(current: CurrentUser, session: DbSession) -> DiagnosticSet:
    return await DiagnosticController.get_set(session)


@router.post("", response_model=DiagnosticResult)
async def submit_diagnostic(
    current: CurrentUser,
    session: DbSession,
    payload: DiagnosticSubmission,
    orchestrator: Orchestrator,
) -> DiagnosticResult:
    return await DiagnosticController.submit(
        session, current, payload, orchestrator
    )
