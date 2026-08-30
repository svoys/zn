"""CRUD для Event — append-only лента изменений."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.event.models import Event


def record_event(
    db: Session, asset_id: int | None, type: str, payload: dict | None = None
) -> Event:
    """Добавляет событие. Коммит остаётся за вызывающим."""
    event = Event(asset_id=asset_id, type=type, payload=payload)
    db.add(event)
    db.flush()
    return event


def list_recent(db: Session, asset_id: int, limit: int = 20) -> list[Event]:
    """Последние события участка, свежие сверху."""
    stmt = (
        select(Event)
        .where(Event.asset_id == asset_id)
        .order_by(Event.occurred_at.desc(), Event.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
