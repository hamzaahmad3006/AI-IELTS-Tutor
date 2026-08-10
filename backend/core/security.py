"""Security primitives: Argon2id password hashing + JWT tokens."""

from __future__ import annotations

import asyncio

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a password. Blocking: prefer `hash_password_async` in a handler."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password. Blocking: prefer `verify_password_async`."""
    return _pwd_context.verify(plain, hashed)


async def hash_password_async(plain: str) -> str:
    """Hash off the event loop.

    Argon2 with these parameters is ~140ms of solid CPU. Called directly from
    an async handler it blocks the *entire* process for that long -- not just
    the one request -- so twenty people signing in at once queue behind each
    other and p95 goes to seconds. A load test measured exactly that: 7.5s at
    twenty users, against 140ms for a single hash.

    A thread genuinely helps here because Argon2 is C code that releases the
    GIL while it works, so the event loop keeps serving other requests.
    """
    return await asyncio.to_thread(_pwd_context.hash, plain)


async def verify_password_async(plain: str, hashed: str) -> bool:
    """Verify off the event loop, for the same reason."""
    return await asyncio.to_thread(_pwd_context.verify, plain, hashed)


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.access_token_ttl_min)).timestamp()
        ),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> dict[str, object]:
    """Decode + verify a JWT. Raises JWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])


def generate_refresh_token() -> str:
    """Opaque, high-entropy refresh token (the raw value is returned to the
    client; only its hash is persisted)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


__all__ = [
    "JWTError",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "generate_refresh_token",
    "hash_refresh_token",
]
