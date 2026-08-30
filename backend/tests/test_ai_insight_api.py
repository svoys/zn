"""Тесты слоя AIInsight и его включения в Digital Twin.

Требуют живой PostgreSQL + PostGIS (изолированный TEST_DB_DSN из conftest).
Юнит-тест генератора работает без БД.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.modules.ai_insight.generator import generate
from app.modules.asset.models import Asset
from app.modules.opportunity.models import Opportunity
from app.modules.opportunity.scoring import compute_score
from app.modules.parcel.models import Parcel
from app.modules.restriction.models import Restriction
from tests.conftest import TestingSessionLocal as SessionLocal

client = TestClient(app)

CAD_CLEAN = "77:02:000202:1"
CAD_DIRTY = "77:02:000202:2"


@pytest.fixture(scope="module")
def db_ready():
    """Наполняет asset/parcel/restriction тестовыми данными, чистит после.

    Схема создаётся один раз на сессию в conftest.py (`_full_schema`) —
    здесь мы управляем только строками (см. docstring `_full_schema`).
    """
    with SessionLocal() as db:
        for t in ("event", "ai_insight", "opportunity", "restriction", "parcel", "asset"):
            db.execute(text(f"DELETE FROM zn.{t}"))
        db.commit()

        clean = Asset(cad_number=CAD_CLEAN, kind="parcel", status="active", area=1000.0)
        dirty = Asset(cad_number=CAD_DIRTY, kind="parcel", status="active", area=1000.0)
        db.add_all([clean, dirty])
        db.flush()
        db.add(Parcel(asset_id=clean.id, permitted_use="ИЖС", cadastral_value=5_000_000))
        db.add(Parcel(asset_id=dirty.id, permitted_use="ИЖС", cadastral_value=5_000_000))
        db.add(Restriction(asset_id=dirty.id, kind="zouit", title="Охранная зона ЛЭП", severity=90))
        db.commit()

    yield

    with SessionLocal() as db:
        for t in ("event", "ai_insight", "opportunity", "restriction", "parcel", "asset"):
            db.execute(text(f"DELETE FROM zn.{t}"))
        db.commit()


class TestGeneratorUnit:
    """Генератор не выдумывает числа — только объясняет посчитанные факторы."""

    def _make(self, restrictions):
        parcel = Parcel(permitted_use="ИЖС", cadastral_value=1)
        asset = Asset(cad_number="x")
        computed = compute_score(asset, parcel, restrictions)
        # Лёгкий «фейковый» ORM-объект Opportunity из посчитанного словаря.
        opp = Opportunity(
            asset_id=1, score=computed["score"], rating=computed["rating"],
            rationale=computed["rationale"], factors=computed["factors"],
            model_version=computed["model_version"],
        )
        return asset, parcel, opp

    def test_generate_returns_swot_and_explanation(self):
        asset, parcel, opp = self._make([])
        out = generate(asset, parcel, [], opp)
        kinds = {i["kind"] for i in out}
        assert kinds == {"swot", "explanation"}
        for i in out:
            assert i["model_version"] == "insight-v1"
            assert "based_on" in i["trace"]
            # число в trace взято из скоринга, не выдумано генератором.
            assert i["trace"]["based_on"]["score"] == opp.score

    def test_restriction_becomes_threat(self):
        r = Restriction(kind="zouit", title="Охранная зона ЛЭП", severity=90)
        asset, parcel, opp = self._make([r])
        swot = next(i for i in generate(asset, parcel, [r], opp) if i["kind"] == "swot")
        assert any("Охранная зона ЛЭП" in t for t in swot["content"]["threats"])

    def test_explanation_breakdown_matches_factors(self):
        asset, parcel, opp = self._make([])
        expl = next(i for i in generate(asset, parcel, [], opp) if i["kind"] == "explanation")
        assert len(expl["content"]["breakdown"]) == len(opp.factors)


class TestRegenerateEndpoint:
    def test_regenerate_creates_current_insights(self, db_ready):
        r = client.post(f"/api/v1/asset/{CAD_DIRTY}/insights/regenerate")
        assert r.status_code == 201
        body = r.json()
        assert {i["kind"] for i in body} == {"swot", "explanation"}

    def test_regenerate_autocomputes_opportunity(self, db_ready):
        # У CAD_CLEAN скоринга ещё нет — regenerate должен посчитать его сам.
        client.post(f"/api/v1/asset/{CAD_CLEAN}/insights/regenerate")
        twin = client.get(f"/api/v1/asset/{CAD_CLEAN}/twin").json()
        assert twin["opportunity"] is not None
        assert len(twin["insights"]) == 2

    def test_regenerate_supersedes_previous_per_kind(self, db_ready):
        client.post(f"/api/v1/asset/{CAD_DIRTY}/insights/regenerate")
        client.post(f"/api/v1/asset/{CAD_DIRTY}/insights/regenerate")
        with SessionLocal() as db:
            aid = db.execute(
                text("SELECT id FROM zn.asset WHERE cad_number=:c"), {"c": CAD_DIRTY}
            ).scalar_one()
            n_current = db.execute(
                text("SELECT count(*) FROM zn.ai_insight WHERE asset_id=:a AND is_current"),
                {"a": aid},
            ).scalar_one()
        # ровно по одному текущему на категорию (swot + explanation)
        assert n_current == 2

    def test_regenerate_404_for_missing(self, db_ready):
        r = client.post("/api/v1/asset/88:88:888888:888/insights/regenerate")
        assert r.status_code == 404


class TestTwinIncludesInsights:
    def test_twin_exposes_insights(self, db_ready):
        client.post(f"/api/v1/asset/{CAD_DIRTY}/insights/regenerate")
        twin = client.get(f"/api/v1/asset/{CAD_DIRTY}/twin").json()
        assert {i["kind"] for i in twin["insights"]} == {"swot", "explanation"}
        swot = next(i for i in twin["insights"] if i["kind"] == "swot")
        assert "threats" in swot["content"]


class TestTwinIncludesEvents:
    def test_twin_exposes_recent_events(self, db_ready):
        with SessionLocal() as db:
            aid = db.execute(
                text("SELECT id FROM zn.asset WHERE cad_number=:c"), {"c": CAD_DIRTY}
            ).scalar_one()
            db.execute(
                text(
                    "INSERT INTO zn.event (asset_id, type, payload) "
                    "VALUES (:a, 'cad_value_changed', '{\"old\": 1, \"new\": 2}')"
                ),
                {"a": aid},
            )
            db.commit()
        twin = client.get(f"/api/v1/asset/{CAD_DIRTY}/twin").json()
        assert any(e["type"] == "cad_value_changed" for e in twin["recent_events"])
