"""Telegram OIDC customer sign-in tests; HTTPS to Telegram is mocked."""
import os
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:////tmp/ali_kuryer_ci_customer.db"
os.environ["SECRET_KEY"] = "only-for-regression-tests"
os.environ["ENVIRONMENT"] = "test"

from main import app
from app import models, telegram_login
from app.database import SessionLocal

client = TestClient(app, follow_redirects=False)
CLIENT_ID = "987654321"
CLIENT_SECRET = "test-secret-do-not-use-in-production"
DEVICE = "AbCdEfGh1234567890_-AbCdEfGh1234567890_-AbC"
assert len(DEVICE) == 43


def configure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_LOGIN_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("TELEGRAM_LOGIN_CLIENT_SECRET", CLIENT_SECRET)
    monkeypatch.setenv("TELEGRAM_LOGIN_ENABLED", "1")


def test_telegram_status_only_exposes_readiness(monkeypatch):
    monkeypatch.delenv("TELEGRAM_LOGIN_ENABLED", raising=False)
    result = client.get("/api/auth/telegram/status")
    assert result.status_code == 200
    assert result.json()["available"] is False
    assert "SMS" in result.json()["message"]
    assert "CLIENT_SECRET" not in result.text


def test_telegram_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_LOGIN_ENABLED", raising=False)
    result = client.post("/api/auth/telegram/start", json={"device_secret": DEVICE})
    assert result.status_code == 503


def test_start_has_pkce_phone_consent_and_no_secret_in_url(monkeypatch):
    configure(monkeypatch)
    result = client.post("/api/auth/telegram/start", json={"device_secret": DEVICE})
    assert result.status_code == 200, result.text
    url = result.json()["authorization_url"]
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.scheme == "https" and parsed.hostname == "oauth.telegram.org"
    assert qs["scope"] == ["openid profile phone"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["redirect_uri"] == [telegram_login.CALLBACK_URL]
    assert CLIENT_SECRET not in url
    assert "code_verifier" not in qs
    assert qs["nonce"]
    assert qs["state"]


def test_invalid_callback_and_ticket_are_rejected(monkeypatch):
    configure(monkeypatch)
    bad = client.get("/api/auth/telegram/callback", params={
        "state": "unknown", "code": "attacker"
    })
    assert bad.status_code == 400
    finish = client.post("/api/auth/telegram/finish", json={
        "ticket": "A" * 43, "device_secret": DEVICE
    })
    assert finish.status_code == 401


def test_telegram_consent_verified_phone_and_replay(monkeypatch):
    configure(monkeypatch)
    start = client.post("/api/auth/telegram/start", json={"device_secret": DEVICE})
    qs = parse_qs(urlparse(start.json()["authorization_url"]).query)
    state = qs["state"][0]
    nonce = qs["nonce"][0]
    phone = "+998909150789"
    sub = "telegram-test-oidc-verified-789"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id_token": "this-is-only-a-mocked-test-token"}

    monkeypatch.setattr(telegram_login.requests, "post", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr(telegram_login, "verify_telegram_id_token",
                        lambda raw, requested_nonce: {
                            "sub": sub, "name": "Telegram Mijoz",
                            "phone_number": phone, "phone_number_verified": True
                        } if requested_nonce == nonce else {})

    callback = client.get("/api/auth/telegram/callback", params={"state": state, "code": "mock-code"})
    assert callback.status_code == 303, callback.text
    link = urlparse(callback.headers["location"])
    assert link.scheme == "alikuryer" and link.hostname == "telegram-login"
    ticket = parse_qs(link.query)["ticket"][0]
    assert len(ticket) == 43

    wrong_device = client.post("/api/auth/telegram/finish", json={
        "ticket": ticket, "device_secret": "B" * 43
    })
    assert wrong_device.status_code == 401
    valid = client.post("/api/auth/telegram/finish", json={
        "ticket": ticket, "device_secret": DEVICE
    })
    assert valid.status_code == 200, valid.text
    assert valid.json()["phone"] == phone
    token = valid.json()["access_token"]
    profile = client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
    assert profile.status_code == 200
    assert profile.json()["phone"] == phone

    replay = client.post("/api/auth/telegram/finish", json={
        "ticket": ticket, "device_secret": DEVICE
    })
    assert replay.status_code == 401
    with SessionLocal() as db:
        user = db.query(models.User).filter_by(phone=phone).one()
        assert user.role == "customer"
        assert db.get(models.VerifiedPhone, phone).user_id == user.id
        assert db.get(models.TelegramIdentity, sub).user_id == user.id
