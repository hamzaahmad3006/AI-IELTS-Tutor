"""Correlation-ID middleware: attaches a trace id to every request/response."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging import reset_correlation_id, set_correlation_id

CORRELATION_HEADER = "X-Correlation-Id"

logger = logging.getLogger("api.request")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # An inbound id is honoured so a trace can span the mobile client and
        # the API; otherwise one is minted here.
        correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        token = set_correlation_id(correlation_id)
        started = time.perf_counter()

        try:
            response = await call_next(request)
            response.headers[CORRELATION_HEADER] = correlation_id
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "durationMs": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            return response
        except Exception:
            # Logged here because by the time the exception surfaces outside
            # this middleware the timing and request context are gone.
            logger.exception(
                "request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "durationMs": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        finally:
            reset_correlation_id(token)
