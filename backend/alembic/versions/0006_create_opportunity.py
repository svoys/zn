"""create opportunity table (versioned investment opportunity)

Версионируется: одна текущая версия на asset (partial UNIQUE WHERE is_current).
См. docs/digital-twin-design.md §5.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "opportunity",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("rating", sa.String(length=2), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("factors", postgresql.JSONB(), nullable=True),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("computed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["zn.asset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_opportunity_score"),
        schema="zn",
    )
    op.create_index("ix_opportunity_asset", "opportunity", ["asset_id"], schema="zn")
    op.create_index(
        "ix_opportunity_asset_current", "opportunity", ["asset_id", "is_current"], schema="zn"
    )
    # Одна текущая версия на asset — partial UNIQUE.
    op.execute(
        "CREATE UNIQUE INDEX uq_opportunity_current ON zn.opportunity (asset_id) "
        "WHERE is_current"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS zn.uq_opportunity_current")
    op.drop_index("ix_opportunity_asset_current", table_name="opportunity", schema="zn")
    op.drop_index("ix_opportunity_asset", table_name="opportunity", schema="zn")
    op.drop_table("opportunity", schema="zn")
