"""Search API routes.

GET /api/v1/search — умный поиск активов с фильтрами и пагинацией.
Контракт: docs/api.md → "GET /api/v1/search".
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.asset.models import Asset
from app.modules.search import crud
from app.modules.search.schemas import AssetPage

router = APIRouter(prefix="/search", tags=["search"])


def _asset_to_dict(asset: Asset) -> dict:
    """Конвертирует ORM-модель в dict для AssetRead-схемы, превращая geometry в GeoJSON.

    Дублирует логику из app/api/asset.py — пока без рефакторинга, чтобы не
    плодить shared-зависимости на раннем этапе.
    """
    from geoalchemy2.shape import to_shape

    data = {c.name: getattr(asset, c.name) for c in asset.__table__.columns}
    if asset.geometry is not None:
        data["geometry"] = to_shape(asset.geometry).__geo_interface__
    return data


@router.get(
    "",
    response_model=AssetPage,
    summary="Поиск активов с фильтрами и пагинацией",
    description="Возвращает страницу активов по переданным фильтрам. Все фильтры комбинируются через AND.",
    status_code=status.HTTP_200_OK,
)
def search_assets(
    q: str | None = Query(default=None, description="Текстовый поиск по address и cad_number"),
    region: str | None = Query(default=None, description="Код региона (первые 2 цифры cad_number)"),
    area_min: float | None = Query(default=None, ge=0, description="Мин. площадь, кв.м"),
    area_max: float | None = Query(default=None, ge=0, description="Макс. площадь, кв.м"),
    category: str | None = Query(default=None, description="Точное совпадение категории"),
    # alias="status" сохраняет внешний контракт API (?status=...), а имя
    # параметра status_filter не затеняет импортированный fastapi.status.
    status_filter: str = Query(
        default="active", alias="status", description="Статус актива"
    ),
    limit: int = Query(default=20, ge=1, le=100, description="Размер страницы"),
    offset: int = Query(default=0, ge=0, description="Сдвиг пагинации"),
    db: Session = Depends(get_db),
) -> AssetPage:
    items, total = crud.search_assets(
        db,
        q=q,
        region=region,
        area_min=area_min,
        area_max=area_max,
        category=category,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return AssetPage(
        items=[_asset_to_dict(a) for a in items],
        total=total,
        limit=limit,
        offset=offset,
    )
