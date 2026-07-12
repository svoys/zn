"""CRUD operations for Asset.

Изолирует DB-логику от HTTP-слоя. Эндпоинты вызывают эти функции и не пишут
SQL напрямую — так легче тестировать и переиспользовать из Telegram/ETL.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.asset.models import Asset
from app.modules.asset.schemas import AssetCreate


def get_asset_by_cad_number(db: Session, cad_number: str) -> Asset | None:
    """Возвращает актив по кадастровому номеру или None."""
    stmt = select(Asset).where(Asset.cad_number == cad_number)
    return db.execute(stmt).scalar_one_or_none()


def create_asset(db: Session, payload: AssetCreate) -> Asset:
    """Создаёт новый актив. Коммит остаётся за вызывающим (FastAPI-зависимость)."""
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.flush()
    return asset
