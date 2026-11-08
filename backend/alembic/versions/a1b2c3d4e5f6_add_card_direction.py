"""add direction and enabled to memory cards

Revision ID: a1b2c3d4e5f6
Revises: 0f6fb4477299
Create Date: 2026-11-06

The learning system is English-to-Chinese only. Existing non-recognition
cards are kept for history but disabled. SQLite triggers enforce the direction
at the database layer for future inserts/updates.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "0f6fb4477299"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "memory_cards",
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="EN_TO_ZH"),
    )
    op.add_column(
        "memory_cards",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.execute("UPDATE memory_cards SET direction = 'EN_TO_ZH'")
    op.execute("UPDATE memory_cards SET enabled = 0 WHERE card_type != 'en_to_zh'")
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_memory_cards_direction_insert
        BEFORE INSERT ON memory_cards
        FOR EACH ROW WHEN NEW.direction != 'EN_TO_ZH'
        BEGIN
            SELECT RAISE(ABORT, 'memory_cards.direction must be EN_TO_ZH');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_memory_cards_direction_update
        BEFORE UPDATE OF direction ON memory_cards
        FOR EACH ROW WHEN NEW.direction != 'EN_TO_ZH'
        BEGIN
            SELECT RAISE(ABORT, 'memory_cards.direction must be EN_TO_ZH');
        END;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_memory_cards_direction_insert")
    op.execute("DROP TRIGGER IF EXISTS trg_memory_cards_direction_update")
    with op.batch_alter_table("memory_cards") as batch:
        batch.drop_column("enabled")
        batch.drop_column("direction")
