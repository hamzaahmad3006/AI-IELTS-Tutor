"""cue_cards table (Speaking Part 2 bank)

Revision ID: 0010_cue_cards
Revises: 0009_writing_prompts
Create Date: 2026-07-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_cue_cards"
down_revision: Union[str, None] = "0009_writing_prompts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cue_cards",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("topic", sa.String(length=120), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("bullet_points", sa.JSON(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("prep_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("speak_seconds", sa.Integer(), server_default="120", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cue_cards")
