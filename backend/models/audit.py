"""Audit log ORM model: records privileged admin actions (SRS section 33)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin


def _uuid() -> str:
    return uuid.uuid4().hex


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    actor_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    audit_metadata: Mapped[Any | None] = mapped_column("metadata", JSON, nullable=True)
