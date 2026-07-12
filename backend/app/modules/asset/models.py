"""Asset domain model.

Соответствует доменной сущности Asset — см. docs/domain-model.md.
Схема таблицы описана в docs/database.md.
"""

from datetime import datetime
from typing import Literal

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Допустимые значения owner_type и status — фиксируются на уровне типа.
OwnerType = Literal["state", "municipal", "private", "unknown"]
AssetStatus = Literal["active", "archived", "deleted"]


class Asset(Base):
    """Любой объект недвижимости (MVP: земельный участок).

    Кадастровый номер — естественный ключ, по которому идентифицируется объект
    во внешних источниках (Росреестр, НСПД). Уникален.
    """

    __tablename__ = "asset"
    __table_args__ = (
        # Уникальный индекс по cad_number — защита от дублей и быстрый поиск.
        Index("uq_asset_cad_number", "cad_number", unique=True),
        # GIST-индекс по геометрии — для пространственных запросов.
        Index("ix_asset_geometry", "geometry", postgresql_using="gist"),
        # B-tree по статусу — частый фильтр active/archived.
        Index("ix_asset_status", "status"),
        {"schema": "zn"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cad_number: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326)
    )
    area: Mapped[float | None] = mapped_column(Numeric(12, 2))
    category: Mapped[str | None] = mapped_column(String(100))
    owner_type: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} cad_number={self.cad_number!r} status={self.status!r}>"
