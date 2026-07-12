"""create asset table with postgis

Revision ID: 0001
Revises:
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаёт схему zn, расширения PostGIS и таблицу asset."""
    # Схема zn — все таблицы домена живут здесь, не в public.
    op.execute("CREATE SCHEMA IF NOT EXISTS zn")

    # Расширения PostGIS. Должны быть установлены на сервере (образ postgis/postgis).
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")

    op.create_table(
        "asset",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cad_number", sa.String(length=40), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "geometry",
            Geometry(geometry_type="POLYGON", srid=4326),
            nullable=True,
        ),
        sa.Column("area", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("owner_type", sa.String(length=30), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        schema="zn",
    )

    op.create_index(
        "uq_asset_cad_number",
        "asset",
        ["cad_number"],
        unique=True,
        schema="zn",
    )
    op.create_index(
        "ix_asset_geometry",
        "asset",
        ["geometry"],
        postgresql_using="gist",
        schema="zn",
    )
    op.create_index(
        "ix_asset_status",
        "asset",
        ["status"],
        schema="zn",
    )

    # Триггер: updated_at обновляется автоматически при UPDATE.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION zn.tg_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER asset_set_updated_at
        BEFORE UPDATE ON zn.asset
        FOR EACH ROW
        EXECUTE FUNCTION zn.tg_set_updated_at();
        """
    )


def downgrade() -> None:
    """Откатывает миграцию: удаляет таблицу и функцию триггера."""
    op.execute("DROP TRIGGER IF EXISTS asset_set_updated_at ON zn.asset")
    op.execute("DROP FUNCTION IF EXISTS zn.tg_set_updated_at()")
    op.drop_index("ix_asset_status", table_name="asset", schema="zn")
    op.drop_index("ix_asset_geometry", table_name="asset", schema="zn")
    op.drop_index("uq_asset_cad_number", table_name="asset", schema="zn")
    op.drop_table("asset", schema="zn")
