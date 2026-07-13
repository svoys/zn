"""Search CRUD — построение запроса с фильтрами и пагинацией.

Фильтры комбинируются через AND. `q` ищет по address и cad_number через ILIKE.
`region` — первые 2 цифры cad_number (напр. "50" → Московская обл.).
Пагинация — классическая offset/limit; total считается отдельным запросом.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.asset.models import Asset


def search_assets(
    db: Session,
    *,
    q: str | None = None,
    region: str | None = None,
    area_min: float | None = None,
    area_max: float | None = None,
    category: str | None = None,
    status: str = "active",
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Asset], int]:
    """Возвращает (items, total) под переданные фильтры.

    Items — список ORM-объектов Asset; total — общее число подходящих записей
    (без учёта пагинации).
    """
    stmt = select(Asset)

    # Текстовый поиск: по адресу и кадастровому номеру.
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Asset.address.ilike(pattern),
                Asset.cad_number.ilike(pattern),
            )
        )

    # Регион: префикс кадастрового номера (первые 2 цифры).
    if region:
        stmt = stmt.where(Asset.cad_number.like(f"{region}:%"))

    # Диапазон площади.
    if area_min is not None:
        stmt = stmt.where(Asset.area >= area_min)
    if area_max is not None:
        stmt = stmt.where(Asset.area <= area_max)

    # Точное совпадение категории.
    if category:
        stmt = stmt.where(Asset.category == category)

    # Статус: по умолчанию active.
    if status:
        stmt = stmt.where(Asset.status == status)

    # Total — отдельный запрос COUNT(*). Дешевле, чем window-function на больших выборках.
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar_one()

    # Пагинация. ORDER BY для детерминизма (иначе offset скачет между запросами).
    stmt = stmt.order_by(Asset.id).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars().all())

    return items, total
