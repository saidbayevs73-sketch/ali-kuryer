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



def test_customer_auth_options_are_honest_without_sms_or_telegram(monkeypatch):
    from fastapi import HTTPException
    from app import otp, telegram_login
    monkeypatch.setattr(otp, "require_otp_ready",
                        lambda: (_ for _ in ()).throw(HTTPException(503, "unconfigured")))
    monkeypatch.setattr(telegram_login, "service_ready", lambda: False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    result = client.get("/api/auth/options")
    assert result.status_code == 200
    data = result.json()
    assert data["sms_registration"] is False
    assert data["sms_verification"] is False
    assert data["telegram_login"] is False
    assert data["google_login"] is False
    assert data["password_login"] is True
    assert "SMS" in data["message"]
    assert "unconfigured" not in result.text
    assert "SECRET_KEY" not in result.text
    assert "CLIENT_SECRET" not in result.text


def test_customer_auth_options_report_configuration_readiness(monkeypatch):
    from app import otp, telegram_login
    monkeypatch.setattr(otp, "require_otp_ready", lambda: None)
    monkeypatch.setattr(telegram_login, "service_ready", lambda: True)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-public-client-id.apps.googleusercontent.com")
    result = client.get("/api/auth/options")
    assert result.status_code == 200
    data = result.json()
    assert data["sms_registration"] is True
    assert data["telegram_login"] is True
    assert data["google_login"] is True
    assert "test-public-client-id" not in result.text


def test_username_signup_off_until_persistent_database_and_explicit_activation(monkeypatch):
    monkeypatch.delenv("ALI_USERNAME_LOGIN_ENABLED", raising=False)
    assert client.get("/api/auth/username/status").json()["available"] is False
    body = {
        "name": "Yangi mijoz", "username": "mijoz_registration_a",
        "password": "MijozStrongPassword123!", "accepted_privacy": True,
    }
    result = client.post("/api/auth/username/register", json=body)
    assert result.status_code == 503
    with SessionLocal() as db:
        assert db.get(models.UsernameIdentity, "mijoz_registration_a") is None


def test_username_signup_creates_unverified_customer_and_cabinet(monkeypatch):
    monkeypatch.setenv("ALI_USERNAME_LOGIN_ENABLED", "1")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("RENDER", raising=False)
    body = {
        "name": "Yangi sinov xaridor", "username": "mijoz_login_test_b",
        "password": "MijozStrongPassword123!", "accepted_privacy": True,
    }
    created = client.post("/api/auth/username/register", json=body)
    assert created.status_code == 201, created.text
    assert created.json()["phone_verified"] is False
    assert client.post("/api/auth/username/register", json=body).status_code == 409
    assert client.post("/api/auth/username/login", json={
        "username": body["username"], "password": "badpassword",
    }).status_code == 401
    login = client.post("/api/auth/username/login", json={
        "username": body["username"], "password": body["password"],
    })
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    details = client.get("/api/auth/me",
        headers={"Authorization": "Bearer " + token})
    assert details.status_code == 200
    assert details.json()["role"] == "customer"
    assert details.json()["phone"] is None
    with SessionLocal() as db:
        binding = db.get(models.UsernameIdentity, body["username"])
        assert binding is not None
        assert db.get(models.VerifiedPhone, "+998901112233") is None
        created_user = db.get(models.User, binding.user_id)
        assert created_user.role == "customer"
        assert created_user.password_hash != body["password"]


def test_username_signup_never_accepts_reserved_name_or_unconfirmed_privacy(monkeypatch):
    monkeypatch.setenv("ALI_USERNAME_LOGIN_ENABLED", "1")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.delenv("RENDER", raising=False)
    body = {
        "name":"Tester", "username":"admin",
        "password":"StrongExamplePassword45!", "accepted_privacy": True
    }
    assert client.post("/api/auth/username/register", json=body).status_code == 422
    assert client.post("/api/auth/username/register", json={
        **body, "username":"new_test_user", "accepted_privacy":False
    }).status_code == 422
    assert client.post("/api/auth/username/register", json={
        **body, "username":"ünicode_name"
    }).status_code == 422



def test_admin_username_login_requires_real_admin_password_not_admin_admin(monkeypatch):
    from app import security
    monkeypatch.setenv("ADMIN_PHONE", "+998901290777")
    monkeypatch.delenv("ALI_ADMIN_RESET_REQUEST_ID", raising=False)
    password = "Safe-Temporary-Admin-Password987!"
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(phone="+998901290777").first()
        if user is None:
            user = models.User(name="Staff admin test",
                phone="+998901290777", password_hash=security.hash_password(password),
                role="admin", is_active=True)
            db.add(user)
        else:
            user.role="admin"
            user.is_active=True
            user.password_hash=security.hash_password(password)
        db.commit()
    assert client.post("/api/auth/admin/login",
        json={"username":"admin","password":"admin"}).status_code == 401
    assert client.post("/api/auth/admin/login",
        json={"username":"other","password":password}).status_code == 401
    good = client.post("/api/auth/admin/login",
        json={"username":"admin","password":password})
    assert good.status_code == 200, good.text
    token = good.json()["access_token"]
    assert good.json()["role"] == "admin"
    assert client.get("/api/v1/admin/support/threads",
        headers={"Authorization":"Bearer "+token}).status_code == 200
    assert client.post("/api/auth/admin/change-password",
        headers={"Authorization":"Bearer "+token},
        json={"current_password":"bad", "new_password":"Other-Strong-Admin-Password543!"}).status_code == 401
    assert client.post("/api/auth/admin/change-password",
        headers={"Authorization":"Bearer "+token},
        json={"current_password":password, "new_password":"admin"}).status_code == 422
    update=client.post("/api/auth/admin/change-password",
        headers={"Authorization":"Bearer "+token},
        json={"current_password":password,
              "new_password":"Other-Strong-Admin-Password543!"})
    assert update.status_code == 200, update.text
    # Changing password immediately revokes even unexpired admin JWTs.
    assert client.get("/api/v1/admin/support/threads",
        headers={"Authorization":"Bearer "+token}).status_code == 401
    assert client.post("/api/auth/admin/login",
        json={"username":"admin","password":password}).status_code == 401
    relog = client.post("/api/auth/admin/login",
        json={"username":"admin","password":"Other-Strong-Admin-Password543!"})
    assert relog.status_code == 200
    assert relog.json()["role"] == "admin"


def test_one_time_admin_recovery_keeps_user_and_prevents_replay(monkeypatch):
    from app.bootstrap import maybe_reset_existing_admin
    from app import security
    phone = "+998901290778"
    newpassword = "Secure-New-Admin-Recovery-555!"
    nonce = "OwnerRecoverOnce_20261010_BlockedReplay456"
    monkeypatch.setenv("ALI_ADMIN_RESET_REQUEST_ID", nonce)
    monkeypatch.setenv("ALI_ADMIN_RESET_PASSWORD", newpassword)
    with SessionLocal() as db:
        admin=db.query(models.User).filter_by(phone=phone).first()
        if admin is None:
            admin=models.User(name="Admin recovery test",
                phone=phone, password_hash=security.hash_password("Previous-Strong-Admin-Password123!"),
                role="admin",is_active=True)
            db.add(admin)
            db.commit()
        else:
            admin.password_hash=security.hash_password("Previous-Strong-Admin-Password123!")
            db.commit()
        maybe_reset_existing_admin(db, admin)
        assert security.verify_password(newpassword, admin.password_hash)
        admin.password_hash=security.hash_password("Changed-Within-Admin-Panel-234!")
        db.commit()
        maybe_reset_existing_admin(db, admin)
        assert security.verify_password("Changed-Within-Admin-Panel-234!", admin.password_hash)
        assert not security.verify_password(newpassword, admin.password_hash)
    monkeypatch.delenv("ALI_ADMIN_RESET_REQUEST_ID")
    monkeypatch.delenv("ALI_ADMIN_RESET_PASSWORD")


def test_customer_token_cannot_change_admin_password(monkeypatch):
    from app import security
    phone="+998901290779"
    with SessionLocal() as db:
        user=db.query(models.User).filter_by(phone=phone).first()
        if user is None:
            user=models.User(name="Customer no admin access",phone=phone,
                password_hash=security.hash_password("CustomerStrongPassword99!"),
                role="customer",is_active=True)
            db.add(user)
            db.commit()
        else:
            user.role="customer"
            db.commit()
        token=security.create_access_token({"sub":str(user.id),"role":"customer"})
    r=client.post("/api/auth/admin/change-password",
       headers={"Authorization":"Bearer "+token},
       json={"current_password":"CustomerStrongPassword99!",
             "new_password":"NewStrongAdminPassword456!"})
    assert r.status_code == 403
