"""Auth routes: thin HTTP layer delegating to AuthController."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from controllers.auth_controller import (
    AuthController,
    AuthResponse,
    AuthenticatedUser,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from core.config import get_settings
from core.rate_limit import limit_by_ip
from db.session import get_db
from dependencies import get_current_user
from models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
_settings = get_settings()


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_ip("register", _settings.rate_limit_register_per_min))],
)
async def register(payload: RegisterRequest, session: DbSession) -> AuthResponse:
    return await AuthController.register(session, payload)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(limit_by_ip("login", _settings.rate_limit_login_per_min))],
)
async def login(payload: LoginRequest, session: DbSession) -> AuthResponse:
    return await AuthController.login(session, payload)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(payload: RefreshRequest, session: DbSession) -> AuthResponse:
    return await AuthController.refresh(session, payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, session: DbSession) -> None:
    await AuthController.logout(session, payload)


@router.get("/me", response_model=AuthenticatedUser)
async def me(
    current: Annotated[User, Depends(get_current_user)],
) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=current.id,
        email=current.email,
        full_name=current.full_name,
        role=current.role,
    )
