"""create event table (append-only change log / monitoring)

`asset_id` nullable (событие территории без конкретного участка). Индекс
(asset_id, occurred_at) — лента «свежие сверху». Тип события НЕ ограничен CHECK'ом
(список растёт с источниками), валидация — в коде. См. docs/digital-twin-design.md §2.5.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=True),
        sa.Column("type", sa.String(length=60), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["zn.asset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="zn",
    )
    op.create_index("ix_event_asset_occurred", "event", ["asset_id", "occurred_at"], schema="zn")
    op.create_index("ix_event_type", "event", ["type"], schema="zn")


def downgrade() -> None:
    op.drop_index("ix_event_type", table_name="event", schema="zn")
    op.drop_index("ix_event_asset_occurred", table_name="event", schema="zn")
    op.drop_table("event", schema="zn")
