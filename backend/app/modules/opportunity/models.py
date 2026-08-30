"""Opportunity ⭐ — инвестиционная возможность (версионируется).

Каждый пересчёт Opportunity Score пишет НОВУЮ строку; предыдущая помечается
is_current=false. История сохраняется (принцип №4). Explainability: разложение
скоринга лежит в `factors` (JSONB) с указанием источника каждого фактора.
См. docs/digital-twin-design.md.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Opportunity(Base):
    __tablename__ = "opportunity"
    __table_args__ = (
        Index("ix_opportunity_asset", "asset_id"),
        # Быстрый доступ к текущей версии. Ограничение «одна текущая на asset»
        # (partial UNIQUE WHERE is_current) создаётся сырым SQL в миграции 0006 —
        # SQLAlchemy Index не выражает его переносимо.
        Index("ix_opportunity_asset_current", "asset_id", "is_current"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_opportunity_score"),
        {"schema": "zn"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zn.asset.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rating: Mapped[str | None] = mapped_column(String(2))
    rationale: Mapped[str | None] = mapped_column(Text)
    factors: Mapped[list | None] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    computed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Opportunity asset_id={self.asset_id} score={self.score} current={self.is_current}>"
