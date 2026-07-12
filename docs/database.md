# База данных

## Стек

- **PostgreSQL 16** + расширение **PostGIS 3.4**
- **SQLAlchemy 2.0** (ORM, sync-режим)
- **GeoAlchemy2** — для геометрий
- **Alembic** — миграции

## Решение: sync SQLAlchemy + psycopg2

FastAPI — async-first, но на раннем этапе выбран **синхронный** SQLAlchemy через `psycopg2-binary`.
Причины:
- Проще отладка и первый опыт команды с SQLAlchemy 2.0.
- FastAPI автоматически выполняет синхронные хендлеры в threadpool — event loop не блокируется на уровне запроса.
- Переход на `asyncpg` + `AsyncSession` отложен до возникновения реальной нагрузки (v2.0).

Когда перейдём на async — поменяются только `session.py` и обёртки хендлеров; модели и схемы остаются.

## Соглашения

- Все таблицы в схеме `zn` (не в `public`).
- Имена таблиц — **snake_case**, единственное число (`asset`, `parcel`).
- Имена колонок — snake_case.
- Первичный ключ — `id BIGSERIAL`.
- `created_at` / `updated_at` — `TIMESTAMPTZ`, по умолчанию `now()`.
- `updated_at` обновляется триггером при UPDATE.
- Геометрии хранятся в проекции **EPSG:4326** (WGS84, lat/lon).

## Расширения

Первая миграция создаёт расширения:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
```

## Таблица `asset`

Первая и единственная таблица MVP. Соответствует доменной сущности Asset.

| Колонка | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | Внутренний ID |
| `cad_number` | `VARCHAR(40)` | UNIQUE, NOT NULL | Кадастровый номер `XX:XX:XXXXXX:XXX` |
| `address` | `TEXT` | nullable | Адрес/местоположение |
| `geometry` | `geometry(Polygon, 4326)` | nullable | Контур участка (PostGIS) |
| `area` | `NUMERIC(12, 2)` | nullable | Площадь в кв.м |
| `category` | `VARCHAR(100)` | nullable | Категория земель (ВРИ) |
| `owner_type` | `VARCHAR(30)` | nullable | Форма собственности: `state`/`municipal`/`private`/`unknown` |
| `status` | `VARCHAR(30)` | NOT NULL, default `active` | `active`/`archived`/`deleted` |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, default `now()` | Обновляется триггером |

## Индексы

| Имя | Колонка | Тип | Назначение |
|---|---|---|---|
| `uq_asset_cad_number` | `cad_number` | UNIQUE | Поиск по кадастровому номеру, защита от дублей |
| `ix_asset_geometry` | `geometry` | GIST | Пространственный поиск (ST_Within, ST_Intersects) |
| `ix_asset_status` | `status` | B-tree | Фильтр активных записей |

## Плановые таблицы (после MVP)

`parcel`, `listing`, `auction`, `restriction`, `opportunity`, `user`, `watchlist`, `event`, `ai_insight`.
Описываются в этом файле по мере реализации.
