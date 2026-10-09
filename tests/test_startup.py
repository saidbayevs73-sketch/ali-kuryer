"""Run the real application against an isolated SQLite database only."""
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app_context():
    with tempfile.TemporaryDirectory(prefix="ali-kuryer-test-") as directory:
        os.environ["DATABASE_URL"] = f"sqlite:///{directory}/test.db"
        os.environ["SECRET_KEY"] = "test-only-key-not-for-deployment"
        os.environ["ENVIRONMENT"] = "development"
        from app.database import Base, SessionLocal, engine
        from app.models import Order, Restaurant, MenuItem
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            restaurant = Restaurant(name="Existing restaurant")
            db.add(restaurant)
            db.flush()
            db.add(MenuItem(restaurant_id=restaurant.id, name="Existing meal", price=15000))
            db.add(Order(address="Existing address", restaurant_id=restaurant.id, total=15000, status="pending"))
            db.commit()
        main = importlib.import_module("main")
        with TestClient(main.app) as client:
            yield client, SessionLocal
        engine.dispose()


def test_pages_and_assets(app_context):
    client, _ = app_context
    for path in ("/", "/admin", "/restaurant", "/courier"):
        response = client.get(path)
        assert response.status_code == 200
        assert "Ali Kuryer" in response.text
        assert 'href="http://testserver/static/app.css"' in response.text
        assert 'src="http://testserver/static/app.js"' in response.text
        assert response.headers["x-frame-options"] == "DENY"
    for path, content_type in (("/static/app.css", "text/css"), ("/static/app.js", "javascript")):
        response = client.get(path)
        assert response.status_code == 200
        assert content_type in response.headers["content-type"]


def test_health_and_database_preservation(app_context):
    client, Session = app_context
    from app.models import Order
    assert client.get("/api/health").json()["ok"] is True
    assert client.get("/api/customer/restaurants").json()[0]["name"] == "Existing restaurant"
    assert client.get("/api/customer/restaurants/1/menu").json()["items"][0]["price"] == 15000
    assert client.get("/api/customer/restaurants/999/menu").status_code == 404
    result = subprocess.run([sys.executable, "-c", "import main"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with Session() as db:
        order = db.get(Order, 1)
        assert (order.address, order.total, order.status) == ("Existing address", 15000, "pending")
        assert db.query(Order).count() == 1


def test_registration_and_login(app_context):
    client, Session = app_context
    from app.models import User
    from app.security import decode_access_token
    user = {"name": "Test user", "phone": "+998901234567", "password": "TestPassword123"}
    assert client.post("/api/auth/register", json=user).status_code == 201
    assert client.post("/api/auth/register", json=user).status_code == 409
    login = {"phone": user["phone"], "password": user["password"]}
    response = client.post("/api/auth/login", json=login)
    assert response.status_code == 200
    assert decode_access_token(response.json()["access_token"])["role"] == "customer"
    assert client.post("/api/auth/login", json={**login, "password": "wrong"}).status_code == 401
    with Session() as db:
        assert db.query(User).filter_by(phone=user["phone"]).one().password_hash != user["password"]


@pytest.mark.parametrize("changes", [{"password": "short"}, {"password": "a" * 73}, {"password": "é" * 37}, {"name": "  "}])
def test_invalid_registration(app_context, changes):
    client, _ = app_context
    user = {"name": "Test user", "phone": "+998901234568", "password": "TestPassword123"}
    assert client.post("/api/auth/register", json={**user, **changes}).status_code == 422


def test_invalid_phone(app_context):
    client, _ = app_context
    response = client.post("/api/auth/register", json={"name": "Test user", "phone": "+1239012345689", "password": "TestPassword123"})
    assert response.status_code == 400


def test_production_docs_and_paths(app_context):
    environment = {**os.environ, "ENVIRONMENT": "production"}
    root = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = root
    code = "from fastapi.testclient import TestClient; import main; c=TestClient(main.app); assert c.get('/api/docs').status_code == 404; assert c.get('/').status_code == 200; assert c.get('/static/app.css').status_code == 200"
    result = subprocess.run([sys.executable, "-c", code], cwd="/tmp", env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
