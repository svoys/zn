"""Pytest configuration.

Обеспечивает:
  - импортируемость `app.*` из корня backend/.
  - переменную окружения DB_DSN для тестов (можно перезаписать).
"""

import os
import sys
from pathlib import Path

# backend/ — корень для абсолютных импортов `app.*`.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# На случай, если .env не подгрузится — дефолтная тестовая БД.
os.environ.setdefault("DB_DSN", "postgresql+psycopg2://zn:zn@localhost:5432/zn_test")
