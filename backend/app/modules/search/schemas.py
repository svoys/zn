"""Pydantic-схемы для модуля search.

AssetRead переиспользуется из модуля asset — контракт един для всех эндпоинтов,
отдающих актив. Здесь добавляем только обёртку с пагинацией.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.modules.asset.schemas import AssetRead


class AssetPage(BaseModel):
    """Страница результатов поиска с метаданными пагинации.

    Используется как response_model для GET /api/v1/search.
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[AssetRead]
    total: int = Field(ge=0, description="Общее число записей под фильтры")
    limit: int = Field(ge=1, le=100, description="Размер страницы")
    offset: int = Field(ge=0, description="Сдвиг пагинации")
