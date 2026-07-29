"""grammar_lessons table

Revision ID: 0012_grammar_lessons
Revises: 0011_vocabulary
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_grammar_lessons"
down_revision: Union[str, None] = "0011_vocabulary"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "grammar_lessons",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("concept_tag", sa.String(length=60), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("examples", sa.JSON(), nullable=False),
        sa.Column("level", sa.String(length=20), server_default="intermediate", nullable=False),
        sa.Column("minutes", sa.Integer(), server_default="5", nullable=False),
        sa.Column("weakness_tags", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_grammar_lessons_concept_tag", "grammar_lessons", ["concept_tag"])


def downgrade() -> None:
    op.drop_index("ix_grammar_lessons_concept_tag", table_name="grammar_lessons")
    op.drop_table("grammar_lessons")
