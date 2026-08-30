"""AIInsight — структурированный вывод AI поверх посчитанных данных.

Принципиально: инсайт НЕ выдумывает цифры. Он объясняет уже вычисленные факторы
Opportunity Score и ограничения (SWOT / risk / explanation). Числа берутся из
`opportunity.factors`; LLM (веха-плюс) пишет только текст. `trace` (JSONB) хранит,
на каких данных/источниках построен вывод — для объяснимости.

Версионируется по (asset_id, kind): каждый пересчёт пишет новую строку, прежняя
той же категории помечается is_current=false. История сохраняется (принцип №4).
См. docs/digital-twin-design.md §2.4.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Категории инсайтов — справочник фиксируется CHECK-констрейнтом.
INSIGHT_KINDS = ("swot", "risk", "scenario", "explanation")


class AIInsight(Base):
    __tablename__ = "ai_insight"
    __table_args__ = (
        Index("ix_ai_insight_asset", "asset_id"),
        # Быстрый доступ к текущим версиям по категории. Ограничение
        # «одна текущая на (asset, kind)» (partial UNIQUE WHERE is_current)
        # создаётся сырым SQL в миграции 0007.
        Index("ix_ai_insight_asset_current", "asset_id", "kind", "is_current"),
        CheckConstraint(
            "kind IN ('swot', 'risk', 'scenario', 'explanation')",
            name="ck_ai_insight_kind",
        ),
        {"schema": "zn"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zn.asset.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trace: Mapped[dict | None] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<AIInsight asset_id={self.asset_id} kind={self.kind} current={self.is_current}>"
