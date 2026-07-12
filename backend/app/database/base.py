"""SQLAlchemy declarative base.

Все модели наследуются от `Base`. Метаданные `Base.metadata` используются
Alembic для автогенерации миграций.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Декларативная база для всех моделей ZN."""
