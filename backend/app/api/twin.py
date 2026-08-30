"""Digital Twin API.

GET  /api/v1/asset/{cad_number}/twin                  — полный цифровой двойник (агрегат).
POST /api/v1/asset/{cad_number}/opportunity/recompute — пересчитать Opportunity Score.
POST /api/v1/asset/{cad_number}/insights/regenerate   — пересобрать AI-инсайты (SWOT/explanation).

Лёгкая карточка объекта остаётся на GET /api/v1/asset/{cad_number}.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.asset import _asset_to_read
from app.database.session import get_db
from app.modules.ai_insight import crud as insight_crud
from app.modules.ai_insight import generator
from app.modules.ai_insight.schemas import AIInsightRead
from app.modules.asset import crud as asset_crud
from app.modules.asset.schemas import CAD_NUMBER_PATTERN
from app.modules.opportunity import crud as opp_crud
from app.modules.opportunity import scoring
from app.modules.opportunity.schemas import OpportunityRead
from app.modules.parcel import crud as parcel_crud
from app.modules.parcel.schemas import ParcelRead
from app.modules.restriction import crud as restriction_crud
from app.modules.restriction.schemas import RestrictionRead
from app.modules.event import crud as event_crud
from app.modules.event.schemas import EventRead
from app.modules.twin.schemas import DigitalTwinRead

router = APIRouter(prefix="/asset", tags=["twin"])


def _load_asset_or_404(db: Session, cad_number: str):
    asset = asset_crud.get_asset_by_cad_number(db, cad_number)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    return asset


def _ensure_current_opportunity(db: Session, asset, parcel, restrictions):
    """Возвращает текущий Opportunity; если его нет — считает и сохраняет.

    Инсайты объясняют именно скоринг, поэтому он обязан существовать.
    """
    opp = opp_crud.get_current(db, asset.id)
    if opp is None:
        computed = scoring.compute_score(asset, parcel, restrictions)
        opp = opp_crud.save_new_version(db, asset.id, computed)
    return opp


@router.get(
    "/{cad_number}/twin",
    response_model=DigitalTwinRead,
    summary="Получить Digital Twin по кадастровому номеру",
    description="Агрегат: asset + parcel + ограничения + инвест-возможность + AI-инсайты.",
    responses={404: {"description": "Актив не найден"}},
)
def get_twin(
    cad_number: str = Path(..., pattern=CAD_NUMBER_PATTERN),
    db: Session = Depends(get_db),
) -> DigitalTwinRead:
    asset = _load_asset_or_404(db, cad_number)
    parcel = parcel_crud.get_parcel(db, asset.id)
    restrictions = restriction_crud.list_restrictions(db, asset.id)
    opportunity = opp_crud.get_current(db, asset.id)
    insights = insight_crud.list_current(db, asset.id)
    recent_events = event_crud.list_recent(db, asset.id, limit=20)
    return DigitalTwinRead(
        asset=_asset_to_read(asset),
        parcel=ParcelRead.model_validate(parcel) if parcel is not None else None,
        restrictions=[RestrictionRead.model_validate(r) for r in restrictions],
        opportunity=(
            OpportunityRead.model_validate(opportunity)
            if opportunity is not None
            else None
        ),
        insights=[AIInsightRead.model_validate(i) for i in insights],
        recent_events=[EventRead.model_validate(e) for e in recent_events],
    )


@router.post(
    "/{cad_number}/opportunity/recompute",
    response_model=OpportunityRead,
    status_code=status.HTTP_201_CREATED,
    summary="Пересчитать Opportunity Score",
    description="Считает прозрачный взвешенный скоринг из parcel+ограничений и "
    "сохраняет новую версию (предыдущая помечается неактуальной).",
    responses={404: {"description": "Актив не найден"}},
)
def recompute_opportunity(
    cad_number: str = Path(..., pattern=CAD_NUMBER_PATTERN),
    db: Session = Depends(get_db),
) -> OpportunityRead:
    asset = _load_asset_or_404(db, cad_number)
    parcel = parcel_crud.get_parcel(db, asset.id)
    restrictions = restriction_crud.list_restrictions(db, asset.id)
    computed = scoring.compute_score(asset, parcel, restrictions)
    opp = opp_crud.save_new_version(db, asset.id, computed)
    db.commit()
    db.refresh(opp)
    return OpportunityRead.model_validate(opp)


@router.post(
    "/{cad_number}/insights/regenerate",
    response_model=list[AIInsightRead],
    status_code=status.HTTP_201_CREATED,
    summary="Пересобрать AI-инсайты",
    description="Строит SWOT/explanation поверх текущего Opportunity Score "
    "(если скоринга нет — считает его). Новые версии заменяют прежние по категории.",
    responses={404: {"description": "Актив не найден"}},
)
def regenerate_insights(
    cad_number: str = Path(..., pattern=CAD_NUMBER_PATTERN),
    db: Session = Depends(get_db),
) -> list[AIInsightRead]:
    asset = _load_asset_or_404(db, cad_number)
    parcel = parcel_crud.get_parcel(db, asset.id)
    restrictions = restriction_crud.list_restrictions(db, asset.id)
    opportunity = _ensure_current_opportunity(db, asset, parcel, restrictions)

    generated = generator.generate(asset, parcel, restrictions, opportunity)
    saved = [insight_crud.save_new_version(db, asset.id, g) for g in generated]
    db.commit()
    for ins in saved:
        db.refresh(ins)
    return [AIInsightRead.model_validate(i) for i in saved]
