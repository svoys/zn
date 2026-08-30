"""CRUD для Opportunity — версионирование через is_current."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.opportunity.models import Opportunity


def get_current(db: Session, asset_id: int) -> Opportunity | None:
    """Текущая (актуальная) инвестиционная возможность участка."""
    stmt = select(Opportunity).where(
        Opportunity.asset_id == asset_id,
        Opportunity.is_current.is_(True),
    )
    return db.execute(stmt).scalar_one_or_none()


def save_new_version(db: Session, asset_id: int, computed: dict) -> Opportunity:
    """Сохраняет новую версию скоринга, снимая флаг is_current со старых.

    Коммит остаётся за вызывающим (FastAPI-зависимостью).
    """
    # Снять текущий флаг со всех предыдущих версий этого актива.
    db.execute(
        update(Opportunity)
        .where(Opportunity.asset_id == asset_id, Opportunity.is_current.is_(True))
        .values(is_current=False)
    )
    db.flush()

    opp = Opportunity(
        asset_id=asset_id,
        score=computed["score"],
        rating=computed["rating"],
        rationale=computed["rationale"],
        factors=computed["factors"],
        model_version=computed["model_version"],
        is_current=True,
    )
    db.add(opp)
    db.flush()
    return opp
