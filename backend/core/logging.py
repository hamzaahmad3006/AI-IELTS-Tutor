"""Structured JSON logging with correlation-id propagation.

Every line is one JSON object, so logs stay greppable and machine-parseable once
they reach a log aggregator. The correlation id lives in a ContextVar rather
than being threaded through call signatures: any code reached during a request —
a controller, a provider adapter, an exception handler — gets it for free, and
it is the value the client already saw in the `X-Correlation-Id` response
header, so a user-reported error can be traced to exact log lines.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

#: LogRecord attributes that are not caller-supplied extras.
_RESERVED = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
) | {"message", "asctime", "taskName"}


def set_correlation_id(value: str | None) -> object:
    """Bind the id for the current context. Returns a token for `reset`."""
    return _correlation_id.set(value)


def reset_correlation_id(token: object) -> None:
    """Restore the previous value. Prevents leaking across reused workers."""
    _correlation_id.reset(token)  # type: ignore[arg-type]


def get_correlation_id() -> str | None:
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    """Renders a LogRecord as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = get_correlation_id()
        if correlation_id:
            payload["correlationId"] = correlation_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Anything passed as logger.info(..., extra={...}) rides along, so
        # call sites can attach structured fields instead of formatting them
        # into the message string.
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root and uvicorn loggers."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # uvicorn installs its own handlers; clear them so access and error lines
    # are not emitted twice, once plain and once as JSON.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
