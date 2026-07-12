"""Alembic environment.

Источником схемы является SQLAlchemy-модель `Base.metadata` из `app.database.base`.
DSN берётся из настроек приложения (`app.core.config.settings.DB_DSN`), а не из alembic.ini,
чтобы конфигурация БД была единственным местом правды.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Импортируем настройки приложения и метаданные моделей.
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Добавляем корень backend/ в sys.path, чтобы работали абсолютные импорты `app.*`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
import app.modules.asset.models  # noqa: E402,F401  # регистрируем модели в метаданных

# DSN из настроек приложения, не из alembic.ini.
config.set_main_option("sqlalchemy.url", settings.DB_DSN)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Offline-режим: SQL генерируется без подключения к БД."""
    context.configure(
        url=settings.DB_DSN,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online-режим: миграции применяются к подключённой БД."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
