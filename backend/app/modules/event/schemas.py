"""Pydantic-схемы Event."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    """Событие в ленте Digital Twin."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    payload: dict | None = None
    occurred_at: datetime
