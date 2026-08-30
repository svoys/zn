"""Opportunity Score — прозрачная взвешенная модель (MVP).

Принципиально НЕ «чёрный ящик»: score = Σ(weight × normalized_value), каждый
фактор сохраняется с вкладом и источником. LLM на следующей вехе будет писать
только текстовый rationale поверх этих факторов, а не выдумывать цифры.
См. docs/digital-twin-design.md §5.
"""

from __future__ import annotations

from app.modules.asset.models import Asset
from app.modules.parcel.models import Parcel
from app.modules.restriction.models import Restriction

MODEL_VERSION = "score-v1"

# Веса факторов (в сумме = 1.0). Меняются с версией модели.
WEIGHTS = {
    "legal_cleanliness": 0.5,
    "use_clarity": 0.3,
    "economics": 0.2,
}


def _rating(score: int) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def compute_score(
    asset: Asset,
    parcel: Parcel | None,
    restrictions: list[Restriction],
) -> dict:
    """Возвращает dict с полями score/rating/rationale/factors/model_version.

    Детерминированно, без обращений к внешним сервисам.
    """
    # 1) Правовая чистота: чем тяжелее максимальное ограничение, тем ниже.
    max_severity = max(
        (r.severity for r in restrictions if r.severity is not None),
        default=0,
    )
    legal_value = 1.0 - min(max_severity, 100) / 100.0

    # 2) Определённость использования: задан ли ВРИ.
    use_value = 1.0 if (parcel and parcel.permitted_use) else 0.0

    # 3) Экономика: известна ли кадастровая стоимость (proxy на оцениваемость).
    econ_value = 1.0 if (parcel and parcel.cadastral_value is not None) else 0.0

    raw_factors = [
        ("legal_cleanliness", legal_value,
         f"restrictions (max severity={max_severity})"),
        ("use_clarity", use_value, "parcel.permitted_use"),
        ("economics", econ_value, "parcel.cadastral_value"),
    ]

    factors = []
    total = 0.0
    for name, value, source in raw_factors:
        weight = WEIGHTS[name]
        contribution = round(weight * value * 100, 1)
        total += weight * value
        factors.append({
            "factor": name,
            "weight": weight,
            "value": round(value, 3),
            "contribution": contribution,
            "source": source,
        })

    score = round(total * 100)
    rating = _rating(score)

    # Черновой rationale (позже заменит LLM). Опираемся на факторы, не на догадки.
    strongest = max(factors, key=lambda f: f["contribution"])
    weakest = min(factors, key=lambda f: f["contribution"])
    rationale = (
        f"Оценка {score}/100 (рейтинг {rating}). "
        f"Сильнее всего вклад даёт «{strongest['factor']}» ({strongest['contribution']}), "
        f"слабее всего — «{weakest['factor']}» ({weakest['contribution']}). "
        f"Требует проверки специалистом."
    )

    return {
        "score": score,
        "rating": rating,
        "rationale": rationale,
        "factors": factors,
        "model_version": MODEL_VERSION,
    }
