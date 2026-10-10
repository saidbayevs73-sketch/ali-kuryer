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
        assert result.json()["mode"] == ("operator" if question.startswith("Operator") else "basic")
        assert expected in result.json()["reply"]


def test_family_dinner_suggestions_are_relevant_and_clearly_sample(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    result = client.post("/api/assistant/chat", json={
        "message": "Menga oilaviy kechki ovqat uchun 3 xil menyu tavsiya qil."
    })
    assert result.status_code == 200
    answer = result.json()
    assert answer["mode"] == "basic"
    assert "Uchta namunaviy" in answer["reply"]
    assert "tovuq" in answer["reply"]
    assert "haqiqiy menyusidan" in answer["reply"]


def test_quick_food_suggestions_have_useful_fallback(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_URL", raising=False)
    for message in ("Bugun nima yesam?", "Yengil ovqat", "Oqsilli ovqat"):
        result = client.post("/api/assistant/chat", json={"message": message})
        assert result.status_code == 200
        assert result.json()["mode"] == "basic"
        assert "oshxona" in result.json()["reply"] or "oshxonalar" in result.json()["reply"]


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



def _test_food_photo_base64() -> str:
    import base64
    from io import BytesIO
    from PIL import Image
    buffer = BytesIO()
    Image.new("RGB", (100, 100), "orange").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_muhammadali_operator_handoff_even_without_ai(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    result = client.post("/api/assistant/chat", json={
        "message": "Meni operatorga ulang, iltimos"
    })
    assert result.status_code == 200
    assert result.json()["mode"] == "operator"
    assert result.json()["action"] == "open_operator"
    assert result.json()["operator_url"].startswith("https://t.me/")


def test_image_calorie_analysis_calls_vision_model_without_storing_photo(monkeypatch):
    import httpx
    monkeypatch.setenv("AI_API_KEY", "test-secret-for-mock-only")
    monkeypatch.setenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    monkeypatch.setenv("AI_MODEL", "gpt-4.1-mini")
    seen = {}
    async def mock_post(self, url, **kwargs):
        seen.update(kwargs["json"])
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "choices": [{"message": {"content": "Ko‘rinishidan 300–450 kkal, taxminiy."}}]
        })
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    response = client.post("/api/assistant/chat", json={
        "message": "Bu taom nechta kaloriya?",
        "image_base64": _test_food_photo_base64()
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["mode"] == "ai"
    assert result["image_analyzed"] is True
    assert "300" in result["reply"]
    content = seen["messages"][1]["content"]
    assert isinstance(content, list) and content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert len(seen["messages"]) == 2


def test_image_when_key_rejected_does_not_invent_calories(monkeypatch):
    import httpx
    monkeypatch.setenv("AI_API_KEY", "test-invalid")
    monkeypatch.setenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")
    async def rejected(self, url, **kwargs):
        return httpx.Response(401, request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx.AsyncClient, "post", rejected)
    response = client.post("/api/assistant/chat", json={
        "message": "Rasmdagi taomning kaloriyasi qancha?",
        "image_base64": _test_food_photo_base64()
    })
    assert response.status_code == 200
    assert response.json()["mode"] == "basic"
    assert response.json()["image_analyzed"] is False
    assert "tahlil qila olmayapti" in response.json()["reply"]


def test_large_phone_camera_photo_resizes_instead_of_rejecting():
    # A common 4080 × 3060 mobile photo exceeds the old 12-million-pixel limit.
    import base64
    from io import BytesIO
    from PIL import Image
    from app.routers.customer_experience import _prepare_food_image
    buf = BytesIO()
    Image.new("RGB", (4080, 3060), (181, 114, 49)).save(
        buf, format="JPEG", quality=65
    )
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    compressed = _prepare_food_image(encoded)
    assert compressed.startswith("data:image/jpeg;base64,")
    thumbnail = Image.open(BytesIO(base64.b64decode(compressed.split(",", 1)[1])))
    assert max(thumbnail.size) <= 1280


def test_image_rejects_bad_and_oversized_uploads(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    for value in ("not a base64 data string!", "SGVsbG8gd29ybGQ="):
        res = client.post("/api/assistant/chat", json={
            "message": "Kaloriya qancha?",
            "image_base64": value
        })
        assert res.status_code == 400
    big = "A" * 6_000_001
    res = client.post("/api/assistant/chat", json={
        "message": "Kaloriya qancha?", "image_base64": big
    })
    assert res.status_code in (413, 422)


def test_photo_is_not_required_for_normal_chat(monkeypatch):
    monkeypatch.delenv("AI_API_KEY", raising=False)
    response = client.post("/api/assistant/chat", json={"message":"Yengil ovqat"})
    assert response.status_code == 200
    assert response.json()["mode"] == "basic"


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


def test_ai_quota_error_for_photo_is_not_fake_calorie_count(monkeypatch):
    import httpx
    monkeypatch.setenv("AI_API_KEY","mock-only-test-credential")
    monkeypatch.setenv("AI_API_URL","https://api.openai.com/v1/chat/completions")
    async def rejected(self, url, **kwargs):
        return httpx.Response(429,request=httpx.Request("POST",url),
            json={"error":{"code":"insufficient_quota","message":"private"}})
    monkeypatch.setattr(httpx.AsyncClient,"post",rejected)
    response=client.post("/api/assistant/chat",json={
        "message":"Rasmdagi taomda qancha kkal?",
        "image_base64":_test_food_photo_base64()
    })
    assert response.status_code==200
    result=response.json()
    assert result["mode"]=="basic"
    assert result["ai_issue"]=="quota"
    assert result["image_analyzed"] is False
    assert "Billing" in result["reply"]
    assert "tahlil qila olmayapti" in result["reply"]
    assert "private" not in result["reply"]


def test_ai_rate_limit_error_explains_retry(monkeypatch):
    import httpx
    monkeypatch.setenv("AI_API_KEY","mock-only-test-credential")
    monkeypatch.setenv("AI_API_URL","https://api.openai.com/v1/chat/completions")
    async def rejected(self,url,**kwargs):
        return httpx.Response(429,request=httpx.Request("POST",url),
            json={"error":{"code":"rate_limit_exceeded"}})
    monkeypatch.setattr(httpx.AsyncClient,"post",rejected)
    response=client.post("/api/assistant/chat",json={
        "message":"Menga bir yangi noodatiy ijodiy g‘oya haqida batafsil tushuntiring."
    })
    assert response.status_code==200
    result=response.json()
    assert result["mode"]=="basic"
    assert result["ai_issue"]=="rate_limit"
    assert "limit" in result["reply"]
