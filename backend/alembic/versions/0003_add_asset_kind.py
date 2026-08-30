"""add asset.kind discriminator

Дискриминатор типа объекта. MVP: только 'parcel'. Готовит asset к 1:1-расширению
через zn.parcel (см. миграцию 0004).

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "asset",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="parcel"),
        schema="zn",
    )
    op.create_check_constraint(
        "ck_asset_kind",
        "asset",
        "kind IN ('parcel', 'building', 'complex', 'unknown')",
        schema="zn",
    )


def downgrade() -> None:
    op.drop_constraint("ck_asset_kind", "asset", schema="zn", type_="check")
    op.drop_column("asset", "kind", schema="zn")
