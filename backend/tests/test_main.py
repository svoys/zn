"""Smoke-тесты: Этап 1 — запуск API, корень и docs.

Покрывают базовую работоспособность FastAPI-приложения без БД.
Эти тесты не требуют PostgreSQL — используют TestClient с подменой БД.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRoot:
    """Этап 1: GET / должен отвечать 200 и отдавать метаданные приложения."""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_payload(self):
        response = client.get("/")
        body = response.json()
        assert body["project"] == "ZN API"
        assert body["status"] == "running"
        assert body["environment"] in {"development", "staging", "production"}


class TestDocs:
    """Этап 1: Swagger UI и OpenAPI-схема должны быть доступны."""

    def test_docs_page(self):
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()

    def test_redoc_page(self):
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_schema(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        # Эндпоинт Asset должен быть зарегистрирован.
        assert "/api/v1/asset/{cad_number}" in schema["paths"]
        assert "get" in schema["paths"]["/api/v1/asset/{cad_number}"]
