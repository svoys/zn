"""Тесты слоя Restriction + Opportunity и обновлённого Digital Twin.

Требуют живой PostgreSQL + PostGIS. Изолированный тестовый engine (TEST_DB_DSN)
берётся из conftest — dev-база не затрагивается.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.modules.asset.models import Asset
from app.modules.opportunity.scoring import compute_score
from app.modules.parcel.models import Parcel
from app.modules.restriction.models import Restriction
from tests.conftest import TestingSessionLocal as SessionLocal

client = TestClient(app)

CAD_CLEAN = "77:01:000101:1"   # чистый участок с ВРИ и кад. стоимостью
CAD_DIRTY = "77:01:000101:2"   # с тяжёлым ограничением


@pytest.fixture(scope="module")
def db_ready():
    """Наполняет asset/parcel/restriction тестовыми данными, чистит после.

    Схема создаётся один раз на сессию в conftest.py (`_full_schema`) —
    здесь мы управляем только строками (см. docstring `_full_schema`).
    """
    with SessionLocal() as db:
        for t in ("event", "opportunity", "restriction", "parcel", "asset"):
            db.execute(text(f"DELETE FROM zn.{t}"))
        db.commit()

        clean = Asset(cad_number=CAD_CLEAN, kind="parcel", status="active", area=1000.0)
        dirty = Asset(cad_number=CAD_DIRTY, kind="parcel", status="active", area=1000.0)
        db.add_all([clean, dirty])
        db.flush()

        db.add(Parcel(asset_id=clean.id, permitted_use="ИЖС", cadastral_value=5_000_000))
        db.add(Parcel(asset_id=dirty.id, permitted_use="ИЖС", cadastral_value=5_000_000))
        # У «грязного» участка тяжёлое ограничение (severity=90).
        db.add(Restriction(asset_id=dirty.id, kind="zouit", title="Охранная зона ЛЭП", severity=90))
        db.commit()

    yield

    with SessionLocal() as db:
        for t in ("event", "opportunity", "restriction", "parcel", "asset"):
            db.execute(text(f"DELETE FROM zn.{t}"))
        db.commit()


class TestScoringUnit:
    """Юнит-тест чистой функции скоринга (без БД, без HTTP)."""

    def test_clean_scores_higher_than_dirty(self):
        clean = compute_score(Asset(cad_number=CAD_CLEAN),
                              Parcel(permitted_use="ИЖС", cadastral_value=1),
                              restrictions=[])
        dirty = compute_score(Asset(cad_number=CAD_DIRTY),
                              Parcel(permitted_use="ИЖС", cadastral_value=1),
                              restrictions=[Restriction(kind="zouit", title="x", severity=90)])
        assert clean["score"] > dirty["score"]
        assert 0 <= dirty["score"] <= 100
        assert clean["rating"] in {"A", "B", "C", "D"}
        # factors всегда с указанием источника (explainability).
        assert all("source" in f for f in clean["factors"])
        assert sum(f["weight"] for f in clean["factors"]) == pytest.approx(1.0)


class TestRecomputeEndpoint:
    def test_recompute_creates_current_version(self, db_ready):
        r = client.post(f"/api/v1/asset/{CAD_CLEAN}/opportunity/recompute")
        assert r.status_code == 201
        body = r.json()
        assert 0 <= body["score"] <= 100
        assert body["model_version"] == "score-v1"
        assert body["factors"] and all("contribution" in f for f in body["factors"])

    def test_recompute_supersedes_previous(self, db_ready):
        client.post(f"/api/v1/asset/{CAD_CLEAN}/opportunity/recompute")
        client.post(f"/api/v1/asset/{CAD_CLEAN}/opportunity/recompute")
        # Должна остаться ровно одна текущая версия (partial unique + логика CRUD).
        with SessionLocal() as db:
            aid = db.execute(
                text("SELECT id FROM zn.asset WHERE cad_number=:c"), {"c": CAD_CLEAN}
            ).scalar_one()
            current = db.execute(
                text("SELECT count(*) FROM zn.opportunity WHERE asset_id=:a AND is_current"),
                {"a": aid},
            ).scalar_one()
        assert current == 1

    def test_recompute_404_for_missing(self, db_ready):
        r = client.post("/api/v1/asset/99:99:999999:999/opportunity/recompute")
        assert r.status_code == 404


class TestTwinIncludesLayers:
    def test_twin_has_restrictions_and_opportunity(self, db_ready):
        client.post(f"/api/v1/asset/{CAD_DIRTY}/opportunity/recompute")
        r = client.get(f"/api/v1/asset/{CAD_DIRTY}/twin")
        assert r.status_code == 200
        body = r.json()
        assert len(body["restrictions"]) == 1
        assert body["restrictions"][0]["severity"] == 90
        assert body["opportunity"] is not None
        assert body["opportunity"]["rating"] in {"A", "B", "C", "D"}
