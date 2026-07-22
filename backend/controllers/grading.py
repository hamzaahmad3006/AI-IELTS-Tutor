"""Shared objective-answer grading helpers (Reading + Listening)."""

from __future__ import annotations

from typing import Any


def normalize(value: Any) -> Any:
    """Normalize an answer for comparison: lowercase/trim scalars, sort lists."""
    if isinstance(value, list):
        return sorted(str(v).strip().lower() for v in value)
    if value is None:
        return ""
    return str(value).strip().lower()


def is_correct(submitted: Any, correct: Any) -> bool:
    return normalize(submitted) == normalize(correct)
