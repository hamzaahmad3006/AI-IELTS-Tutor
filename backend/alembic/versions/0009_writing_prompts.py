"""writing_prompts table (Task 1/2 prompt bank)

Revision ID: 0009_writing_prompts
Revises: 0008_weaknesses
Create Date: 2026-07-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_writing_prompts"
down_revision: Union[str, None] = "0008_weaknesses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "writing_prompts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("exam_type", sa.String(length=20), server_default="academic", nullable=False),
        sa.Column("task_number", sa.Integer(), server_default="2", nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=120), nullable=True),
        sa.Column("asset_ref", sa.String(length=300), nullable=True),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("min_words", sa.Integer(), server_default="250", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("writing_prompts")
