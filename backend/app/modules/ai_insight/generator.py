"""Генерация AIInsight поверх УЖЕ посчитанных данных.

Ключевой принцип продукта: инсайт объясняет, но не выдумывает. Все числа берутся
из `opportunity.factors` и `restriction.severity`; текст лишь интерпретирует их.
Здесь реализован детерминированный генератор (fallback). Точка расширения под LLM —
`_llm_narrative()`: когда появится доступ к модели, она перепишет ТОЛЬКО
человекочитаемый текст поверх тех же фактов, а `trace` зафиксирует источник.

См. docs/digital-twin-design.md §2.4, §5.
"""

from __future__ import annotations

from typing import Any

MODEL_VERSION = "insight-v1"

# Человекочитаемые ярлыки факторов скоринга.
FACTOR_LABELS = {
    "legal_cleanliness": "правовая чистота",
    "use_clarity": "определённость разрешённого использования",
    "economics": "экономическая оцениваемость",
}

_STRONG = 0.7   # порог «сильная сторона»
_WEAK = 0.3     # порог «слабая сторона»


def _label(factor: str) -> str:
    return FACTOR_LABELS.get(factor, factor)


def _llm_narrative(kind: str, facts: dict[str, Any]) -> dict | None:
    """Место под LLM-генерацию текста поверх `facts`.

    Возвращает None, если модель недоступна (тогда используется детерминированный
    fallback). LLM НЕ получает права придумывать числа — только формулировать
    выводы по переданным фактам. Пока не подключено → None.
    """
    return None


def _swot(factors: list[dict], restrictions: list) -> dict:
    strengths, weaknesses, opportunities, threats = [], [], [], []

    for f in factors:
        label = _label(f["factor"])
        value = f.get("value", 0.0)
        if value >= _STRONG:
            strengths.append(f"Высокая {label} (вклад {f['contribution']} из 100).")
        elif value <= _WEAK:
            weaknesses.append(
                f"Низкая {label} — фактор почти не даёт вклада ({f['contribution']})."
            )

    # Ограничения → угрозы, по убыванию тяжести.
    for r in sorted(
        restrictions, key=lambda r: (r.severity or 0), reverse=True
    ):
        sev = r.severity if r.severity is not None else "н/д"
        threats.append(f"{r.title} (тип: {r.kind}, тяжесть: {sev}).")

    # Возможности выводим из сочетания сильных сторон (без новых чисел).
    strong_factors = {f["factor"] for f in factors if f.get("value", 0.0) >= _STRONG}
    if {"legal_cleanliness", "use_clarity"} <= strong_factors:
        opportunities.append(
            "Чистый правовой статус при заданном ВРИ — участок пригоден к быстрому вводу в оборот."
        )
    if "economics" in strong_factors:
        opportunities.append(
            "Известна кадастровая стоимость — возможна предварительная оценка сделки."
        )
    if not threats and not weaknesses:
        opportunities.append("Существенных ограничений не выявлено — низкий правовой риск.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }


def _explanation(opportunity) -> dict:
    factors = opportunity.factors or []
    ordered = sorted(factors, key=lambda f: f.get("contribution", 0), reverse=True)
    breakdown = [
        {
            "factor": _label(f["factor"]),
            "contribution": f.get("contribution"),
            "source": f.get("source"),
        }
        for f in ordered
    ]
    summary = (
        f"Итоговая оценка {opportunity.score}/100 (рейтинг {opportunity.rating}). "
        "Складывается из взвешенных факторов, каждый из которых посчитан из данных "
        "участка, а не задан вручную."
    )
    return {"summary": summary, "breakdown": breakdown}


def generate(asset, parcel, restrictions: list, opportunity) -> list[dict]:
    """Строит набор актуальных инсайтов (swot + explanation) по текущим данным.

    `opportunity` — ORM-объект текущей версии Opportunity (обязателен: инсайт
    объясняет именно её). Возвращает список dict'ов, готовых для crud.save_new_version.
    """
    factors = opportunity.factors or []
    base_trace = {
        "generator": "deterministic",
        "based_on": {
            "opportunity_model_version": opportunity.model_version,
            "score": opportunity.score,
            "rating": opportunity.rating,
        },
        "sources": sorted({f.get("source") for f in factors if f.get("source")}),
        "restriction_count": len(restrictions),
    }

    insights: list[dict] = []

    # 1) SWOT
    swot_facts = {"factors": factors, "restrictions_titles": [r.title for r in restrictions]}
    swot_content = _llm_narrative("swot", swot_facts) or _swot(factors, restrictions)
    insights.append({
        "kind": "swot",
        "content": swot_content,
        "trace": base_trace,
        "model_version": MODEL_VERSION,
    })

    # 2) Explanation скоринга
    expl_content = _llm_narrative("explanation", {"opportunity": opportunity.score}) \
        or _explanation(opportunity)
    insights.append({
        "kind": "explanation",
        "content": expl_content,
        "trace": base_trace,
        "model_version": MODEL_VERSION,
    })

    return insights
