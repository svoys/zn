"""create parcel table (1:1 extension of asset)

Правовой/градостроительный слой участка. asset_id — shared PK и FK на zn.asset
с каскадным удалением. См. docs/digital-twin-design.md.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parcel",
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("land_category", sa.String(length=120), nullable=True),
        sa.Column("permitted_use", sa.Text(), nullable=True),
        sa.Column("permitted_use_aux", postgresql.JSONB(), nullable=True),
        sa.Column("zone_code", sa.String(length=60), nullable=True),
        sa.Column("cadastral_quarter", sa.String(length=20), nullable=True),
        sa.Column("cadastral_value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["zn.asset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id"),
        schema="zn",
    )

    # updated_at через тот же триггер, что и у asset.
    op.execute(
        """
        CREATE TRIGGER parcel_set_updated_at
        BEFORE UPDATE ON zn.parcel
        FOR EACH ROW
        EXECUTE FUNCTION zn.tg_set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS parcel_set_updated_at ON zn.parcel")
    op.drop_table("parcel", schema="zn")
