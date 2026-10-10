"""Safeguards for role-gated admin settings and inactive payment placeholders."""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ali_kuryer_ci_customer.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "only-for-regression-tests")

from fastapi.testclient import TestClient
from app import models, security
from app.database import SessionLocal
from main import app

client = TestClient(app)


def bootstrap_accounts():
    with SessionLocal() as db:
        for phone, name, role in [
            ("+998909900001", "Platform Admin Test", "admin"),
            ("+998909900002", "Mijoz Test", "customer"),
        ]:
            obj = db.query(models.User).filter_by(phone=phone).first()
            if obj is None:
                obj = models.User(phone=phone, name=name, role=role,
                                  password_hash="test", is_active=True)
                db.add(obj)
                db.flush()
            elif obj.role != role:
                obj.role = role
            if role == "admin": aid = obj.id
            else: uid = obj.id
        db.commit()
    def h(user_id, role):
        return {"Authorization": "Bearer " + security.create_access_token(
            {"sub": str(user_id), "role": role}
        )}
    return h(aid, "admin"), h(uid, "customer")


def test_admin_settings_permissions_and_payment_safety():
    admin, customer = bootstrap_accounts()
    assert client.get("/api/admin/platform-config").status_code == 401
    assert client.get("/api/admin/platform-config", headers=customer).status_code == 403
    assert client.get("/api/admin/customers", headers=customer).status_code == 403

    payload = {
        "contacts": {
            "support_phone": "+998901234567", "support_email": "info@example.uz",
            "telegram_url": "https://t.me/AliKuryerYordamBot",
            "office_address": "Namangan",
        },
        "providers": {
            x: {"contract_signed": True, "requested_enabled": True,
                "merchant_id": "public123", "merchant_label": x}
            for x in ("click", "payme", "bank_card")
        },
    }
    saved = client.put("/api/admin/platform-config", headers=admin, json=payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()["providers"]["click"]["contract_signed"] is True
    public = client.get("/api/public/platform-config")
    assert public.status_code == 200
    assert public.json()["contacts"]["support_phone"] == "+998901234567"
    assert public.json()["online_payments_available"] is False
    assert all(x["available"] is False for x in public.json()["payment_methods"] if x["id"] != "cash")
    assert "public123" not in public.text

    # No card number or CVV accepted, no real card processing yet.
    assert client.post("/api/customer/saved-cards",
                       headers=customer,
                       json={"pan": "4111111111111111", "cvv": "123"}).status_code == 503
    assert client.get("/api/customer/saved-cards", headers=customer).json()["cards"] == []


def test_public_and_customer_list():
    admin, customer = bootstrap_accounts()
    listing = client.get("/api/admin/customers?limit=10", headers=admin)
    assert listing.status_code == 200
    customers = listing.json()["customers"]
    assert any(x["name"] == "Mijoz Test" for x in customers)
    assert all("password_hash" not in x and "google_sub" not in x for x in customers)
    assert client.get("/api/admin/customers?limit=101", headers=admin).status_code == 422
    assert client.get("/admin/settings").status_code == 404


def test_refuse_secret_like_keys_and_external_telegram():
    admin, _ = bootstrap_accounts()
    payload = {
        "contacts": {"telegram_url": "https://evil.example/phish"},
        "providers": {x: {"merchant_id":"ok"} for x in ("click","payme","bank_card")},
    }
    assert client.put("/api/admin/platform-config", json=payload, headers=admin).status_code == 422
    payload["contacts"]["telegram_url"] = "https://t.me/AliKuryerYordamBot"
    payload["providers"]["click"]["api_secret"] = "should-not-save"
    assert client.put("/api/admin/platform-config", json=payload, headers=admin).status_code == 422


def test_legacy_site_cors_origin_is_allowlisted():
    response = client.options(
        "/api/public/platform-config",
        headers={
            "Origin": "https://ali-kuryer-1.onrender.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://ali-kuryer-1.onrender.com"


def test_payment_support_issues_only_admin_can_resolve():
    admin, customer = bootstrap_accounts()
    from app import models
    from app.database import SessionLocal
    with SessionLocal() as db:
        usr = db.query(models.User).filter_by(phone="+998909900002").first()
        owner = db.query(models.User).filter_by(phone="+998909900001").first()
        rest = models.Restaurant(name="Payment test restaurant", owner_id=owner.id, is_approved=True)
        db.add(rest)
        db.flush()
        order = models.Order(
            customer_id=usr.id, restaurant_id=rest.id, address="Namangan 10",
            total=51000, status="pending", payment_method="cash",
        )
        db.add(order)
        db.commit()
        order_id = order.id
    assert client.get("/api/admin/payment-issues", headers=customer).status_code == 403
    assert client.post("/api/admin/payment-issues", headers=customer, json={
        "provider":"payme","category":"payment_failed",
        "description":"Murojaat tafsilotlari"
    }).status_code == 403
    data = {
        "order_id": order_id,
        "provider":"bank_card", "category":"duplicate_charge",
        "description":"To‘lov ikki marta yechilgan bo‘lishi mumkin",
    }
    created = client.post("/api/customer/payment-issues", headers=customer, json=data)
    assert created.status_code == 201, created.text
    issue_id = created.json()["id"]
    duplicate = client.post("/api/customer/payment-issues", headers=customer, json=data)
    assert duplicate.json()["id"] == issue_id
    admin_list = client.get("/api/admin/payment-issues", headers=admin)
    assert any(item["id"] == issue_id for item in admin_list.json()["issues"])
    assert client.patch("/api/admin/payment-issues/"+str(issue_id),
        headers=customer, json={"status":"resolved","note":"Tekshirib chiqildi"}).status_code == 403
    rejected = client.patch("/api/admin/payment-issues/"+str(issue_id),
        headers=admin, json={"status":"resolved","note":"ok"})
    assert rejected.status_code == 422
    updated = client.patch("/api/admin/payment-issues/"+str(issue_id),
        headers=admin, json={"status":"awaiting_provider",
                              "note":"Bankdan to‘lov ma’lumotlari kutilmoqda",
                              "assign_to_self":True})
    assert updated.status_code == 200, updated.text
    assert updated.json()["assigned_admin_id"]
    event_log=client.get("/api/admin/payment-issues/"+str(issue_id)+"/audit",headers=admin)
    assert event_log.status_code == 200
    assert len(event_log.json()["events"]) == 2
    assert client.get("/api/admin/payment-issues/"+str(issue_id)+"/audit",
                      headers=customer).status_code == 403
    with SessionLocal() as db:
        fresh=db.get(models.Order,order_id)
        assert fresh.payment_method=="cash"
        assert fresh.status=="pending"
        assert fresh.total==51000


def test_reject_card_number_cvv_in_support_issue():
    admin, _ = bootstrap_accounts()
    for description in ("Kartam 4111 1111 1111 1111 dan pul yechildi",
                        "CVV 123 muammosi", "api_key eskirgan"):
        r=client.post("/api/admin/payment-issues",headers=admin,json={
            "provider":"click","category":"other","description":description
        })
        assert r.status_code==422,r.text
