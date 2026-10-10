"""Firebase phone verification regression tests; no network calls to Google."""
import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:////tmp/ali_kuryer_ci_customer.db"
os.environ["SECRET_KEY"] = "only-for-regression-tests"
os.environ["ENVIRONMENT"] = "test"

from main import app
from app import auth, models
from app.database import SessionLocal

client = TestClient(app)


def test_phone_login_is_disabled_without_explicit_firebase_activation(monkeypatch):
    monkeypatch.delenv("FIREBASE_PHONE_ENABLED", raising=False)
    response = client.post("/api/auth/firebase/phone-login", json={
        "id_token": "fake-token-" + ("x" * 110), "name": "Test"
    })
    assert response.status_code == 503
    assert "access_token" not in response.text


def test_phone_login_never_accepts_unverified_short_token():
    response = client.post("/api/auth/firebase/phone-login", json={
        "id_token": "short", "name": "Test"
    })
    assert response.status_code == 422


def test_phone_login_and_replay_idempotent_for_verified_customer(monkeypatch):
    monkeypatch.setenv("FIREBASE_PHONE_ENABLED", "1")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "ali-kuryer")
    phone = "+998909120074"
    uid = "firebase_test_uid_ali_074"
    monkeypatch.setattr(auth, "validate_firebase_phone_token",
                        lambda token: (phone, uid))
    response = client.post("/api/auth/firebase/phone-login", json={
        "id_token": "test-verified-id-token-" + ("a" * 120), "name": "Ali Test"
    })
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    profile = client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
    assert profile.status_code == 200
    assert profile.json()["phone"] == phone
    response2 = client.post("/api/auth/firebase/phone-login", json={
        "id_token": "test-verified-id-token-" + ("b" * 120), "name": "Ali Test"
    })
    assert response2.status_code == 200
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(phone=phone).one()
        proof = db.get(models.VerifiedPhone, phone)
        assert proof.user_id == user.id
        identity = db.get(models.FirebasePhoneIdentity, uid)
        assert identity.user_id == user.id


def test_staff_phone_cannot_escalate_via_firebase(monkeypatch):
    monkeypatch.setenv("FIREBASE_PHONE_ENABLED", "1")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "ali-kuryer")
    phone = "+998909120075"
    from app.security import hash_password
    with SessionLocal() as db:
        if not db.query(models.User).filter_by(phone=phone).first():
            db.add(models.User(name="Courier", phone=phone,
                               role="courier", password_hash=hash_password("TestPassword123"),
                               is_active=True))
            db.commit()
    monkeypatch.setattr(auth, "validate_firebase_phone_token",
                        lambda token: (phone, "firebase_test_uid_courier_075"))
    result = client.post("/api/auth/firebase/phone-login", json={
        "id_token": "test-staff-token-" + ("q" * 120)
    })
    assert result.status_code == 403
    assert "access_token" not in result.text
