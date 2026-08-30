"""Asset API routes.

GET /api/v1/asset/{cad_number} — карточка объекта (Digital Twin).
"""


from fastapi import APIRouter, Depends, HTTPException, Path, status
from geoalchemy2.shape import to_shape
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.asset import crud
from app.modules.asset.models import Asset
from app.modules.asset.schemas import CAD_NUMBER_PATTERN, AssetRead

router = APIRouter(prefix="/asset", tags=["asset"])


def _asset_to_read(asset: Asset) -> AssetRead:
    """Конвертирует ORM-модель в схему ответа, превращая geometry в GeoJSON.

    GeoAlchemy2 хранит геометрию как WKB-бинарник. `to_shape` превращает его
    в shapely-объект, `__geo_interface__` — в GeoJSON-совместимый dict.
    Без обращения к БД — всё в памяти.
    """
    data = {c.name: getattr(asset, c.name) for c in asset.__table__.columns}
    if asset.geometry is not None:
        data["geometry"] = to_shape(asset.geometry).__geo_interface__
    return AssetRead.model_validate(data)


@router.get(
    "/{cad_number}",
    response_model=AssetRead,
    summary="Получить актив по кадастровому номеру",
    description="Возвращает цифровой двойник объекта (Digital Twin).",
    responses={
        404: {"description": "Актив не найден", "content": {"application/json": {"example": {"detail": "Asset not found"}}}},
    },
)
def get_asset(
    cad_number: str = Path(
        ...,
        description="Кадастровый номер формата XX:XX:XXXXXX:XXX",
        pattern=CAD_NUMBER_PATTERN,
    ),
    db: Session = Depends(get_db),
) -> AssetRead:
    asset = crud.get_asset_by_cad_number(db, cad_number)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    return _asset_to_read(asset)
