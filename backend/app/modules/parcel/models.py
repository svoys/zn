"""Parcel domain model — правовой/градостроительный слой земельного участка.

1:1-расширение Asset: asset_id — одновременно PK и FK на zn.asset (shared PK).
Asset отвечает «что и где», Parcel — «какие правовые атрибуты у участка».
См. docs/digital-twin-design.md.
"""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Parcel(Base):
    __tablename__ = "parcel"
    __table_args__ = {"schema": "zn"}

    asset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("zn.asset.id", ondelete="CASCADE"),
        primary_key=True,
    )
    land_category: Mapped[str | None] = mapped_column(String(120))
    permitted_use: Mapped[str | None] = mapped_column(Text)
    permitted_use_aux: Mapped[dict | None] = mapped_column(JSONB)
    zone_code: Mapped[str | None] = mapped_column(String(60))
    cadastral_quarter: Mapped[str | None] = mapped_column(String(20))
    cadastral_value: Mapped[float | None] = mapped_column(Numeric(18, 2))
    raw: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    asset = relationship("Asset", backref="parcel", uselist=False)

    def __repr__(self) -> str:
        return f"<Parcel asset_id={self.asset_id} zone={self.zone_code!r}>"
