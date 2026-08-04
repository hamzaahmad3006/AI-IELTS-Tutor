"""composite indexes for the hot query shapes

Revision ID: 0018_indexes_retention
Revises: 0017_prompt_version
Create Date: 2026-08-04

Every attempt table already indexes user_id, but no query ever asks only for
that. They all ask for one learner's rows in time order -- progress charts,
history lists, the EMA that drives adaptive difficulty -- which means the
existing index finds the rows and the database then sorts them. A composite
(user_id, created_at) returns them already ordered.

The same shape covers ai_interactions, and a created_at index is added there
separately because the retention sweep scans by age across all users, which the
composite cannot serve.

No partitioning. It was on the backlog, but these tables hold thousands of rows,
not millions, and partitioning an existing table means rewriting it -- real
downtime and a migration that cannot be safely reversed, bought in exchange for
nothing measurable. It stays open, with the reason recorded, rather than being
marked done by doing it prematurely.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0018_indexes_retention"
down_revision: Union[str, None] = "0017_prompt_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: (index name, table, columns)
_INDEXES: list[tuple[str, str, list[str]]] = [
    # "this learner's attempts, newest first" -- every history and chart query.
    ("ix_writing_attempts_user_created", "writing_attempts", ["user_id", "created_at"]),
    ("ix_speaking_attempts_user_created", "speaking_attempts", ["user_id", "created_at"]),
    ("ix_reading_attempts_user_created", "reading_attempts", ["user_id", "created_at"]),
    ("ix_listening_attempts_user_created", "listening_attempts", ["user_id", "created_at"]),
    # Admin usage reporting, per learner and in time order.
    ("ix_ai_interactions_user_created", "ai_interactions", ["user_id", "created_at"]),
    # Retention sweeps scan by age across all users; the composite above starts
    # with user_id and so cannot help them.
    ("ix_ai_interactions_created", "ai_interactions", ["created_at"]),
    # Expired-token cleanup, same reason.
    ("ix_refresh_tokens_expires", "refresh_tokens", ["expires_at"]),
    # The weakness list filters out resolved rows before ordering by priority.
    ("ix_weaknesses_user_resolved", "weaknesses", ["user_id", "resolved"]),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _ in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
