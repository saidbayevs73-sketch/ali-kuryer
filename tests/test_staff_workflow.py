"""End-to-end API tests for staff login roles, order lifecycle, selfie and GPS."""
from test_startup import app_context


def auth(user_id):
    from app.security import create_access_token
    return {"Authorization": "Bearer " + create_access_token({"sub": str(user_id)})}


def test_staff_lifecycle(app_context, tmp_path, monkeypatch):
    client, Session = app_context
    from app.models import User
    from app.routers import courier
    monkeypatch.setattr(courier, "PRIVATE_UPLOAD_DIR", tmp_path / "selfies")
    with Session() as db:
        admin = User(name="Admin", phone="+998901231234", role="admin", password_hash="test")
        db.add(admin)
        db.commit()
        admin_id = admin.id
    admin_auth = auth(admin_id)

    restaurant_response = client.post("/api/admin/staff", headers=admin_auth, json={
        "name": "Oshxona mas'ul", "phone": "+998901232344",
        "password": "StrongRestaurantPass12", "role": "restaurant",
        "restaurant_name": "Ali Burger Test",
        "restaurant_address": "Namangan, test ko‘chasi 2",
    })
    assert restaurant_response.status_code == 201, restaurant_response.text
    restaurant_id = restaurant_response.json()["id"]
    restaurant_auth = auth(restaurant_id)

    courier_response = client.post("/api/admin/staff", headers=admin_auth, json={
        "name": "Kuryer Test", "phone": "+998901233455",
        "password": "StrongCourierPass12", "role": "courier",
    })
    assert courier_response.status_code == 201, courier_response.text
    courier_id = courier_response.json()["id"]
    courier_auth = auth(courier_id)


    # Video meeting links are staff-only; only admin may create/close.
    assert client.get("/api/panels/meetings").status_code == 401
    assert client.post("/api/panels/meetings", headers=courier_auth,
                       json={"title": "Test yig‘ilish"}).status_code == 403
    meeting = client.post("/api/panels/meetings", headers=admin_auth,
                          json={"title": "Test yig‘ilish"})
    assert meeting.status_code == 201, meeting.text
    meeting_id = meeting.json()["id"]
    assert meeting.json()["join_url"].startswith("https://meet.jit.si/")
    assert client.get("/api/panels/meetings", headers=restaurant_auth).status_code == 200
    assert any(r["id"] == meeting_id for r in client.get(
        "/api/panels/meetings", headers=courier_auth).json())
    assert client.post(f"/api/panels/meetings/{meeting_id}/close",
                       headers=restaurant_auth).status_code == 403
    assert client.post(f"/api/panels/meetings/{meeting_id}/close",
                       headers=admin_auth).status_code == 200

    # Staff accounts are scoped to their own roles.
    assert client.get("/api/restaurant/orders", headers=courier_auth).status_code == 403
    assert client.get("/api/courier/orders/mine", headers=restaurant_auth).status_code == 403
    assert client.get("/api/admin/orders", headers=courier_auth).status_code == 403
    assert client.get("/api/admin/courier-shifts").status_code == 401

    created_food = client.post("/api/restaurant/menu", headers=restaurant_auth, json={
        "name": "Chuchvara", "price": 25000,
    })
    assert created_food.status_code == 201, created_food.text
    food_id = created_food.json()["id"]

    order_resp = client.post("/api/orders", json={
        "name": "Mijoz Test", "phone": "+998909876543",
        "street": "Mustaqillik ko‘chasi", "house": "8",
        "lat": 40.9971, "lng": 71.6727, "payment": "cash",
        "items": [{"id": food_id, "qty": 2}],
    })
    assert order_resp.status_code == 201, order_resp.text
    order_id = order_resp.json()["order_id"]
    token = order_resp.json()["tracking_token"]

    assert client.get("/api/courier/orders/available", headers=courier_auth).status_code == 403
    assert client.post("/api/courier/orders/" + str(order_id) + "/claim",
                       headers=courier_auth).status_code == 403

    # Not a public asset: a selfie is stored outside /static, and requires
    # an admin role to view.
    shift_response = client.post("/api/courier/shifts/start",
        headers=courier_auth,
        data={"latitude": "40.9971", "longitude": "71.6727"},
        files={"selfie": ("selfie.jpg", b"\xff\xd8\xff" + b"x" * 300, "image/jpeg")})
    assert shift_response.status_code == 201, shift_response.text
    shift_id = shift_response.json()["shift_id"]
    photo_path = tmp_path / "selfies"
    assert len(list(photo_path.iterdir())) == 1
    assert client.get(f"/api/admin/courier-shifts/{shift_id}/photo").status_code == 401
    photo_response = client.get(f"/api/admin/courier-shifts/{shift_id}/photo",
                                headers=admin_auth)
    assert photo_response.status_code == 200
    assert photo_response.headers["cache-control"] == "private, no-store"
    approval = client.post(f"/api/admin/courier-shifts/{shift_id}/review",
                           headers=admin_auth, json={"status": "approved"})
    assert approval.status_code == 200, approval.text

    assert client.post(f"/api/restaurant/orders/{order_id}/status",
                       headers=restaurant_auth,
                       json={"status": "ready"}).status_code == 409
    assert client.post(f"/api/restaurant/orders/{order_id}/status",
                       headers=restaurant_auth,
                       json={"status": "preparing"}).status_code == 200
    assert client.post(f"/api/restaurant/orders/{order_id}/status",
                       headers=restaurant_auth,
                       json={"status": "ready"}).status_code == 200

    available = client.get("/api/courier/orders/available", headers=courier_auth)
    assert available.status_code == 200 and any(
        o["id"] == order_id for o in available.json()
    )
    claim = client.post(f"/api/courier/orders/{order_id}/claim",
                        headers=courier_auth)
    assert claim.status_code == 200, claim.text
    assert client.post(f"/api/courier/orders/{order_id}/claim",
                       headers=courier_auth).status_code == 409

    mine = client.get("/api/courier/orders/mine", headers=courier_auth)
    assert mine.status_code == 200
    assert any(o["id"] == order_id and o["phone"] == "+998909876543"
               for o in mine.json())

    location = client.post("/api/courier/location", headers=courier_auth, json={
        "latitude": 40.998, "longitude": 71.673,
    })
    assert location.status_code == 200, location.text
    tracking = client.post(f"/api/orders/{order_id}/track", json={"token": token})
    assert tracking.status_code == 200
    assert tracking.json()["courier_location"]["lat"] == 40.998

    assert client.post(f"/api/courier/orders/{order_id}/status",
                       headers=courier_auth,
                       json={"status": "delivered"}).status_code == 409
    assert client.post(f"/api/courier/orders/{order_id}/status",
                       headers=courier_auth,
                       json={"status": "on_the_way"}).status_code == 200
    assert client.post(f"/api/courier/orders/{order_id}/status",
                       headers=courier_auth,
                       json={"status": "delivered"}).status_code == 200
    assert client.post("/api/courier/location", headers=courier_auth, json={
        "latitude": 40.999, "longitude": 71.672,
    }).status_code == 403
