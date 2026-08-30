"""Pydantic-схемы Opportunity."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OpportunityFactor(BaseModel):
    """Один фактор скоринга — с вкладом и источником (explainability)."""

    factor: str
    weight: float
    value: float = Field(description="Нормализованное значение 0..1")
    contribution: float = Field(description="Вклад в итоговый балл, 0..100")
    source: str


class OpportunityRead(BaseModel):
    """Текущая инвестиционная возможность в составе Digital Twin."""

    model_config = ConfigDict(from_attributes=True)

    score: int = Field(ge=0, le=100)
    rating: str | None = None
    rationale: str | None = None
    factors: list[OpportunityFactor] | None = None
    model_version: str
    computed_at: datetime
