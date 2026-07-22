"""Auth routes: thin HTTP layer delegating to AuthController."""

from __future__ import annotations

from fastapi import APIRouter, status

from controllers.auth_controller import (
    AuthController,
    AuthResponse,
    LoginRequest,
    RegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    return AuthController.login(payload)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: RegisterRequest) -> AuthResponse:
    return AuthController.register(payload)
