"""Тесты для Asset endpoint GET /api/v1/asset/{cad_number}.

Два слоя:
  - TestCadNumberValidation — проверяет валидацию path-параметра (422).
    Эти тесты НЕ требуют БД: FastAPI отбивает некорректный cad_number до хендлера.
  - TestAssetEndpoint — проверяет бизнес-логику (200/404). Требует PostgreSQL+PostGIS.
    Если БД недоступна — тесты падают с ошибкой подключения.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.conftest import TestingSessionLocal as SessionLocal
from app.main import app
from app.modules.asset.models import Asset
from app.modules.asset.schemas import CAD_NUMBER_PATTERN

client = TestClient(app)

VALID_CAD_NUMBER = "12:34:567890:123"


@pytest.fixture(scope="module")
def db_ready():
    """Отмечает, что тесту нужна БД.

    Схема (все таблицы) создаётся один раз на сессию в conftest.py
    (`_full_schema`), поэтому здесь мы её не создаём и не удаляем —
    иначе порядок выполнения тестовых файлов начинает влиять на
    результат (см. docstring `_full_schema` в conftest.py).
    Применяется только к классам, которым нужна БД (TestAssetEndpoint).
    Валидационные тесты запускаются без БД.
    """
    yield


def _insert_asset(cad_number: str, **overrides) -> None:
    """Вспомогательная функция: вставляет актив в БД."""
    with SessionLocal() as db:
        db.execute(
            text("DELETE FROM zn.asset WHERE cad_number = :cn"),
            {"cn": cad_number},
        )
        db.commit()

        asset = Asset(
            cad_number=cad_number,
            address=overrides.get("address", "Московская обл., Одинцовский р-н"),
            area=overrides.get("area", 1500.00),
            category=overrides.get("category", "Земли населённых пунктов"),
            owner_type=overrides.get("owner_type", "private"),
            status=overrides.get("status", "active"),
        )
        db.add(asset)
        db.commit()


class TestAssetEndpoint:
    """Этап 6: GET /api/v1/asset/{cad_number} — бизнес-логика (требует БД)."""

    def test_get_existing_asset(self, db_ready):
        _insert_asset(VALID_CAD_NUMBER)
        response = client.get(f"/api/v1/asset/{VALID_CAD_NUMBER}")
        assert response.status_code == 200
        body = response.json()
        assert body["cad_number"] == VALID_CAD_NUMBER
        assert body["status"] == "active"
        assert body["area"] == 1500.00
        assert "created_at" in body
        assert "updated_at" in body

    def test_get_nonexistent_asset_returns_404(self, db_ready):
        response = client.get("/api/v1/asset/99:99:999999:999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Asset not found"


class TestAssetGeometry:
    """Проверка, что geometry отдаётся как GeoJSON Polygon.

    Вставляем актив с полигоном через ST_GeomFromGeoJSON и проверяем,
    что в ответе API геометрия представлена как GeoJSON-совместимый dict.
    """

    POLYGON_GEOJSON = {
        "type": "Polygon",
        "coordinates": [
            [[37.0, 55.0], [37.1, 55.0], [37.1, 55.1], [37.0, 55.1], [37.0, 55.0]]
        ],
    }

    def test_geometry_returned_as_geojson(self, db_ready):
        # Вставляем актив с полигоном через SQL (ST_GeomFromGeoJSON).
        with SessionLocal() as db:
            db.execute(
                text("DELETE FROM zn.asset WHERE cad_number = :cn"),
                {"cn": "77:77:777777:777"},
            )
            db.execute(
                text(
                    "INSERT INTO zn.asset (cad_number, address, area, status, geometry) "
                    "VALUES (:cn, :addr, :area, 'active', ST_GeomFromGeoJSON(:geo))"
                ),
                {
                    "cn": "77:77:777777:777",
                    "addr": "Тестовый полигон",
                    "area": 100.0,
                    "geo": json.dumps(self.POLYGON_GEOJSON),
                },
            )
            db.commit()

        response = client.get("/api/v1/asset/77:77:777777:777")
        assert response.status_code == 200
        body = response.json()
        assert body["geometry"] is not None
        assert body["geometry"]["type"] == "Polygon"
        # Polygon coordinates — массив колец; первое кольцо содержит 5 точек
        # (замкнутый полигон: первая == последняя).
        assert len(body["geometry"]["coordinates"][0]) == 5


class TestCadNumberValidation:
    """422 для некорректных кадастровых номеров — валидация на уровне FastAPI.

    Эти тесты не касаются БД: некорректный cad_number отбивается path-валидатором
    до того, как хендлер откроет сессию.
    """

    @pytest.mark.parametrize(
        "bad_cad_number",
        [
            "invalid",          # не похоже на кадастровый
            "1234567890",       # без разделителей
            "12-34-567890-123", # неверный разделитель
            "1:2:3:4",          # слишком короткие группы
        ],
    )
    def test_invalid_cad_number_returns_422(self, bad_cad_number: str):
        response = client.get(f"/api/v1/asset/{bad_cad_number}")
        assert response.status_code == 422

