# Задачи ZN

Живой список статуса разработки. Обновляется по мере прогресса.

---

## MVP (Этап 1–7)

| # | Этап | Статус | Коммит |
|---|---|---|---|
| 1 | Запуск API (`/`, `/docs`) | ✅ Готов | `ddb32a7` |
| 2 | Подключение PostgreSQL | ✅ Готов | `ddb32a7` |
| 3 | SQLAlchemy (base, session) | ✅ Готов | `ddb32a7` |
| 4 | Alembic (инициализация, миграции) | ✅ Готов | `ddb32a7`, `dbbd749` |
| 5 | Бизнес-модель Asset (9 полей) | ✅ Готов | `ddb32a7` |
| 6 | REST API `GET /asset/{cad_number}` | ✅ Готов | `ddb32a7` |
| 7 | Digital Twin | ⏳ Не начат | — |

---

## Инфраструктура

| Задача | Статус |
|---|---|
| Git/GitHub подключён (`svoys/zn`) | ✅ |
| `.gitignore` (venv, env, logs, pycache) | ✅ |
| Виртуальное окружение `.venv` | ✅ |
| `docker-compose.yml` (postgis/postgis) | ✅ |
| БД Neon (PostgreSQL 16 + PostGIS) подключена | ✅ |
| Миграция `0001` применена (таблица `zn.asset`) | ✅ |
| Тесты (11/11 passed) | ✅ |
| Демо-данные (2 актива) | ✅ |
| `developer-handbook.md` | ✅ |

---

## В плане

### Ближайшие задачи (по приоритету)

- [ ] **Geometry с реальным полигоном** — добавить демо-полигон в `zn.asset`, проверить отдачу GeoJSON через `ST_AsGeoJSON`
- [ ] **Модуль `search`** — умный поиск с фильтрами (регион, площадь, ВРИ, цена) + пагинация
- [ ] **Модуль `gis`** — каталог для GIS-операций (пространственные запросы: `ST_Within`, `ST_Intersects`)
- [ ] **Модуль `notifications`** — каталог (в архитектурной схеме есть, в коде нет)

### Среднесрочные

- [ ] Digital Twin — агрегация данных (карта, ограничения, история, AI-анализ, Opportunity Score)
- [ ] ETL — загрузка данных из Росреестра, НСПД, ГИС Торги, Авито, ЦИАН, OpenStreetMap
- [ ] Модель `Parcel` — специализация Asset под земельный участок
- [ ] Модель `Listing` — объявление о продаже
- [ ] Модель `Opportunity` — инвестиционная возможность (⭐ ключевая сущность)
- [ ] Переход на async SQLAlchemy (`asyncpg` + `AsyncSession`)

### Долгосрочные (v2.0–v3.0)

- [ ] Торги, сделки, автоматическая оценка стоимости
- [ ] Мониторинг рынка
- [ ] Telegram-бот
- [ ] API для бизнеса
- [ ] AI-ассистент, прогноз стоимости
- [ ] Генерация инвестиционных отчётов
- [ ] Совместная работа команд

---

## Документация

| Файл | Статус |
|---|---|
| `docs/project.md` (через PROJECT.md) | ✅ |
| `docs/principles.md` | ✅ |
| `docs/domain-model.md` | ✅ |
| `docs/features.md` | ✅ |
| `docs/system-design.md` | ✅ |
| `docs/api.md` | ✅ |
| `docs/database.md` | ✅ |
| `docs/developer-handbook.md` | ✅ |
| `docs/vision.md` | ❌ Пусто |
| `docs/roadmap.md` | ❌ Пусто |
| `docs/architecture.md` | ❌ Пусто |
| `docs/modules.md` | ❌ Пусто |
| `docs/ui.md` | ❌ Пусто |
| `docs/etl.md` | ❌ Пусто |
| `docs/ai.md` | ❌ Пусто |
