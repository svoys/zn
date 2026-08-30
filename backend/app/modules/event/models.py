"""Event — журнал изменений/мониторинг актива (append-only).

Принцип №4 «все изменения объектов сохраняются во времени»: события НЕ
обновляются и не удаляются, только добавляются. Источник — ETL (сравнение старой
и новой выгрузки) и, позже, внешние сигналы (аукционы, объявления). `asset_id`
nullable: null = событие территории/района, не привязанное к конкретному участку.
См. docs/digital-twin-design.md §2.5.
"""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Типы событий. Справочник намеренно НЕ зашит в CHECK — источников со временем
# станет много (ETL/аукционы/объявления), список будет расти; валидацию держим
# в коде (EVENT_TYPES), а не в БД, чтобы не плодить миграции на каждый новый тип.
EVENT_TYPES = (
    "cad_value_changed",
    "permitted_use_changed",
    "category_changed",
    "zoning_changed",
    "new_auction_nearby",
    "price_drop",
    "ingested",
)


class Event(Base):
    __tablename__ = "event"
    __table_args__ = (
        # Лента событий участка «свежие сверху» — частый запрос для Digital Twin.
        Index("ix_event_asset_occurred", "asset_id", "occurred_at"),
        Index("ix_event_type", "type"),
        {"schema": "zn"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("zn.asset.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Event id={self.id} type={self.type!r} asset_id={self.asset_id}>"
