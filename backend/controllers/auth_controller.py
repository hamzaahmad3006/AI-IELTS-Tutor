"""Auth controller: request/response schemas + business logic.

NOTE: this is a scaffold. Password hashing (Argon2id), JWT issuance, refresh-
token rotation and RBAC are stubbed and must be implemented before production
per the SRS (sections 18 & 33)."""

from __future__ import annotations

from .base import CamelModel


class LoginRequest(CamelModel):
    email: str
    password: str


class RegisterRequest(CamelModel):
    full_name: str
    email: str
    password: str


class AuthenticatedUser(CamelModel):
    id: str
    email: str
    full_name: str
    role: str


class AuthTokens(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class AuthResponse(CamelModel):
    user: AuthenticatedUser
    tokens: AuthTokens


class AuthController:
    """Handles authentication use-cases."""

    @staticmethod
    def login(payload: LoginRequest) -> AuthResponse:
        # TODO: verify Argon2id hash + issue signed JWT + persist refresh token.
        return AuthResponse(
            user=AuthenticatedUser(
                id="usr_1",
                email=payload.email,
                full_name="Sarah",
                role="learner",
            ),
            tokens=AuthTokens(
                access_token="stub.access.token",
                refresh_token="stub.refresh.token",
            ),
        )

    @staticmethod
    def register(payload: RegisterRequest) -> AuthResponse:
        # TODO: create user row, hash password, issue tokens.
        return AuthResponse(
            user=AuthenticatedUser(
                id="usr_new",
                email=payload.email,
                full_name=payload.full_name,
                role="learner",
            ),
            tokens=AuthTokens(
                access_token="stub.access.token",
                refresh_token="stub.refresh.token",
            ),
        )
