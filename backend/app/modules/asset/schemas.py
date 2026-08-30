"""Pydantic-схемы для Asset module.

Отделяем API-контракт (schemas) от персистентной модели (models):
  - models.py — как хранится в БД (geometry как WKB-бинарник в PostGIS).
  - schemas.py — как отдаётся/принимается через API (geometry как GeoJSON).

Асимметрия строгости owner_type/status:
  - На ЗАПИСЬ (AssetCreate) — строгий Literal: не пускаем мусор в БД.
  - На ЧТЕНИЕ (AssetRead) — свободный str: если ETL/внешний источник записал
    значение вне справочника, GET-эндпоинт не должен падать с 500 на
    сериализации. Целостность на чтении подстрахована CHECK-констрейнтами в БД
    (миграция 0002), но схема чтения остаётся терпимой к дрейфу данных.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Формат кадастрового номера: XX:XX:XXXXXX:XXX (регион:район:квартал:участок).
CAD_NUMBER_PATTERN = r"^\d{2}:\d{2}:\d{6,7}:\d{1,4}$"

OwnerType = Literal["state", "municipal", "private", "unknown"]
AssetStatus = Literal["active", "archived", "deleted"]


class AssetBase(BaseModel):
    """Общие поля объекта (без owner_type/status — они различаются по строгости)."""

    model_config = ConfigDict(from_attributes=True)

    cad_number: str = Field(pattern=CAD_NUMBER_PATTERN)
    kind: str = Field(default="parcel", description="Тип объекта (MVP: parcel)")
    address: str | None = None
    geometry: dict | None = Field(default=None, description="GeoJSON geometry")
    area: float | None = None
    category: str | None = None


class AssetRead(AssetBase):
    """Схема ответа GET /asset/{cad_number} и элемент страницы поиска.

    owner_type/status — свободные строки (терпимость к дрейфу данных из ETL).
    """

    id: int
    owner_type: str | None = None
    status: str = "active"
    created_at: datetime
    updated_at: datetime


class AssetCreate(AssetBase):
    """Схема создания (для будущих POST-эндпоинтов и ETL) — строгая валидация."""

    owner_type: OwnerType | None = None
    status: AssetStatus = "active"

    @field_validator("cad_number")
    @classmethod
    def normalize_cad_number(cls, v: str) -> str:
        return v.strip()
