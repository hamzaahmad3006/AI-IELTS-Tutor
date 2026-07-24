"""In-memory fixed-window rate limiter + FastAPI dependencies (SRS section 34).

Per-process and dependency-free so it runs in dev/CI without Redis. The
`Limiter.hit` seam can be reimplemented against Redis for multi-instance
deployments without changing the dependencies or routes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated, Awaitable, Callable

from fastapi import Depends, Request

from core.config import get_settings
from dependencies import get_current_user
from models.user import User


class RateLimitExceeded(Exception):
    """Raised when a caller exceeds a rate-limit window."""

    def __init__(self, retry_after: int, limit: int) -> None:
        self.retry_after = retry_after
        self.limit = limit
        super().__init__("Rate limit exceeded")


@dataclass
class _Window:
    start: float
    count: int


class Limiter:
    """Fixed-window counter. hit() is fully synchronous (atomic on the event
    loop), so no lock is needed for a single-process deployment."""

    def __init__(self) -> None:
        self._windows: dict[str, _Window] = {}

    def hit(self, key: str, limit: int, window_s: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        window = self._windows.get(key)
        if window is None or (now - window.start) >= window_s:
            self._windows[key] = _Window(start=now, count=1)
            return True, 0
        window.count += 1
        if window.count > limit:
            retry_after = max(1, int(window_s - (now - window.start)) + 1)
            return False, retry_after
        return True, 0

    def reset(self) -> None:
        self._windows.clear()


limiter = Limiter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


IpDep = Callable[[Request], Awaitable[None]]


def limit_by_ip(scope: str, per_min: int) -> IpDep:
    """Dependency: limit `per_min` requests per client IP for `scope`."""

    async def _dep(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        key = f"{scope}:ip:{_client_ip(request)}"
        allowed, retry_after = limiter.hit(key, per_min, 60)
        if not allowed:
            raise RateLimitExceeded(retry_after=retry_after, limit=per_min)

    return _dep


def limit_by_user(scope: str, per_min: int) -> Callable[..., Awaitable[None]]:
    """Dependency: limit `per_min` requests per authenticated user for `scope`."""

    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> None:
        if not get_settings().rate_limit_enabled:
            return
        key = f"{scope}:user:{user.id}"
        allowed, retry_after = limiter.hit(key, per_min, 60)
        if not allowed:
            raise RateLimitExceeded(retry_after=retry_after, limit=per_min)

    return _dep
