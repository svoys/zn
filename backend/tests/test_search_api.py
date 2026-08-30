"""Тесты для модуля search — GET /api/v1/search.

Требуют живой PostgreSQL + PostGIS. Фикстура db_ready переиспользуется из
test_asset_api.py — она создаёт таблицу zn.asset и чистит после.

Покрываем:
  - поиск без фильтров (все активы)
  - текстовый поиск (q)
  - фильтр по региону (region)
  - диапазон площади (area_min/area_max)
  - точное совпадение категории (category)
  - пагинация (limit/offset)
  - total считается корректно
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from tests.conftest import TestingSessionLocal as SessionLocal
from app.main import app
from app.modules.asset.models import Asset

client = TestClient(app)

# Кадастровые номера для тестовых данных (разные регионы/площади).
TEST_ASSETS = [
    {"cad_number": "50:01:010101:101", "address": "Москва, ул. Тверская", "area": 100.0, "category": "Земли населённых пунктов"},
    {"cad_number": "50:02:020202:202", "address": "Москва, ул. Арбат", "area": 200.0, "category": "Земли населённых пунктов"},
    {"cad_number": "12:34:567890:123", "address": "Одинцово, д. Раздоры", "area": 1500.0, "category": "Земли населённых пунктов"},
    {"cad_number": "66:01:010101:101", "address": "Екатеринбург, ул. Ленина", "area": 500.0, "category": "Земли промышленности"},
]


@pytest.fixture(scope="module")
def db_ready():
    """Заполняет asset тестовыми данными, чистит после.

    Схема создаётся один раз на сессию в conftest.py (`_full_schema`) —
    здесь мы только управляем СТРОКАМИ, не таблицами (см. docstring
    `_full_schema` про порядок-зависимость при create_all/drop_all по файлам).
    """
    with SessionLocal() as db:
        db.execute(text("DELETE FROM zn.asset"))
        db.commit()
        for asset_data in TEST_ASSETS:
            db.add(Asset(**asset_data, owner_type="private", status="active"))
        db.commit()

    yield

    with SessionLocal() as db:
        db.execute(text("DELETE FROM zn.asset"))
        db.commit()


class TestSearchNoFilters:
    """Поиск без фильтров — возвращает все активы."""

    def test_returns_all_active_assets(self, db_ready):
        response = client.get("/api/v1/search")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == len(TEST_ASSETS)
        assert len(body["items"]) == len(TEST_ASSETS)
        assert body["limit"] == 20
        assert body["offset"] == 0


class TestSearchTextQuery:
    """Текстовый поиск (q) — по address и cad_number."""

    def test_search_by_address_substring(self, db_ready):
        response = client.get("/api/v1/search", params={"q": "Тверская"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert "Тверская" in body["items"][0]["address"]

    def test_search_by_cad_number_substring(self, db_ready):
        response = client.get("/api/v1/search", params={"q": "567890"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["cad_number"] == "12:34:567890:123"

    def test_search_case_insensitive(self, db_ready):
        response = client.get("/api/v1/search", params={"q": "москва"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2  # Тверская + Арбат


class TestSearchRegion:
    """Фильтр по региону — первые 2 цифры cad_number."""

    def test_filter_by_region_50(self, db_ready):
        response = client.get("/api/v1/search", params={"region": "50"})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        for item in body["items"]:
            assert item["cad_number"].startswith("50:")


class TestSearchAreaRange:
    """Диапазон площади — area_min/area_max."""

    def test_filter_area_min(self, db_ready):
        response = client.get("/api/v1/search", params={"area_min": 300})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2  # 500 (Екб) + 1500 (Одинцово)
        for item in body["items"]:
            assert item["area"] >= 300

    def test_filter_area_max(self, db_ready):
        response = client.get("/api/v1/search", params={"area_max": 200})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2  # 100 + 200
        for item in body["items"]:
            assert item["area"] <= 200

    def test_filter_area_range(self, db_ready):
        response = client.get(
            "/api/v1/search", params={"area_min": 100, "area_max": 500}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3  # 100, 200, 500


class TestSearchCategory:
    """Точное совпадение категории."""

    def test_filter_by_category(self, db_ready):
        response = client.get(
            "/api/v1/search", params={"category": "Земли промышленности"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["category"] == "Земли промышленности"


class TestSearchPagination:
    """Пагинация limit/offset + total."""

    def test_limit_returns_subset(self, db_ready):
        response = client.get("/api/v1/search", params={"limit": 2})
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == len(TEST_ASSETS)  # total не зависит от limit
        assert len(body["items"]) == 2
        assert body["limit"] == 2

    def test_offset_skips_first(self, db_ready):
        response = client.get(
            "/api/v1/search", params={"limit": 2, "offset": 2}
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2  # 4 всего - 2 offset = 2
        assert body["offset"] == 2

    def test_limit_max_100_enforced(self, db_ready):
        # limit > 100 должен отбиваться FastAPI валидатором (422)
        response = client.get("/api/v1/search", params={"limit": 101})
        assert response.status_code == 422

    def test_limit_min_1_enforced(self, db_ready):
        response = client.get("/api/v1/search", params={"limit": 0})
        assert response.status_code == 422


class TestSearchCombined:
    """Комбинированные фильтры (AND)."""

    def test_region_plus_area_min(self, db_ready):
        response = client.get(
            "/api/v1/search", params={"region": "50", "area_min": 150}
        )
        assert response.status_code == 200
        body = response.json()
        # Регион 50: Тверская(100) + Арбат(200). area_min=150 → только Арбат.
        assert body["total"] == 1
        assert body["items"][0]["address"] == "Москва, ул. Арбат"
