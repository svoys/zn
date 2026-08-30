"""create ai_insight table (versioned AI outputs: swot / risk / scenario / explanation)

Версионируется по (asset_id, kind): одна текущая версия на категорию
(partial UNIQUE WHERE is_current). См. docs/digital-twin-design.md §2.4.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_insight",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("trace", postgresql.JSONB(), nullable=True),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["zn.asset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "kind IN ('swot', 'risk', 'scenario', 'explanation')",
            name="ck_ai_insight_kind",
        ),
        schema="zn",
    )
    op.create_index("ix_ai_insight_asset", "ai_insight", ["asset_id"], schema="zn")
    op.create_index(
        "ix_ai_insight_asset_current",
        "ai_insight",
        ["asset_id", "kind", "is_current"],
        schema="zn",
    )
    # Одна текущая версия на (asset, kind) — partial UNIQUE.
    op.execute(
        "CREATE UNIQUE INDEX uq_ai_insight_current ON zn.ai_insight (asset_id, kind) "
        "WHERE is_current"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS zn.uq_ai_insight_current")
    op.drop_index("ix_ai_insight_asset_current", table_name="ai_insight", schema="zn")
    op.drop_index("ix_ai_insight_asset", table_name="ai_insight", schema="zn")
    op.drop_table("ai_insight", schema="zn")
