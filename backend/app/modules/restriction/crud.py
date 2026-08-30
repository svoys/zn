"""CRUD для Restriction."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.restriction.models import Restriction


def list_restrictions(db: Session, asset_id: int) -> list[Restriction]:
    """Все ограничения участка, тяжёлые сначала (severity DESC NULLS LAST)."""
    stmt = (
        select(Restriction)
        .where(Restriction.asset_id == asset_id)
        .order_by(Restriction.severity.desc().nullslast(), Restriction.id)
    )
    return list(db.execute(stmt).scalars().all())
