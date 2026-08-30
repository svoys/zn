"""Pytest configuration.

Обеспечивает:
  - импортируемость `app.*` из корня backend/;
  - рабочий каталог = backend/, чтобы pydantic-settings нашёл .env;
  - ИЗОЛИРОВАННУЮ тестовую БД (TEST_DB_DSN), отдельную от боевой (DB_DSN).

Почему это важно: фикстуры выполняют `DELETE FROM zn.asset` и `drop_all`.
Раньше тесты использовали боевой `engine` из app.database.session (DB_DSN) и
могли стереть dev-данные. Теперь весь тестовый ввод-вывод идёт через отдельный
`test_engine` (TEST_DB_DSN), а зависимость `get_db` в приложении подменяется,
чтобы и API (TestClient) работал только с тестовой базой.
"""

import os
import sys
from pathlib import Path

import pytest

# backend/ — корень для абсолютных импортов `app.*` и для .env (env_file=".env").
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Тесты запускаются из backend/, чтобы pydantic-settings подхватил backend/.env.
os.chdir(BACKEND_DIR)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.session import get_db  # noqa: E402

# Импортируем ВСЕ модели (через `as`, чтобы не переопределить имя `app` ниже —
# `import app.modules.x.models` без `as` привязывает имя `app` к пакету `app`
# в этом модуле и затирает `from app.main import app`, ломая
# `app.dependency_overrides`), чтобы они зарегистрировались в Base.metadata:
# иначе create_all/drop_all ниже увидят только те таблицы, что успели
# импортировать другие тестовые модули к этому моменту.
from app.modules.ai_insight import models as _ai_insight_models  # noqa: E402,F401
from app.modules.asset import models as _asset_models  # noqa: E402,F401
from app.modules.event import models as _event_models  # noqa: E402,F401
from app.modules.opportunity import models as _opportunity_models  # noqa: E402,F401
from app.modules.parcel import models as _parcel_models  # noqa: E402,F401
from app.modules.restriction import models as _restriction_models  # noqa: E402,F401

from app.main import app  # noqa: E402

# ─── Safety net ────────────────────────────────────────────────────────────
# Тестовая БД ДОЛЖНА отличаться от боевой — иначе DELETE/drop_all снесут dev-данные.
if settings.TEST_DB_DSN == settings.DB_DSN:
    raise RuntimeError(
        "TEST_DB_DSN must differ from DB_DSN — tests wipe tables and would "
        "destroy your dev database. Set a separate TEST_DB_DSN in .env."
    )

# ─── Изолированный тестовый engine ──────────────────────────────────────────
test_engine = create_engine(settings.TEST_DB_DSN, pool_pre_ping=True, future=True)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)


def _get_test_db():
    """Тестовая версия зависимости get_db — сессия на test_engine."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Подмена зависимости: теперь и эндпоинты (через TestClient), и прямые обращения
# в тестах работают исключительно с тестовой БД.
app.dependency_overrides[get_db] = _get_test_db


@pytest.fixture(scope="session", autouse=True)
def _full_schema():
    """Создаёт ПОЛНУЮ схему один раз на весь тестовый сеанс и удаляет её в конце.

    Раньше каждый тестовый файл сам создавал/удалял свой подмножество таблиц
    (`Base.metadata.create_all/drop_all(tables=[...])`) в fixture с
    `scope="module"`. Так как `asset` ссылается FK из `parcel`/`restriction`/
    `opportunity`/`ai_insight`/`event`, порядок выполнения файлов имел значение:
    если один модуль ронял `asset` раньше, чем другой модуль успевал создать
    свою таблицу с FK на него — тесты падали с `UndefinedTable`/
    `DependentObjectsStillExist` в зависимости от порядка запуска
    (`pytest` целиком vs. один файл вроде `pytest tests/test_twin_api.py`).

    Теперь схема создаётся один раз здесь; отдельные файлы отвечают только за
    очистку СВОИХ строк (`DELETE FROM ...`) между тестами, а не за
    создание/удаление таблиц.
    """
    with test_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS zn"))
        conn.commit()
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
