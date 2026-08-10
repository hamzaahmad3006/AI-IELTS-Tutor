"""Auth controller: request/response schemas + database-backed business logic.

Implements registration, login, refresh-token rotation and logout with
Argon2id password hashing and JWT access tokens (SRS sections 18 & 33)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pydantic import field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password_async,
    hash_refresh_token,
    verify_password_async,
)
from core.validation import validate_email, validate_password
from core.errors import AlreadyExistsError
from models.user import RefreshToken, User

from .base import CamelModel


# ---------- Schemas ----------
class LoginRequest(CamelModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)


class RegisterRequest(CamelModel):
    full_name: str
    email: str
    password: str

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        name = value.strip()
        if len(name) < 2:
            raise ValueError("Enter your full name")
        return name

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return validate_email(value)

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)


class RefreshRequest(CamelModel):
    refresh_token: str


class AuthenticatedUser(CamelModel):
    id: str
    email: str
    full_name: str
    role: str


class AuthTokens(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(CamelModel):
    user: AuthenticatedUser
    tokens: AuthTokens


# ---------- Controller ----------
class AuthController:
    @staticmethod
    async def _issue_tokens(session: AsyncSession, user: User) -> AuthTokens:
        settings = get_settings()
        access = create_access_token(subject=user.id, role=user.role)
        raw_refresh = generate_refresh_token()
        session.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.refresh_token_ttl_days),
            )
        )
        await session.flush()
        return AuthTokens(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_ttl_min * 60,
        )

    @staticmethod
    def _to_user_dto(user: User) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=user.id, email=user.email, full_name=user.full_name, role=user.role
        )

    @classmethod
    async def register(
        cls, session: AsyncSession, payload: RegisterRequest
    ) -> AuthResponse:
        existing = await session.scalar(
            select(User).where(User.email == payload.email.lower())
        )
        if existing is not None:
            raise AlreadyExistsError("An account with this email already exists")
        user = User(
            email=payload.email.lower(),
            password_hash=await hash_password_async(payload.password),
            full_name=payload.full_name,
            role="learner",
        )
        session.add(user)
        await session.flush()
        tokens = await cls._issue_tokens(session, user)
        return AuthResponse(user=cls._to_user_dto(user), tokens=tokens)

    @classmethod
    async def login(
        cls, session: AsyncSession, payload: LoginRequest
    ) -> AuthResponse:
        user = await session.scalar(
            select(User).where(User.email == payload.email.lower())
        )
        if user is None or not await verify_password_async(
            payload.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
            )
        tokens = await cls._issue_tokens(session, user)
        return AuthResponse(user=cls._to_user_dto(user), tokens=tokens)

    @classmethod
    async def refresh(
        cls, session: AsyncSession, payload: RefreshRequest
    ) -> AuthResponse:
        token_hash = hash_refresh_token(payload.refresh_token)
        record = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        now = datetime.now(timezone.utc)
        expires_at = record.expires_at if record is not None else None
        # SQLite returns naive datetimes; treat stored values as UTC.
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if (
            record is None
            or record.revoked_at is not None
            or expires_at is None
            or expires_at <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        # Rotate: revoke the presented token, issue a fresh pair.
        record.revoked_at = now
        user = await session.get(User, record.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )
        tokens = await cls._issue_tokens(session, user)
        return AuthResponse(user=cls._to_user_dto(user), tokens=tokens)

    @staticmethod
    async def logout(session: AsyncSession, payload: RefreshRequest) -> None:
        record = await session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_refresh_token(payload.refresh_token)
            )
        )
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
