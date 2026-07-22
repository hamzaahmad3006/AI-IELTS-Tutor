"""Security primitives: Argon2id password hashing + JWT tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


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
