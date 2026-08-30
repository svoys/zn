"""create restriction table (ЗОУИТ / обременения, 1:* to asset)

severity (0..100) — вклад ограничения в риск и Opportunity Score.
См. docs/digital-twin-design.md.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "restriction",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.SmallInteger(), nullable=True),
        sa.Column("geometry", Geometry(geometry_type="GEOMETRY", srid=4326), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["zn.asset.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "kind IN ('zouit', 'easement', 'protective_zone', 'flood', 'encumbrance', 'other')",
            name="ck_restriction_kind",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR (severity >= 0 AND severity <= 100)",
            name="ck_restriction_severity",
        ),
        schema="zn",
    )
    op.create_index("ix_restriction_asset", "restriction", ["asset_id"], schema="zn")
    op.create_index(
        "ix_restriction_geometry", "restriction", ["geometry"],
        postgresql_using="gist", schema="zn",
    )


def downgrade() -> None:
    op.drop_index("ix_restriction_geometry", table_name="restriction", schema="zn")
    op.drop_index("ix_restriction_asset", table_name="restriction", schema="zn")
    op.drop_table("restriction", schema="zn")
