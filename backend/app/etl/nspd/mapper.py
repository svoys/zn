"""Маппинг сырого ответа НСПД → поля Asset и Parcel.

⚠️ ПО ПРЕДПОЛОЖЕНИЯМ о структуре ответа (реальных данных пока нет). Маппер
намеренно защитный: каждое поле берётся из НЕСКОЛЬКИХ вероятных ключей через
`_first()`, чего не хватает — становится None (schemas чтения терпимы, БД-CHECK'и
не пропустят мусор в enum'ы). Полный сырой ответ всегда сохраняется в
`parcel.raw`, поэтому даже при неверном маппинге данные не теряются.

Когда появится реальный НСПД — уточнить ключи в *_KEYS и SOURCE_SRID.
"""

from __future__ import annotations

from typing import Any

from geoalchemy2.shape import from_shape

try:  # shapely используется и в остальном проекте (to_shape при чтении)
    from shapely.geometry import shape as shapely_shape
except Exception:  # pragma: no cover - shapely обязателен в рантайме
    shapely_shape = None

# Предполагаемая CRS геометрии в ответе. Если реальный источник не 4326 —
# здесь добавить репроекцию (pyproj) перед from_shape.
SOURCE_SRID = 4326

# Кандидаты ключей (порядок = приоритет). Уточнить по реальному ответу НСПД.
CAD_KEYS = ("cadastral_number", "cad_number", "cadNumber", "cn")
ADDRESS_KEYS = ("address", "readable_address", "addressReadable")
AREA_KEYS = ("area_value", "area", "areaValue")
CATEGORY_KEYS = ("category_type", "land_category", "category", "categoryType")
PERMITTED_USE_KEYS = (
    "permitted_use_established_by_document",
    "permitted_use",
    "utilization",
    "permittedUse",
)
CAD_QUARTER_KEYS = ("cadastral_quarter", "cad_quarter", "quarter")
ZONE_KEYS = ("zone_code", "territorial_zone", "zone")
OWNER_KEYS = ("ownership_type", "ownership", "owner_type", "form_of_ownership")
GEOMETRY_KEYS = ("geometry", "geom", "extent")

# Нормализация формы собственности → enum asset.owner_type.
_OWNER_MAP = {
    "государственная": "state",
    "федеральная": "state",
    "субъект": "state",
    "муниципальная": "municipal",
    "частная": "private",
    "собственность граждан": "private",
    "собственность юридических лиц": "private",
}


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in raw and raw[k] not in (None, "", []):
            return raw[k]
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):  # напр. {"value": 1234.5, "unit": "кв.м"}
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_owner_type(value: Any) -> str | None:
    """Русскую форму собственности → enum (state/municipal/private/unknown/None)."""
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("type") or value.get("name")
    text = str(value).strip().lower()
    for needle, code in _OWNER_MAP.items():
        if needle in text:
            return code
    return "unknown"


def _cad_value(raw: dict[str, Any]) -> float | None:
    # Кадастровая стоимость встречается в разных обёртках.
    for key in ("cadastral_cost", "cadastral_value", "cost", "cadastralCost"):
        if key in raw:
            return _to_float(raw[key])
    return None


def _parse_geometry(raw: dict[str, Any]):
    """GeoJSON-геометрию → WKBElement(srid=4326) для asset.geometry (POLYGON).

    MultiPolygon приводим к крупнейшему полигону (колонка asset.geometry —
    POLYGON); полная геометрия остаётся в parcel.raw. Возвращает None, если
    геометрии нет/не распарсилась.
    """
    geo = _first(raw, GEOMETRY_KEYS)
    if not geo or shapely_shape is None:
        return None
    try:
        shp = shapely_shape(geo)
    except Exception:
        return None
    if shp.is_empty:
        return None
    if shp.geom_type == "MultiPolygon":
        shp = max(shp.geoms, key=lambda g: g.area)  # крупнейший контур
    if shp.geom_type != "Polygon":
        return None
    return from_shape(shp, srid=SOURCE_SRID)


def map_asset_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Поля для zn.asset. cad_number обязателен (иначе ValueError)."""
    cad = _first(raw, CAD_KEYS)
    if not cad:
        raise ValueError("В записи НСПД нет кадастрового номера — нечем идентифицировать asset")
    category = _first(raw, CATEGORY_KEYS)
    return {
        "cad_number": str(cad),
        "kind": "parcel",
        "address": _first(raw, ADDRESS_KEYS),
        "area": _to_float(_first(raw, AREA_KEYS)),
        "category": str(category) if category is not None else None,
        "owner_type": normalize_owner_type(_first(raw, OWNER_KEYS)),
        "status": "active",
        "geometry": _parse_geometry(raw),
    }


def map_parcel_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Поля для zn.parcel. Полный сырой ответ кладём в `raw` (ничего не теряем)."""
    category = _first(raw, CATEGORY_KEYS)
    return {
        "land_category": str(category) if category is not None else None,
        "permitted_use": _first(raw, PERMITTED_USE_KEYS),
        "zone_code": _first(raw, ZONE_KEYS),
        "cadastral_quarter": _first(raw, CAD_QUARTER_KEYS),
        "cadastral_value": _cad_value(raw),
        "raw": raw,
    }
