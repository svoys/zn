"""Клиент НСПД (Национальная система пространственных данных).

⚠️ СКЕЛЕТ ПО ПРЕДПОЛОЖЕНИЯМ. Реальный API НСПД (endpoint, авторизация, формат
ответа) на момент написания не подключён. Весь сетевой ввод-вывод изолирован в
одном методе `_request()` — когда появится доступ, реализуется только он
(рекомендуется httpx с таймаутом и ретраями), остальной пайплайн (mapper/service)
не меняется.

Для разработки и тестов есть офлайн-режим `NspdClient.from_fixture(path)` — читает
заранее сохранённые ответы из JSON-файла, не выходя в сеть.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Предполагаемая система координат геометрии в ответе НСПД. Если реальный
# источник отдаёт не 4326 (например, Web Mercator 3857 или региональную МСК),
# здесь понадобится репроекция в mapper — см. mapper.SOURCE_SRID.
DEFAULT_BASE_URL = "https://nspd.gov.ru/api/geoportal/v1"  # ПРЕДПОЛОЖЕНИЕ
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "zn-etl/0.1 (+https://z-n.ru)"


class NspdClient:
    """Достаёт «сырые» записи участков из НСПД.

    Два режима:
      • сетевой  — `NspdClient(base_url=..., api_key=...)` (метод `_request` пока
                   не реализован → NotImplementedError с понятным сообщением);
      • офлайн   — `NspdClient.from_fixture(path)` для dev/тестов.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        _fixture: dict[str, Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        # _fixture: {"by_cad": {cad: raw}, "by_region": {region: [raw, ...]}}
        self._fixture = _fixture

    # ─── Публичный API ────────────────────────────────────────────────
    @classmethod
    def from_fixture(cls, path: str | Path) -> "NspdClient":
        """Офлайн-клиент, читающий ответы из JSON-фикстуры."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(_fixture=data)

    def fetch_by_cad(self, cad_number: str) -> dict[str, Any] | None:
        """Одна запись участка по кадастровому номеру (или None, если нет)."""
        if self._fixture is not None:
            return self._fixture.get("by_cad", {}).get(cad_number)
        return self._request("GET", f"/parcel/{cad_number}")

    def fetch_region(self, region_code: str, limit: int = 100) -> list[dict[str, Any]]:
        """Список участков по коду региона (первые `limit`)."""
        if self._fixture is not None:
            items = self._fixture.get("by_region", {}).get(region_code, [])
            return list(items)[:limit]
        data = self._request("GET", f"/region/{region_code}/parcels", params={"limit": limit})
        return data.get("items", []) if isinstance(data, dict) else list(data)

    # ─── Шов под реальную сеть ────────────────────────────────────────
    def _request(self, method: str, path: str, params: dict | None = None) -> Any:
        """ЕДИНСТВЕННАЯ точка сетевого ввода-вывода.

        Реализовать при подключении реального НСПД. Ориентир:

            import httpx
            headers = {"User-Agent": USER_AGENT}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as c:
                r = c.request(method, path, params=params, headers=headers)
                r.raise_for_status()
                return r.json()
        """
        raise NotImplementedError(
            "Сетевой режим НСПД не подключён. Реализуйте NspdClient._request "
            "(httpx) под реальный API, либо используйте NspdClient.from_fixture(path) "
            "для офлайн-ингеста."
        )
