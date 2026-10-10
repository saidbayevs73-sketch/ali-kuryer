"""SMS OTP security tests. Captured code is a fake SMS service used ONLY here."""
import os
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ali_kuryer_ci_customer.db")
os.environ.setdefault("SECRET_KEY", "only-for-regression-tests")
os.environ.setdefault("ENVIRONMENT", "test")

from main import app
from app import models, otp
from app.database import SessionLocal

client = TestClient(app)


def fake_provider(monkeypatch):
    codes = {}
    monkeypatch.setenv("ALI_SMS_PROVIDER", "eskiz")
    monkeypatch.setenv("ESKIZ_API_TOKEN", "test-only-no-network")
    monkeypatch.setenv("ALI_SMS_SENDER", "TEST")
    monkeypatch.setattr(otp, "send_sms", lambda phone, code: codes.__setitem__(phone, code))
    return codes


def test_wrong_missing_expired_and_reused_sms_codes(monkeypatch):
    captured = fake_provider(monkeypatch)
    phone = "+998901110041"
    payload = {"name": "OTP tester", "phone": phone, "password": "ValidPassword123"}
    assert client.post("/api/auth/register", json=payload).status_code == 422
    assert client.post("/api/auth/register", json={**payload, "otp_code": "123456"}).status_code == 400
    started = client.post("/api/auth/otp/request", json={"phone": phone})
    assert started.status_code == 200
    assert "code" not in started.json()
    assert len(captured[phone]) == 6
    assert client.post("/api/auth/otp/request", json={"phone": phone}).status_code == 429
    # Wrong code causes a failed attempt and cannot create an account.
    wrong = "000000" if captured[phone] != "000000" else "999999"
    assert client.post("/api/auth/register", json={**payload, "otp_code": wrong}).status_code == 400
    with SessionLocal() as db:
        assert db.query(models.User).filter_by(phone=phone).first() is None
    ok = client.post("/api/auth/register", json={**payload, "otp_code": captured[phone]})
    assert ok.status_code == 201, ok.text
    # Replay cannot create a second user.
    assert client.post("/api/auth/register", json={**payload, "otp_code": captured[phone]}).status_code == 409
    login = client.post("/api/auth/login", json={"phone": phone, "password": "ValidPassword123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    status = client.get("/api/auth/phone/status", headers={"Authorization": "Bearer " + token})
    assert status.status_code == 200 and status.json()["verified"] is True


def test_expired_code_and_maximum_failed_attempts(monkeypatch):
    captured = fake_provider(monkeypatch)
    p = "+998901110042"
    assert client.post("/api/auth/otp/request", json={"phone": p}).status_code == 200
    with SessionLocal() as db:
        challenge = db.get(models.SmsChallenge, p)
        challenge.expires_at = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.post("/api/auth/register", json={
        "name": "Expired user", "phone": p, "password": "ValidPassword123",
        "otp_code": captured[p]
    }).status_code == 400
    p = "+998901110043"
    assert client.post("/api/auth/otp/request", json={"phone": p}).status_code == 200
    wrong = "111111" if captured[p] != "111111" else "222222"
    for i in range(5):
        response = client.post("/api/auth/register", json={
            "name": "Attempts user", "phone": p, "password": "ValidPassword123",
            "otp_code": wrong
        })
        assert response.status_code == 400, (i, response.text)
    blocked = client.post("/api/auth/register", json={
        "name": "Attempts user", "phone": p, "password": "ValidPassword123",
        "otp_code": captured[p]
    })
    assert blocked.status_code == 429


def test_existing_customer_can_verify_phone_after_login(monkeypatch):
    captured = fake_provider(monkeypatch)
    phone = "+998901110044"
    from app.security import hash_password
    with SessionLocal() as db:
        u = models.User(name="Existing", phone=phone,
                        password_hash=hash_password("ValidPassword123"),
                        role="customer", is_active=True)
        db.add(u);db.commit()
    token = client.post("/api/auth/login", json={
        "phone": phone, "password": "ValidPassword123"
    }).json()["access_token"]
    h = {"Authorization": "Bearer " + token}
    assert client.get("/api/auth/phone/status", headers=h).json()["verified"] is False
    assert client.post("/api/auth/phone/request", json={"phone": phone}, headers=h).status_code == 200
    assert client.post("/api/auth/phone/confirm", json={
        "phone": phone, "otp_code": captured[phone]
    }, headers=h).status_code == 200
    assert client.get("/api/auth/phone/status", headers=h).json()["verified"] is True


def test_sms_provider_missing_fails_closed(monkeypatch):
    monkeypatch.delenv("ALI_SMS_PROVIDER", raising=False)
    req = client.post("/api/auth/otp/request", json={"phone": "+998901110045"})
    assert req.status_code == 503
    assert "kod" not in req.json()
