"""Generic repository helpers for user-owned rows.

The "fetch by id, then check it belongs to the caller" dance was written out
six times across the controllers, and each copy had to remember to return 404
rather than 403 — because 403 confirms the row exists to someone who should not
know that. One implementation, one place to get that right.

This is deliberately thin. It is not an abstraction layer over SQLAlchemy:
controllers still build their own queries where the query is the interesting
part. It only removes the duplication that was actually there.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.errors import NotFoundError

ModelT = TypeVar("ModelT")


class OwnedRepository(Generic[ModelT]):
    """Reads rows that belong to a single user.

    `owner_field` is the attribute holding the user id, since not every model
    calls it `user_id`.
    """

    def __init__(
        self,
        model: type[ModelT],
        *,
        label: str,
        owner_field: str = "user_id",
    ) -> None:
        self.model = model
        self.label = label
        self.owner_field = owner_field

    async def get(self, session: AsyncSession, row_id: str) -> ModelT | None:
        return await session.scalar(
            select(self.model).where(getattr(self.model, "id") == row_id)
        )

    async def get_owned(
        self, session: AsyncSession, row_id: str, user_id: str
    ) -> ModelT:
        """Fetch a row the caller owns, or raise NotFound.

        A row owned by someone else raises NotFound, never Forbidden: telling a
        stranger "this exists but is not yours" leaks that the id is real, which
        is enough to enumerate other people's data.
        """
        row = await self.get(session, row_id)
        if row is None or getattr(row, self.owner_field, None) != user_id:
            raise NotFoundError(f"{self.label} not found")
        return row

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        limit: int | None = None,
    ) -> list[ModelT]:
        query = select(self.model).where(
            getattr(self.model, self.owner_field) == user_id
        )
        if limit is not None:
            query = query.limit(limit)
        return list((await session.execute(query)).scalars().all())
