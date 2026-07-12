# Developer Handbook

Краткий справочник для запуска и разработки ZN.

---

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/svoys/zn.git
cd zn
```

### 2. Настройка Python

Требуется Python 3.11+.

```bash
cd backend
python -m venv .venv

# Активация:
# Windows (Git Bash / PowerShell):
.venv/Scripts/activate
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. База данных

ZN использует PostgreSQL с расширением PostGIS. Есть два варианта.

**Вариант A — Neon (облако, без установки):**
1. Зарегистрируйтесь на https://neon.tech (через GitHub)
2. Создайте проект, скопируйте connection string
3. Вставьте в `backend/.env` как `DB_DSN` (формат ниже)

**Вариант B — Docker локально:**
```bash
# Из корня проекта (где docker-compose.yml):
docker compose up -d
```
Поднимется два контейнера: основная БД (порт 5432) и тестовая (5433).

### 4. Конфигурация (.env)

Скопируйте `.env.example` → `backend/.env` и заполните:

```env
APP_NAME=ZN API
APP_ENV=development
APP_DEBUG=True
HOST=127.0.0.1
PORT=8000

# Формат: postgresql+psycopg2://user:password@host:port/dbname
DB_DSN=postgresql+psycopg2://zn:zn@localhost:5432/zn
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

TEST_DB_DSN=postgresql+psycopg2://zn:zn@localhost:5432/zn_test
```

> ⚠️ `backend/.env` в `.gitignore` — не коммитите секреты.

### 5. Миграции

```bash
# Из backend/ с активированным venv:
alembic upgrade head       # применить все миграции
alembic current            # показать текущую ревизию
alembic downgrade -1       # откатить последнюю
alembic revision --autogenerate -m "описание"  # создать новую
```

### 6. Запуск API

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

### 7. Тесты

```bash
# Из backend/ с активированным venv:
pytest                       # все тесты
pytest tests/test_main.py    # только smoke
pytest -v                    # подробный вывод
pytest --tb=short            # короткие трейсбеки
```

Тесты делятся на два слоя:
- **Smoke/валидация** — без БД, всегда зелёные (запуск API, `/docs`, валидация cad_number)
- **Бизнес-логика** — требуют живой БД (вставка актива, проверка 200/404)

---

## Структура проекта

```
zn/
├── backend/
│   ├── app/
│   │   ├── api/              # HTTP-эндпоинты
│   │   │   ├── __init__.py   # api_router (префикс /api/v1)
│   │   │   └── asset.py      # GET /asset/{cad_number}
│   │   ├── core/             # конфиг, логирование
│   │   ├── database/         # SQLAlchemy base, engine, session
│   │   ├── modules/          # доменные модули
│   │   │   ├── asset/        # модели, схемы, CRUD
│   │   │   ├── ai/           # (пусто, планируется)
│   │   │   ├── monitoring/   # (пусто, планируется)
│   │   │   └── search/       # (пусто, планируется)
│   │   └── main.py           # FastAPI app
│   ├── alembic/              # миграции
│   │   └── versions/
│   ├── tests/                # pytest
│   ├── .env                  # локальный конфиг (в gitignore)
│   ├── requirements.txt
│   ├── pytest.ini
│   └── alembic.ini
├── docs/                     # документация проекта
├── .env.example              # шаблон конфига
├── .gitignore
└── docker-compose.yml        # PostGIS контейнеры
```

---

## Стек

| Слой | Технология |
|---|---|
| API | FastAPI |
| ORM | SQLAlchemy 2.0 (sync, через psycopg2) |
| Геометрии | GeoAlchemy2 + PostGIS |
| Миграции | Alembic |
| БД | PostgreSQL 16 + PostGIS 3.4 |
| Логирование | loguru |
| Тесты | pytest + FastAPI TestClient |

---

## Архитектурные решения

### Sync SQLAlchemy, не async

FastAPI — async-first, но на старте выбран **синхронный** SQLAlchemy через `psycopg2`:
- Проще отладка и обучение
- FastAPI автоматически выполняет синхронные хендлеры в threadpool — event loop не блокируется
- Переход на `asyncpg` + `AsyncSession` запланирован на v2.0 (поменяются только `session.py` и обёртки хендлеров)

### Схема `zn`, не `public`

Все доменные таблицы в схеме `zn`. Изолирует домен от системных таблиц и расширений.

### Кадастровый номер — естественный ключ

Формат `XX:XX:XXXXXX:XXX`, валидируется regex на уровне API (`Path(pattern=...)`) и имеет UNIQUE-индекс в БД.

### Геометрии в WGS84 (EPSG:4326)

PostGIS хранит полигоны в SRID 4326. На API отдаются как GeoJSON через `ST_AsGeoJSON`.

---

## Частые команды

```bash
# Git
git add -A && git commit -m "..." && git push

# Зависимости — добавить новый пакет
pip install <package>
pip freeze | grep -i <package> >> requirements.txt  # или вписать вручную

# Создать миграцию после изменения моделей
alembic revision --autogenerate -m "описание"
alembic upgrade head

# Перезапустить API (если без --reload)
# Ctrl+C, затем снова uvicorn app.main:app --reload
```

---

## Что готово, что в плане

См. `TASKS.md`.
