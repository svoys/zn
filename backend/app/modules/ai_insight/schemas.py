"""Pydantic-схемы AIInsight."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AIInsightRead(BaseModel):
    """Инсайт в составе Digital Twin."""

    model_config = ConfigDict(from_attributes=True)

    kind: str
    content: dict
    trace: dict | None = None
    model_version: str
    created_at: datetime
