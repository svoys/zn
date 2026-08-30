"""Digital Twin — агрегатная схема чтения (read-model).

Собирается на лету из asset + parcel + restrictions + текущий opportunity +
актуальные ai_insight + недавние events. Это не таблица, а композиция.
См. docs/digital-twin-design.md.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.modules.ai_insight.schemas import AIInsightRead
from app.modules.asset.schemas import AssetRead
from app.modules.event.schemas import EventRead
from app.modules.opportunity.schemas import OpportunityRead
from app.modules.parcel.schemas import ParcelRead
from app.modules.restriction.schemas import RestrictionRead


class DigitalTwinRead(BaseModel):
    """Полный цифровой двойник объекта.

    Несёт базовый asset, правовой слой parcel, ограничения, текущую
    инвестиционную возможность, актуальные AI-инсайты и ленту недавних событий.
    """

    model_config = ConfigDict(from_attributes=True)

    asset: AssetRead
    parcel: ParcelRead | None = None
    restrictions: list[RestrictionRead] = Field(default_factory=list)
    opportunity: OpportunityRead | None = None
    insights: list[AIInsightRead] = Field(default_factory=list)
    recent_events: list[EventRead] = Field(default_factory=list)
