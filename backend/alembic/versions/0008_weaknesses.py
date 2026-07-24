"""weaknesses table (learner weakness memory)

Revision ID: 0008_weaknesses
Revises: 0007_audit_logs
Create Date: 2026-07-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_weaknesses"
down_revision: Union[str, None] = "0007_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "weaknesses",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("module", sa.String(length=20), nullable=False),
        sa.Column("tag", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.Float(), server_default="0", nullable=False),
        sa.Column("occurrences", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "module", "tag", name="uq_weakness_user_module_tag"),
    )
    op.create_index("ix_weaknesses_user_id", "weaknesses", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_weaknesses_user_id", table_name="weaknesses")
    op.drop_table("weaknesses")
