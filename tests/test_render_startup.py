"""Regression tests for Render web-service startup."""
import os

# Use an isolated database; no production services or secrets are required.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "only-for-regression-tests"

from fastapi.testclient import TestClient

from app.schemas import LoginRequest, RegisterRequest
from main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_website_is_served_from_repository_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Ali Kuryer" in response.text


def test_missing_panels_do_not_crash_server():
    for url in ("/admin", "/restaurant", "/courier"):
        response = client.get(url)
        assert response.status_code == 404


def test_auth_schemas_exist_and_validate():
    user = RegisterRequest(
        name="Sinov Mijoz",
        phone="+998901234567",
        password="testpassword123",
    )
    assert user.name == "Sinov Mijoz"
    assert LoginRequest(phone=user.phone, password=user.password).phone == user.phone
