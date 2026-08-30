"""add CHECK constraints on asset.owner_type and asset.status

Фиксируем справочники owner_type/status на уровне БД, чтобы ETL и прямые
вставки не могли записать значение вне списка. Схема чтения (AssetRead)
остаётся терпимой к возможному дрейфу — см. app/modules/asset/schemas.py.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_asset_owner_type",
        "asset",
        "owner_type IN ('state', 'municipal', 'private', 'unknown') OR owner_type IS NULL",
        schema="zn",
    )
    op.create_check_constraint(
        "ck_asset_status",
        "asset",
        "status IN ('active', 'archived', 'deleted')",
        schema="zn",
    )


def downgrade() -> None:
    op.drop_constraint("ck_asset_status", "asset", schema="zn", type_="check")
    op.drop_constraint("ck_asset_owner_type", "asset", schema="zn", type_="check")
