"""Идемпотентный ингест записей НСПД в zn.asset + zn.parcel + журнал zn.event.

Ключ идемпотентности — `cad_number`. Повторный прогон обновляет поля, а не
плодит дубли. На создании пишется событие `ingested`; на обновлении сравниваются
отслеживаемые поля и на каждое изменение добавляется событие (cad_value_changed,
permitted_use_changed, category_changed) — так ETL питает мониторинг (веха 0008).
Коммит — за вызывающим (скрипт/задача), чтобы вся пачка легла одной транзакцией.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.etl.nspd import mapper
from app.modules.asset.models import Asset
from app.modules.event import crud as event_crud
from app.modules.parcel.models import Parcel

# Поля asset, которые ETL обновляет на существующей записи (cad_number/kind — нет).
_ASSET_MUTABLE = ("address", "area", "category", "owner_type", "geometry")
_PARCEL_FIELDS = (
    "land_category", "permitted_use", "zone_code",
    "cadastral_quarter", "cadastral_value", "raw",
)

# Изменение какого поля → какой тип события. (источник значения, имя поля) → тип.
_TRACKED = (
    ("parcel", "cadastral_value", "cad_value_changed"),
    ("parcel", "permitted_use", "permitted_use_changed"),
    ("asset", "category", "category_changed"),
)


@dataclass
class IngestResult:
    cad_number: str
    asset_id: int
    created: bool                       # True — новый asset, False — обновлён
    events: list[str] = field(default_factory=list)  # типы записанных событий


@dataclass
class IngestSummary:
    created: int = 0
    updated: int = 0
    failed: int = 0
    events: int = 0

    @property
    def total(self) -> int:
        return self.created + self.updated + self.failed


def _norm(value):
    """Числа приводим к float для устойчивого сравнения (Numeric→Decimal vs float)."""
    if isinstance(value, (int, float)):
        return float(value)
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    return value


def ingest_one(db: Session, raw: dict) -> IngestResult:
    """Вставляет или обновляет один участок + пишет события. Не коммитит."""
    asset_fields = mapper.map_asset_fields(raw)
    parcel_fields = mapper.map_parcel_fields(raw)
    cad = asset_fields["cad_number"]

    asset = db.query(Asset).filter(Asset.cad_number == cad).one_or_none()
    created = asset is None
    events: list[str] = []

    if created:
        asset = Asset(**asset_fields)
        db.add(asset)
        db.flush()
        parcel = Parcel(asset_id=asset.id, **parcel_fields)
        db.add(parcel)
        db.flush()
        event_crud.record_event(db, asset.id, "ingested", {"cad_number": cad})
        events.append("ingested")
        return IngestResult(cad_number=cad, asset_id=asset.id, created=True, events=events)

    # ── обновление: сначала снимок старых отслеживаемых значений ──
    parcel = db.get(Parcel, asset.id)
    # ВАЖНО: нельзя называть обе "неиспользуемые" позиции кортежа одинаково (`_`) —
    # `for _, f, _ in _TRACKED` привязывает `_` к ПОСЛЕДНЕМУ элементу (etype), а не
    # к src, поэтому `if _ == "asset"`/`"parcel"` сравнивались с etype и были ВСЕГДА
    # False — снимок `old` оставался пустым, диффы никогда не находились, и события
    # cad_value_changed/permitted_use_changed/category_changed никогда не писались.
    old = {
        ("asset", f): getattr(asset, f) for src, f, _etype in _TRACKED if src == "asset"
    }
    if parcel is not None:
        old.update({
            ("parcel", f): getattr(parcel, f)
            for src, f, _etype in _TRACKED if src == "parcel"
        })

    for f in _ASSET_MUTABLE:
        setattr(asset, f, asset_fields[f])
    db.flush()

    if parcel is None:
        parcel = Parcel(asset_id=asset.id, **parcel_fields)
        db.add(parcel)
    else:
        for f in _PARCEL_FIELDS:
            setattr(parcel, f, parcel_fields[f])
    db.flush()

    # ── диф старое/новое → события ──
    new_source = {"asset": asset_fields, "parcel": parcel_fields}
    for src, fname, etype in _TRACKED:
        if (src, fname) not in old:
            continue
        old_v, new_v = _norm(old[(src, fname)]), _norm(new_source[src][fname])
        if old_v != new_v:
            event_crud.record_event(
                db, asset.id, etype, {"field": fname, "old": old_v, "new": new_v}
            )
            events.append(etype)

    return IngestResult(cad_number=cad, asset_id=asset.id, created=False, events=events)


def ingest_many(db: Session, raws: list[dict]) -> IngestSummary:
    """Ингест пачки. Сбойная запись не валит остальные (счётчик failed)."""
    summary = IngestSummary()
    for raw in raws:
        try:
            result = ingest_one(db, raw)
            if result.created:
                summary.created += 1
            else:
                summary.updated += 1
            summary.events += len(result.events)
        except Exception:
            summary.failed += 1
    return summary
