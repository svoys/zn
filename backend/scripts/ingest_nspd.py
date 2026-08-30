#!/usr/bin/env python3
"""CLI-ингест участков из НСПД в zn.asset + zn.parcel.

Примеры:
  # офлайн из фикстуры (реальных данных пока нет):
  python scripts/ingest_nspd.py --fixture tests/fixtures/nspd_sample.json --region 77
  python scripts/ingest_nspd.py --fixture tests/fixtures/nspd_sample.json --cad 77:01:000101:1

  # сетевой режим заработает после реализации NspdClient._request:
  NSPD_API_KEY=... python scripts/ingest_nspd.py --region 77 --limit 500

Пишет в БД из settings.DB_DSN. Вся пачка коммитится одной транзакцией.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Позволяем запускать как `python scripts/ingest_nspd.py` из каталога backend.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.session import SessionLocal  # noqa: E402
from app.etl.nspd.client import NspdClient  # noqa: E402
from app.etl.nspd.service import ingest_many  # noqa: E402


def _build_client(args: argparse.Namespace) -> NspdClient:
    if args.fixture:
        return NspdClient.from_fixture(args.fixture)
    return NspdClient(api_key=os.getenv("NSPD_API_KEY"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ингест участков из НСПД")
    parser.add_argument("--fixture", help="путь к JSON-фикстуре (офлайн-режим)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cad", help="один кадастровый номер")
    group.add_argument("--region", help="код региона (пакетная загрузка)")
    parser.add_argument("--limit", type=int, default=100, help="макс. записей для --region")
    args = parser.parse_args()

    client = _build_client(args)

    if args.cad:
        raw = client.fetch_by_cad(args.cad)
        raws = [raw] if raw else []
    else:
        raws = client.fetch_region(args.region, limit=args.limit)

    if not raws:
        print("Нет записей для ингеста.")
        return 1

    with SessionLocal() as db:
        summary = ingest_many(db, raws)
        db.commit()

    print(
        f"Готово: получено {len(raws)}, создано {summary.created}, "
        f"обновлено {summary.updated}, ошибок {summary.failed}."
    )
    return 0 if summary.failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
