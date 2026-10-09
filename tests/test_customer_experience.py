"""Customer feature smoke tests, no real Google or AI API calls."""
import os

os.environ["DATABASE_URL"] = "sqlite:////tmp/ali_kuryer_ci_customer.db"
os.environ["SECRET_KEY"] = "only-for-regression-tests"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("AI_API_KEY", None)
os.environ.pop("GOOGLE_CLIENT_ID", None)

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_public_site_assets_and_legal_notices():
    for url in (
        "/", "/site-assets/customer.css", "/site-assets/customer.js",
        "/legal/privacy.html", "/legal/offer.html",
    ):
        assert client.get(url).status_code == 200


def test_config_exposes_no_server_secret():
    response = client.get("/api/customer-experience/config")
    assert response.status_code == 200
    assert response.json()["google_client_id"] == ""
    assert response.json()["ai_available"] is False
    assert response.json()["bot_url"].startswith("https://t.me/")


def test_ai_requires_private_provider_configuration():
    response = client.post("/api/assistant/chat", json={"message":"Assalomu alaykum"})
    assert response.status_code == 503


def test_partner_requires_consent_and_protects_admin_listing():
    payload = {
        "kind":"courier", "full_name":"Akmal Test", "phone":"+998901234567",
        "city":"Namangan", "detail":"Velosiped", "privacy_accepted":False,
    }
    assert client.post("/api/partner-applications", json=payload).status_code == 400
    payload["privacy_accepted"] = True
    data = client.post("/api/partner-applications", json=payload)
    assert data.status_code == 201, data.text
    assert data.json()["received"] is True
    assert client.get("/api/admin/partner-applications").status_code == 401


def test_google_signin_not_faked_when_unconfigured():
    result = client.post("/api/auth/google", json={"credential":"fake"})
    assert result.status_code == 503


def test_phone_registration_login_and_customer_profile():
    phone = "+998909876543"
    reg = client.post("/api/auth/register", json={
        "name":"Ali Test", "phone":phone, "password":"StrongTest123"
    })
    assert reg.status_code == 201, reg.text
    login = client.post("/api/auth/login", json={
        "phone":phone, "password":"StrongTest123"
    })
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    profile = client.get("/api/auth/me", headers={"Authorization":"Bearer "+token})
    assert profile.status_code == 200
    assert profile.json()["name"] == "Ali Test"
