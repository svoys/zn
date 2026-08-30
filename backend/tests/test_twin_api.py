"""Тесты Digital Twin endpoint — GET /api/v1/asset/{cad_number}/twin.

Требуют живой PostgreSQL + PostGIS. Используют изолированный тестовый engine
из conftest (TEST_DB_DSN) — dev-база не затрагивается.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.modules.asset.models import Asset
from app.modules.parcel.models import Parcel
from tests.conftest import TestingSessionLocal as SessionLocal

client = TestClient(app)

CAD = "50:10:010203:44"


@pytest.fixture(scope="module")
def db_ready():
    """Наполняет asset+parcel одним участком, чистит после.

    Схема создаётся один раз на сессию в conftest.py (`_full_schema`) —
    здесь мы управляем только строками (см. docstring `_full_schema`).
    """
    with SessionLocal() as db:
        db.execute(text("DELETE FROM zn.parcel"))
        db.execute(text("DELETE FROM zn.asset"))
        db.commit()
        asset = Asset(
            cad_number=CAD,
            kind="parcel",
            address="Московская обл., Ленинский р-н",
            area=2500.0,
            category="Земли населённых пунктов",
            owner_type="private",
            status="active",
        )
        db.add(asset)
        db.flush()
        db.add(
            Parcel(
                asset_id=asset.id,
                land_category="Земли населённых пунктов",
                permitted_use="ИЖС",
                zone_code="Ж-1",
                cadastral_quarter="50:10:010203",
                cadastral_value=3_200_000.00,
            )
        )
        db.commit()

    yield

    with SessionLocal() as db:
        db.execute(text("DELETE FROM zn.parcel"))
        db.execute(text("DELETE FROM zn.asset"))
        db.commit()


class TestTwinEndpoint:
    def test_twin_returns_asset_and_parcel(self, db_ready):
        response = client.get(f"/api/v1/asset/{CAD}/twin")
        assert response.status_code == 200
        body = response.json()
        assert body["asset"]["cad_number"] == CAD
        assert body["asset"]["kind"] == "parcel"
        assert body["parcel"] is not None
        assert body["parcel"]["zone_code"] == "Ж-1"
        assert body["parcel"]["permitted_use"] == "ИЖС"
        assert body["parcel"]["cadastral_value"] == 3_200_000.00

    def test_twin_404_for_missing_asset(self, db_ready):
        response = client.get("/api/v1/asset/99:99:999999:999/twin")
        assert response.status_code == 404

    def test_twin_422_for_bad_cad_number(self):
        response = client.get("/api/v1/asset/not-a-cad/twin")
        assert response.status_code == 422
