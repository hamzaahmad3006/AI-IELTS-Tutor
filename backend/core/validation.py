"""Reusable field validators (email format, password strength).

Kept dependency-free (regex) so no extra package is required."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128


def validate_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address")
    if len(email) > 320:
        raise ValueError("Email is too long")
    return email


def validate_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LEN:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LEN} characters"
        )
    if len(value) > MAX_PASSWORD_LEN:
        raise ValueError("Password is too long")
    if not any(c.isalpha() for c in value):
        raise ValueError("Password must contain a letter")
    if not any(c.isdigit() for c in value):
        raise ValueError("Password must contain a number")
    return value
