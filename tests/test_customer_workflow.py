"""Isolated tests for checkout, location and complaint permissions."""
from fastapi.testclient import TestClient
import pytest

# Reuse the isolated temporary database and app client from test_startup.py.
from test_startup import app_context


def make_order(**changes):
    payload = {
        "name": "Test Buyer", "phone": "+998901112233",
        "street": "Namangan markazi", "house": "15",
        "lat": 40.995, "lng": 71.672, "payment": "cash",
        "items": [{"id": 1, "qty": 2}],
    }
    payload.update(changes)
    return payload


def enable_restaurant(Session):
    from app.models import Restaurant
    with Session() as db:
        restaurant = db.get(Restaurant, 1)
        restaurant.is_approved = True
        db.commit()


def test_checkout_and_private_tracking(app_context):
    client, Session = app_context
    enable_restaurant(Session)
    response = client.post("/api/orders", json=make_order())
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["total"] == 30000
    assert data["payment"] == "cash"
    assert len(data["tracking_token"]) >= 20

    tracked = client.post(
        f"/api/orders/{data['order_id']}/track",
        json={"token": data["tracking_token"]},
    )
    assert tracked.status_code == 200
    assert tracked.json()["total"] == 30000
    assert client.post(
        f"/api/orders/{data['order_id']}/track",
        json={"token": "bad" * 10},
    ).status_code == 404
    assert client.get(f"/api/orders/{data['order_id']}/track").status_code == 405

    from app.models import DeliveryDetail, OrderItem
    with Session() as db:
        detail = db.query(DeliveryDetail).filter_by(order_id=data["order_id"]).one()
        assert (detail.latitude, detail.longitude) == (40.995, 71.672)
        assert detail.recipient_name == "Test Buyer"
        assert db.query(OrderItem).filter_by(order_id=data["order_id"]).one().quantity == 2


@pytest.mark.parametrize("change", [
    {"payment": "click"},
    {"lat": 91},
    {"phone": "12345"},
    {"items": [{"id": 999999, "qty": 1}]},
    {"items": [{"id": 1, "qty": 40}]},
])
def test_checkout_rejects_invalid_data(app_context, change):
    client, Session = app_context
    enable_restaurant(Session)
    response = client.post("/api/orders", json=make_order(**change))
    assert response.status_code in (400, 422)


def test_public_page_excludes_staff_links(app_context):
    client, _ = app_context
    response = client.get("/")
    assert response.status_code == 200
    assert "Adminga murojaat" in response.text
    for private in ('href="/admin"', 'href="/restaurant"', 'href="/courier"'):
        assert private not in response.text
    assert client.get("/static/app.js").status_code == 200


def test_anonymous_complaint_and_admin_auth(app_context):
    client, Session = app_context
    response = client.post("/api/customer/complaints", json={
        "name": "Test Buyer",
        "phone": "+998901112233",
        "message": "Yetkazib berishda xizmat sifati haqida murojaatim bor.",
    })
    assert response.status_code == 201, response.text
    complaint_id = response.json()["complaint_id"]

    assert client.get("/api/admin/complaints").status_code == 401

    from app.models import User
    from app.security import create_access_token
    with Session() as db:
        db.add(User(name="Staff", phone="+998909998877", role="admin",
                    password_hash="not-used"))
        db.add(User(name="Customer", phone="+998907776655", role="customer",
                    password_hash="not-used"))
        db.commit()
        admin = db.query(User).filter_by(role="admin").first()
        customer = db.query(User).filter_by(phone="+998907776655").one()
        admin_id, customer_id = admin.id, customer.id

    def bearer(user_id):
        return {"Authorization": "Bearer " + create_access_token({"sub": str(user_id)})}

    assert client.get("/api/admin/complaints", headers=bearer(customer_id)).status_code == 403
    result = client.get("/api/admin/complaints", headers=bearer(admin_id))
    assert result.status_code == 200
    assert any(row["id"] == complaint_id for row in result.json())

    reply = client.post(
        f"/api/admin/complaints/{complaint_id}/reply",
        json={"reply": "Murojaatingiz qabul qilindi, tekshiramiz."},
        headers=bearer(admin_id),
    )
    assert reply.status_code == 200
    assert reply.json()["status"] == "answered"
