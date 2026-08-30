"""CRUD для AIInsight — версионирование через is_current по (asset_id, kind)."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.ai_insight.models import AIInsight


def list_current(db: Session, asset_id: int) -> list[AIInsight]:
    """Все актуальные инсайты участка (по одному на категорию)."""
    stmt = (
        select(AIInsight)
        .where(AIInsight.asset_id == asset_id, AIInsight.is_current.is_(True))
        .order_by(AIInsight.kind)
    )
    return list(db.execute(stmt).scalars().all())


def get_current(db: Session, asset_id: int, kind: str) -> AIInsight | None:
    """Текущий инсайт заданной категории."""
    stmt = select(AIInsight).where(
        AIInsight.asset_id == asset_id,
        AIInsight.kind == kind,
        AIInsight.is_current.is_(True),
    )
    return db.execute(stmt).scalar_one_or_none()


def save_new_version(db: Session, asset_id: int, generated: dict) -> AIInsight:
    """Сохраняет новую версию инсайта, снимая is_current с прежней той же категории.

    Коммит остаётся за вызывающим.
    """
    kind = generated["kind"]
    db.execute(
        update(AIInsight)
        .where(
            AIInsight.asset_id == asset_id,
            AIInsight.kind == kind,
            AIInsight.is_current.is_(True),
        )
        .values(is_current=False)
    )
    db.flush()

    insight = AIInsight(
        asset_id=asset_id,
        kind=kind,
        content=generated["content"],
        trace=generated.get("trace"),
        model_version=generated["model_version"],
        is_current=True,
    )
    db.add(insight)
    db.flush()
    return insight
