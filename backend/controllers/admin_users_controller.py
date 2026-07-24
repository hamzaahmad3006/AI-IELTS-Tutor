"""Admin user management: list, suspend/reactivate, role assignment.

RBAC-guarded at the route; privileged actions are written to the audit log."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from models.user import User

from .base import CamelModel
from .pagination import paginate

VALID_ROLES = {"learner", "content_editor", "admin", "super_admin"}
PRIVILEGED_ROLES = {"admin", "super_admin"}


# ---------- Schemas ----------
class AdminUserItem(CamelModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime


class AdminUserPage(CamelModel):
    items: list[AdminUserItem]
    next_cursor: str | None


class UserUpdateRequest(CamelModel):
    is_active: bool | None = None
    role: str | None = None


def _to_item(user: User) -> AdminUserItem:
    return AdminUserItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
    )


class AdminUsersController:
    @staticmethod
    async def list_users(
        session: AsyncSession, cursor: str | None, limit: int, search: str | None
    ) -> AdminUserPage:
        conditions = []
        if search:
            like = f"%{search.lower()}%"
            conditions.append(
                or_(User.email.ilike(like), User.full_name.ilike(like))
            )
        rows, next_cursor = await paginate(session, User, conditions, cursor, limit)
        return AdminUserPage(
            items=[_to_item(u) for u in rows], next_cursor=next_cursor
        )

    @staticmethod
    async def update_user(
        session: AsyncSession, actor: User, user_id: str, patch: UserUpdateRequest
    ) -> AdminUserItem:
        target = await session.get(User, user_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        changes: dict[str, object] = {}

        if patch.role is not None and patch.role != target.role:
            if patch.role not in VALID_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid role: {patch.role}",
                )
            # Only a super_admin may grant or revoke privileged roles.
            grants_privilege = patch.role in PRIVILEGED_ROLES
            revokes_privilege = target.role in PRIVILEGED_ROLES
            if (grants_privilege or revokes_privilege) and actor.role != "super_admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a super admin can assign or revoke privileged roles",
                )
            if target.id == actor.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot change your own role",
                )
            changes["role"] = {"from": target.role, "to": patch.role}
            target.role = patch.role

        if patch.is_active is not None and patch.is_active != target.is_active:
            if target.id == actor.id and patch.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You cannot suspend your own account",
                )
            changes["is_active"] = {"from": target.is_active, "to": patch.is_active}
            target.is_active = patch.is_active

        if changes:
            session.add(
                AuditLog(
                    actor_id=actor.id,
                    action="update_user",
                    entity_type="user",
                    entity_id=target.id,
                    audit_metadata=changes,
                )
            )
        await session.flush()
        return _to_item(target)
