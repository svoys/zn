"""Тесты ETL-коннектора НСПД (mapper / client / service).

Юнит-тесты маппера и клиента работают без БД. Интеграционные (ингест) требуют
живой PostgreSQL + PostGIS (изолированный TEST_DB_DSN из conftest).
Данные берутся из офлайн-фикстуры tests/fixtures/nspd_sample.json — сети не нужно.
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.etl.nspd import mapper, service
from app.etl.nspd.client import NspdClient
from app.modules.asset.models import Asset
from app.modules.parcel.models import Parcel
from tests.conftest import TestingSessionLocal as SessionLocal

FIXTURE = Path(__file__).parent / "fixtures" / "nspd_sample.json"
CAD1 = "77:01:000101:1"
CAD2 = "77:01:000101:2"


@pytest.fixture(scope="module")
def raws():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data["by_cad"][CAD1], data["by_cad"][CAD2]


# ─────────────────────────── MAPPER (без БД) ───────────────────────────
class TestMapper:
    def test_canonical_keys(self, raws):
        rec1, _ = raws
        a = mapper.map_asset_fields(rec1)
        assert a["cad_number"] == CAD1
        assert a["area"] == 1500.5
        assert a["owner_type"] == "private"
        assert a["category"] == "Земли населённых пунктов"
        assert a["geometry"] is not None  # WKBElement
        assert getattr(a["geometry"], "srid", None) == 4326

    def test_alternate_keys_and_missing_owner(self, raws):
        _, rec2 = raws
        a = mapper.map_asset_fields(rec2)
        assert a["cad_number"] == CAD2       # взято из "cn"
        assert a["area"] == 800.0            # из "area"
        assert a["owner_type"] is None       # формы собственности в записи нет
        assert a["geometry"] is not None     # MultiPolygon → крупнейший контур

    def test_parcel_fields_and_cost_unwrapping(self, raws):
        rec1, rec2 = raws
        p1 = mapper.map_parcel_fields(rec1)
        p2 = mapper.map_parcel_fields(rec2)
        assert p1["cadastral_value"] == 5250000        # из {"value": ...}
        assert p2["cadastral_value"] == 3100000        # из плоского числа
        assert p1["permitted_use"].startswith("Для индивидуального")
        assert p2["permitted_use"].startswith("Для размещения")
        assert p1["raw"] == rec1                        # сырой ответ сохранён целиком

    def test_missing_cad_raises(self):
        with pytest.raises(ValueError):
            mapper.map_asset_fields({"address": "нет кад. номера"})

    @pytest.mark.parametrize("value,expected", [
        ("Частная собственность", "private"),
        ("Государственная собственность", "state"),
        ("Муниципальная собственность", "municipal"),
        ({"type": "Федеральная собственность"}, "state"),
        ("что-то неведомое", "unknown"),
        (None, None),
    ])
    def test_normalize_owner_type(self, value, expected):
        assert mapper.normalize_owner_type(value) == expected


# ─────────────────────────── CLIENT ───────────────────────────
class TestClient:
    def test_fixture_mode(self):
        client = NspdClient.from_fixture(FIXTURE)
        assert client.fetch_by_cad(CAD1)["cadastral_number"] == CAD1
        assert client.fetch_by_cad("00:00:000000:0") is None
        region = client.fetch_region("77")
        assert len(region) == 2

    def test_network_mode_not_implemented(self):
        with pytest.raises(NotImplementedError):
            NspdClient().fetch_by_cad(CAD1)


# ─────────────────────────── SERVICE (с БД) ───────────────────────────
@pytest.fixture(scope="function")
def db_ready():
    """Чистит asset/parcel/event перед и после КАЖДОГО теста.

    Раньше фикстура была `scope="module"` и чистила данные только один раз
    на весь файл — TestService/TestEventEmission используют один и тот же
    CAD1 в нескольких тестах, поэтому `test_ingest_creates_asset_and_parcel`
    вставлял CAD1, а следующий тест `test_ingest_is_idempotent` находил его
    уже существующим и получал `created=False` на "первом" ингесте, где
    ожидалось `True` — то есть тесты проходили/падали в зависимости от того,
    в каком порядке и составе они выполнялись, а не от корректности кода.
    `scope="function"` даёт каждому тесту чистое состояние.

    Схема (таблицы) создаётся один раз на сессию в conftest.py
    (`_full_schema`) — здесь мы управляем только строками.
    """
    with SessionLocal() as db:
        for t in ("event", "parcel", "asset"):
            db.execute(text(f"DELETE FROM zn.{t}"))
        db.commit()
    yield
    with SessionLocal() as db:
        for t in ("event", "parcel", "asset"):
            db.execute(text(f"DELETE FROM zn.{t}"))
        db.commit()


def _count(db, table: str) -> int:
    return db.execute(text(f"SELECT count(*) FROM zn.{table}")).scalar_one()


class TestService:
    def test_ingest_creates_asset_and_parcel(self, db_ready, raws):
        rec1, _ = raws
        with SessionLocal() as db:
            res = service.ingest_one(db, rec1)
            db.commit()
            assert res.created is True
            asset = db.query(Asset).filter(Asset.cad_number == CAD1).one()
            parcel = db.get(Parcel, asset.id)
            assert parcel is not None
            assert parcel.cadastral_value == 5250000
            assert asset.geometry is not None

    def test_ingest_is_idempotent(self, db_ready, raws):
        rec1, _ = raws
        with SessionLocal() as db:
            r1 = service.ingest_one(db, rec1)
            db.commit()
            r2 = service.ingest_one(db, dict(rec1, area_value=1600.0))
            db.commit()
            assert r1.created is True
            assert r2.created is False                 # обновление, не дубль
            assert _count(db, "asset") == 1
            asset = db.query(Asset).filter(Asset.cad_number == CAD1).one()
            assert asset.area == 1600.0                # поле обновилось

    def test_ingest_many_via_client_fixture(self, db_ready):
        client = NspdClient.from_fixture(FIXTURE)
        raws_region = client.fetch_region("77")
        with SessionLocal() as db:
            summary = service.ingest_many(db, raws_region)
            db.commit()
            assert summary.created + summary.updated == 2
            assert summary.failed == 0
            assert _count(db, "asset") == 2
            assert _count(db, "parcel") == 2


# ─────────────────────────── EVENTS (ETL change detection, с БД) ───────────────────────────
def _events(db, asset_id: int, type_: str | None = None) -> int:
    sql = "SELECT count(*) FROM zn.event WHERE asset_id=:a"
    params = {"a": asset_id}
    if type_ is not None:
        sql += " AND type=:t"
        params["t"] = type_
    return db.execute(text(sql), params).scalar_one()


class TestEventEmission:
    def test_create_emits_ingested(self, db_ready, raws):
        rec1, _ = raws
        with SessionLocal() as db:
            res = service.ingest_one(db, rec1)
            db.commit()
            assert "ingested" in res.events
            assert _events(db, res.asset_id, "ingested") == 1

    def test_changed_cad_value_emits_event(self, db_ready, raws):
        rec1, _ = raws
        with SessionLocal() as db:
            res = service.ingest_one(db, rec1)          # create
            db.commit()
            aid = res.asset_id
            # повторный ингест с изменённой кад. стоимостью
            changed = dict(rec1, cadastral_cost={"value": 9999999, "unit": "руб"})
            res2 = service.ingest_one(db, changed)
            db.commit()
            assert res2.created is False
            assert "cad_value_changed" in res2.events
            assert _events(db, aid, "cad_value_changed") == 1
            row = db.execute(
                text("SELECT payload FROM zn.event WHERE asset_id=:a AND type='cad_value_changed'"),
                {"a": aid},
            ).scalar_one()
            assert row["old"] == 5250000 and row["new"] == 9999999

    def test_unchanged_reingest_emits_no_change_events(self, db_ready, raws):
        rec1, _ = raws
        with SessionLocal() as db:
            res = service.ingest_one(db, rec1)
            db.commit()
            aid = res.asset_id
            res2 = service.ingest_one(db, rec1)          # тот же ответ
            db.commit()
            assert res2.events == []                      # ничего не поменялось
            assert _events(db, aid, "cad_value_changed") == 0
            assert _events(db, aid, "permitted_use_changed") == 0
