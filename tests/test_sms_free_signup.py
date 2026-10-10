"""SMS-free customer contact registration: no false phone verification.

Uses test SQLite only; no Render, SMS or Telegram providers are contacted.
"""
import os
os.environ["DATABASE_URL"] = "sqlite:////tmp/ali_kuryer_ci_customer.db"
os.environ["SECRET_KEY"] = "only-for-regression-tests"
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient
from main import app
from app import models, security
from app.database import SessionLocal

client = TestClient(app)


def test_sms_free_signup_requires_explicit_enable(monkeypatch):
    monkeypatch.delenv("ALI_CONTACT_SIGNUP_ENABLED", raising=False)
    result = client.post("/api/auth/contact/register", json={
        "name": "Mijoz test", "phone": "+998901110031",
        "password": "StrongContact#2026", "accepted_privacy": True,
    })
    assert result.status_code == 503


def test_phone_is_contact_only_and_verified_number_not_taken_over(monkeypatch):
    monkeypatch.setenv("ALI_CONTACT_SIGNUP_ENABLED", "1")
    phone = "+998901110032"
    password = "NoSmsContact#2026"
    # A verified user already owns this phone. Unverified signup cannot
    # claim it, log into it, or prevent that owner's verification.
    with SessionLocal() as db:
        existing = models.User(
            name="Original verified", phone=phone,
            password_hash=security.hash_password("OriginalOwner#2026"),
            role="customer", is_active=True
        )
        db.add(existing)
        db.flush()
        proof = models.VerifiedPhone(phone=phone, user_id=existing.id)
        db.add(proof)
        db.commit()
        old_id = existing.id
    try:
        registration = client.post("/api/auth/contact/register", json={
            "name": "Yangi aloqa", "phone": phone,
            "password": password, "accepted_privacy": True
        })
        assert registration.status_code == 201, registration.text
        assert registration.json()["phone_verified"] is False
        token = registration.json()["access_token"]
        me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
        assert me.status_code == 200
        assert me.json()["phone"] == phone
        assert me.json()["phone_verified"] is False
        assert me.json()["id"] != old_id
        with SessionLocal() as db:
            account = db.get(models.User, me.json()["id"])
            contact = db.get(models.UnverifiedCustomerContact, me.json()["id"])
            assert account.phone is None
            assert contact.phone == phone
            assert db.get(models.VerifiedPhone, phone).user_id == old_id
        no_password = client.post("/api/auth/contact/login", json={
            "phone": phone, "password": "incorrect"
        })
        assert no_password.status_code == 401
        logged_in = client.post("/api/auth/contact/login", json={
            "phone": phone, "password": password
        })
        assert logged_in.status_code == 200, logged_in.text
        assert logged_in.json()["phone_verified"] is False
    finally:
        with SessionLocal() as db:
            db.query(models.UnverifiedCustomerContact).filter_by(phone=phone).delete()
            db.query(models.VerifiedPhone).filter_by(phone=phone).delete()
            db.query(models.User).filter_by(phone=phone).delete()
            db.query(models.User).filter_by(id=me.json()["id"]).delete()
            db.commit()


def test_no_sms_signup_rejects_weak_data_and_consent(monkeypatch):
    monkeypatch.setenv("ALI_CONTACT_SIGNUP_ENABLED", "1")
    sample = {"name": "Bir", "phone": "+998901110033",
              "password": "StrongContact#2026", "accepted_privacy": False}
    assert client.post("/api/auth/contact/register", json=sample).status_code == 422
    assert client.post("/api/auth/contact/register", json={
        **sample, "accepted_privacy": True, "phone": "invalid"
    }).status_code == 422


def test_sms_free_signup_cannot_use_temporary_production_sqlite(monkeypatch):
    from app import database
    monkeypatch.setenv("ALI_CONTACT_SIGNUP_ENABLED", "1")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setattr(database, "DATABASE_URL", "sqlite:////tmp/test-only.db")
    response = client.post("/api/auth/contact/register", json={
        "name": "Sinov", "phone": "+998901110034",
        "password": "StrongContact#2026", "accepted_privacy": True
    })
    assert response.status_code == 503
