"""Pytest configuration.

Обеспечивает:
  - импортируемость `app.*` из корня backend/.
  - рабочий каталог = backend/, чтобы pydantic-settings нашёл .env.
"""

import sys
from pathlib import Path

# backend/ — корень для абсолютных импортов `app.*` и для .env (env_file=".env").
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Тесты запускаются из backend/, чтобы pydantic-settings подхватил backend/.env.
import os  # noqa: E402

os.chdir(BACKEND_DIR)

