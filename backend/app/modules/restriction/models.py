"""Restriction domain model — ограничения/ЗОУИТ/обременения участка.

1:* к asset. `severity` (0..100) — вклад ограничения в риск и в Opportunity Score.
Геометрия зоны опциональна (зона может пересекать участок частично).
См. docs/digital-twin-design.md.
"""

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Типы ограничений — справочник фиксируется CHECK-констрейнтом.
RESTRICTION_KINDS = ("zouit", "easement", "protective_zone", "flood", "encumbrance", "other")


class Restriction(Base):
    __tablename__ = "restriction"
    __table_args__ = (
        Index("ix_restriction_asset", "asset_id"),
        Index("ix_restriction_geometry", "geometry", postgresql_using="gist"),
        CheckConstraint(
            "kind IN ('zouit', 'easement', 'protective_zone', 'flood', 'encumbrance', 'other')",
            name="ck_restriction_kind",
        ),
        CheckConstraint(
            "severity IS NULL OR (severity >= 0 AND severity <= 100)",
            name="ck_restriction_severity",
        ),
        {"schema": "zn"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("zn.asset.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[int | None] = mapped_column(SmallInteger)
    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326)
    )
    source: Mapped[str | None] = mapped_column(String(120))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __repr__(self) -> str:
        return f"<Restriction id={self.id} kind={self.kind!r} severity={self.severity}>"
