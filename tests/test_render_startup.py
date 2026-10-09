"""Regression tests for Render web-service startup."""
import os

# Use an isolated database; no production services or secrets are required.
os.environ["DATABASE_URL"] = "sqlite:////tmp/ali_kuryer_ci_customer.db"
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
    # Admin is private; staff routes intentionally redirect to dedicated staff backend.
    assert client.get("/admin", follow_redirects=False).status_code == 404
    for url in ("/restaurant", "/courier"):
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 303
        assert "ali-kuryer-1.onrender.com" in response.headers["location"]


def test_auth_schemas_exist_and_validate():
    user = RegisterRequest(
        name="Sinov Mijoz",
        phone="+998901234567",
        password="testpassword123",
    )
    assert user.name == "Sinov Mijoz"
    assert LoginRequest(phone=user.phone, password=user.password).phone == user.phone


def test_customer_order_chat_and_permissions():
    from app import models, security
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # No external payment or courier side effects in these tests.
        rest_owner = models.User(name="Sinov oshxona", phone="+998900000041",
                                 password_hash="test", role="restaurant", is_active=True)
        customer = models.User(name="Sinov xaridor", phone="+998900000042",
                               password_hash="test", role="customer", is_active=True)
        other = models.User(name="Boshqa mijoz", phone="+998900000043",
                            password_hash="test", role="customer", is_active=True)
        db.add_all([rest_owner, customer, other])
        db.flush()
        restaurant = models.Restaurant(name="Sinov oshxona 41", owner_id=rest_owner.id,
                                       is_approved=True)
        db.add(restaurant)
        db.flush()
        food = models.MenuItem(name="Sinov taom", restaurant_id=restaurant.id,
                               price=27000, is_available=True)
        db.add(food)
        db.commit()
        rid, fid = restaurant.id, food.id
        customer_id, other_id, owner_id = customer.id, other.id, rest_owner.id
    finally:
        db.close()

    def headers(uid, user_role):
        return {"Authorization": "Bearer " + security.create_access_token(
            {"sub": str(uid), "role": user_role}
        )}

    payload = {"restaurant_id": rid, "address": "Namangan shahar, 12-uy",
               "phone": "+998900000042", "privacy_accepted": True,
               "payment_method": "cash",
               "items": [{"menu_item_id": fid, "quantity": 2}]}
    response = client.post("/api/v1/orders", json=payload,
                           headers=headers(customer_id, "customer"))
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total"] == 54000
    order_id = data["id"]
    assert client.get(f"/api/v1/orders/{order_id}",
                      headers=headers(other_id, "customer")).status_code == 403
    assert client.get("/api/v1/orders/my",
                      headers=headers(customer_id, "customer")).json()[0]["id"] == order_id

    status = client.post(f"/api/v1/orders/{order_id}/status",
                         json={"status": "preparing"},
                         headers=headers(owner_id, "restaurant"))
    assert status.status_code == 200
    assert status.json()["status"] == "preparing"

    chat = client.post(f"/api/v1/orders/{order_id}/messages",
                       json={"body": "Taom qachon tayyor?"},
                       headers=headers(customer_id, "customer"))
    assert chat.status_code == 201
    assert client.get(f"/api/v1/orders/{order_id}/messages",
                      headers=headers(other_id, "customer")).status_code == 403

    support = client.post("/api/v1/support/messages",
                          json={"body": "Operator bilan gaplashmoqchiman"},
                          headers=headers(customer_id, "customer"))
    assert support.status_code == 201
    assert client.get("/api/v1/support/messages",
                      headers=headers(other_id, "customer")).json() == []
