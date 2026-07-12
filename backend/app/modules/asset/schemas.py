"""Pydantic-схемы для Asset module.

Отделяем API-контракт (schemas) от персистентной модели (models):
  - models.py — как хранится в БД (geometry как WKB-бинарник в PostGIS).
  - schemas.py — как отдаётся/принимается через API (geometry как GeoJSON).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Формат кадастрового номера: XX:XX:XXXXXX:XXX (регион:район:квартал:участок).
CAD_NUMBER_PATTERN = r"^\d{2}:\d{2}:\d{6,7}:\d{1,4}$"

OwnerType = Literal["state", "municipal", "private", "unknown"]
AssetStatus = Literal["active", "archived", "deleted"]


class AssetBase(BaseModel):
    """Общие поля для создания/чтения."""

    model_config = ConfigDict(from_attributes=True)

    cad_number: str = Field(pattern=CAD_NUMBER_PATTERN)
    address: str | None = None
    geometry: dict | None = Field(default=None, description="GeoJSON geometry")
    area: float | None = None
    category: str | None = None
    owner_type: OwnerType | None = None
    status: AssetStatus = "active"


class AssetRead(AssetBase):
    """Схема ответа GET /asset/{cad_number}."""

    id: int
    created_at: datetime
    updated_at: datetime


class AssetCreate(AssetBase):
    """Схема создания (для будущих POST-эндпоинтов и ETL)."""

    @field_validator("cad_number")
    @classmethod
    def normalize_cad_number(cls, v: str) -> str:
        return v.strip()
