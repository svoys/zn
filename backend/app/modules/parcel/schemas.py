"""Pydantic-схемы Parcel."""

from pydantic import BaseModel, ConfigDict


class ParcelRead(BaseModel):
    """Правовой слой участка в составе Digital Twin."""

    model_config = ConfigDict(from_attributes=True)

    land_category: str | None = None
    permitted_use: str | None = None
    permitted_use_aux: dict | None = None
    zone_code: str | None = None
    cadastral_quarter: str | None = None
    cadastral_value: float | None = None


class ParcelUpsert(ParcelRead):
    """Схема для записи (ETL/POST) — тот же набор полей."""
