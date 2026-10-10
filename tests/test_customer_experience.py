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


def test_ai_greeting_works_without_provider_and_is_labeled_basic():
    response = client.post("/api/assistant/chat", json={"message": "salom"})
    assert response.status_code == 200
    assert "Assalomu alaykum" in response.json()["reply"]
    assert response.json()["mode"] == "basic"


def test_ai_has_honest_useful_fallback_without_provider():
    response = client.post("/api/assistant/chat", json={
        "message": "Bugun qaysi restoranlar yetkazib berayapti?"
    })
    assert response.status_code == 200
    assert response.json()["mode"] == "basic"
    assert "real" in response.json()["reply"] or "oshxonalar" in response.json()["reply"]


def test_ai_fallback_for_common_customer_questions(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    for question, expected in (
        ("Buyurtma holati qayerda?", "Buyurtmalar"),
        ("Telefonimda GPS manzilni qanday qo‘yaman?", "GPS"),
        ("Visa karta orqali to‘lov qilish", "CVV"),
        ("Operator bilan aloqa", "Telegram"),
    ):
        result = client.post("/api/assistant/chat", json={"message": question})
        assert result.status_code == 200
        assert result.json()["mode"] == "basic"
        assert expected in result.json()["reply"]


def test_ai_provider_401_does_not_leave_customer_without_help(monkeypatch):
    import httpx
    from app.routers import customer_experience
    monkeypatch.setenv("AI_API_KEY", "invalid-test-only")
    monkeypatch.setenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    async def reject(self, *args, **kwargs):
        req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        return httpx.Response(401, request=req, json={"error": "Unauthorized"})
    monkeypatch.setattr(httpx.AsyncClient, "post", reject)
    result = client.post("/api/assistant/chat", json={
        "message": "Buyurtmani qanday kuzataman?"
    })
    assert result.status_code == 200
    assert result.json()["mode"] == "basic"
    assert "Buyurtmalar" in result.json()["reply"]


def test_ai_provider_answer_stays_ai_when_successful(monkeypatch):
    import httpx
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    async def succeed(self, *args, **kwargs):
        req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        return httpx.Response(200, request=req,
            json={"choices": [{"message": {"content": "Yordam beraman."}}]})
    monkeypatch.setattr(httpx.AsyncClient, "post", succeed)
    response = client.post("/api/assistant/chat", json={"message": "Salatdan maslahat ber"})
    assert response.status_code == 200
    assert response.json()["reply"] == "Yordam beraman."
    assert response.json()["mode"] == "ai"


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


def test_phone_registration_login_and_customer_profile(monkeypatch):
    from app import otp
    # Test-only SMS transport, no real SMS is sent and no production OTP bypass.
    phone = "+998909876543"
    captured = {}
    monkeypatch.setenv("ALI_SMS_PROVIDER", "eskiz")
    monkeypatch.setenv("ESKIZ_API_TOKEN", "test-only-no-network")
    monkeypatch.setenv("ALI_SMS_SENDER", "TEST")
    def receive_test_sms(destination, code):
        captured["phone"] = destination
        captured["code"] = code
    monkeypatch.setattr(otp, "send_sms", receive_test_sms)
    sent = client.post("/api/auth/otp/request", json={"phone": phone})
    assert sent.status_code == 200, sent.text
    assert sent.json()["sent"] is True
    assert "code" not in sent.json()
    assert captured["phone"] == phone
    reg = client.post("/api/auth/register", json={
        "name":"Ali Test", "phone":phone, "password":"StrongTest123",
        "otp_code": captured["code"]
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
