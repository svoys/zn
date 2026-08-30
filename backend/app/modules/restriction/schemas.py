"""Pydantic-схемы Restriction."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class RestrictionRead(BaseModel):
    """Ограничение в составе Digital Twin."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    description: str | None = None
    severity: int | None = None
    source: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
