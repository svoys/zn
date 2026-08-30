"""CRUD для Parcel."""

from sqlalchemy.orm import Session

from app.modules.parcel.models import Parcel


def get_parcel(db: Session, asset_id: int) -> Parcel | None:
    """Возвращает правовой слой участка по asset_id или None."""
    return db.get(Parcel, asset_id)
