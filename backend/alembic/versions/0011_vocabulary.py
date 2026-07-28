"""vocabulary bank + per-learner SRS review state

Revision ID: 0011_vocabulary
Revises: 0010_cue_cards
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_vocabulary"
down_revision: Union[str, None] = "0010_cue_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vocab_items",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("word", sa.String(length=80), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("lexical_field", sa.String(length=60), nullable=True),
        sa.Column("cefr_level", sa.String(length=10), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="seed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vocab_items_lexical_field", "vocab_items", ["lexical_field"])

    op.create_table(
        "vocab_reviews",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.String(length=32), nullable=False),
        sa.Column("repetitions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ease_factor", sa.Float(), server_default="2.5", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_grade", sa.Integer(), nullable=True),
        sa.Column("total_reviews", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["vocab_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "item_id", name="uq_vocab_review_user_item"),
    )
    op.create_index("ix_vocab_reviews_user_id", "vocab_reviews", ["user_id"])
    op.create_index("ix_vocab_reviews_item_id", "vocab_reviews", ["item_id"])
    op.create_index("ix_vocab_reviews_due_at", "vocab_reviews", ["due_at"])


def downgrade() -> None:
    op.drop_table("vocab_reviews")
    op.drop_index("ix_vocab_items_lexical_field", table_name="vocab_items")
    op.drop_table("vocab_items")
