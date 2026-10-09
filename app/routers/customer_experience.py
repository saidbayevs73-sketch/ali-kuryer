"""Customer-facing support chat and partner application API.

Sensitive AI credentials stay on the server. Applications are intentionally
visible only to authenticated administrators.
"""
import os
import re
import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_db, get_current_user

router = APIRouter(tags=["Customer experience"])
log = logging.getLogger(__name__)
_PHONE = re.compile(r"^\+998[0-9]{9}$")


class PartnerApplicationIn(BaseModel):
    kind: str
    full_name: str = Field(min_length=3, max_length=120)
    phone: str
    city: str = Field(min_length=2, max_length=100)
    detail: str = Field(default="", max_length=1000)
    privacy_accepted: bool
    website: str = Field(default="", max_length=100)  # bot honeypot

    @field_validator("kind")
    @classmethod
    def check_kind(cls, value):
        if value not in {"courier", "restaurant"}:
            raise ValueError("Ariza turi noto‘g‘ri")
        return value

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value):
        value = value.replace(" ", "").replace("-", "").strip()
        if not _PHONE.fullmatch(value):
            raise ValueError("Telefon +998XXXXXXXXX ko‘rinishida bo‘lishi kerak")
        return value


class AssistantChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=600)


@router.get("/api/customer-experience/config")
def public_config():
    # OAuth client IDs are public. Never put an API secret in this response.
    bot_url = os.getenv("ALI_HELP_BOT_URL", "https://t.me/AliKuryerBot")
    if not bot_url.startswith("https://t.me/"):
        bot_url = "https://t.me/AliKuryerBot"
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "ai_available": bool(os.getenv("AI_API_KEY") and os.getenv("AI_API_URL")),
        "bot_url": bot_url,
    }


@router.post("/api/partner-applications", status_code=201)
def create_application(data: PartnerApplicationIn, db: Session = Depends(get_db)):
    if not data.privacy_accepted:
        raise HTTPException(status_code=400, detail="Ma’lumotlarni qayta ishlashga rozilik kerak")
    # Do not reveal to bots that their honeypot submission was discarded.
    if data.website:
        return {"received": True}
    application = models.PartnerApplication(
        kind=data.kind,
        full_name=data.full_name.strip(),
        phone=data.phone,
        city=data.city.strip(),
        detail=data.detail.strip(),
        status="new",
    )
    db.add(application)
    db.commit()
    # Optional delivery to the existing private operator chat.
    # Do not make public submission dependent on Telegram availability.
    from app.routers import support_bot
    support_settings = support_bot.settings()
    if support_settings.get("token") and support_settings.get("group"):
        try:
            support_bot.tg_call(
                "sendMessage",
                chat_id=int(support_settings["group"]),
                text=(
                    f"Ali Kuryer hamkorlik arizasi №{application.id}\\n"
                    f"Turi: {application.kind}\\n"
                    f"Ism: {application.full_name}\\n"
                    f"Telefon: {application.phone}\\n"
                    f"Shahar: {application.city}\\n"
                    f"Izoh: {application.detail}"
                ),
            )
        except Exception:
            log.warning("Partner application notification failed; record saved", exc_info=False)
    return {"received": True, "application_id": application.id}


@router.get("/api/admin/partner-applications")
def list_applications(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.is_active or user.role != "admin":
        raise HTTPException(status_code=403, detail="Faqat administrator")
    items = db.query(models.PartnerApplication).order_by(
        models.PartnerApplication.id.desc()
    ).limit(100).all()
    return [{
        "id": x.id,
        "kind": x.kind,
        "full_name": x.full_name,
        "phone": x.phone,
        "city": x.city,
        "detail": x.detail,
        "status": x.status,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    } for x in items]


@router.post("/api/assistant/chat")
async def assistant_chat(data: AssistantChatIn):
    """OpenAI-compatible upstream. Respond honestly when not configured."""
    api_url = os.getenv("AI_API_URL", "").strip()
    key = os.getenv("AI_API_KEY", "").strip()
    if not api_url or not key:
        raise HTTPException(status_code=503, detail="AI xizmati hozircha ulanmagan")
    url = urlparse(api_url)
    if url.scheme != "https" or not url.hostname:
        raise HTTPException(status_code=503, detail="AI xizmati noto‘g‘ri sozlangan")
    system_message = (
        "Siz Ali Kuryer saytining Muhammadali nomli o‘zbek tilidagi "
        "virtual yordamchisisiz. Xushmuomala, ixcham, aniq javob bering. "
        "Buyurtma statusi, haqiqiy narx yoki restoran mavjudligini uydirmang. "
        "Maxfiy ma’lumot va karta raqamlarini so‘ramang. "
        "Mijozga ovqat tanlash, buyurtma tartibi, hamkorlik va kuryer "
        "bo‘lish bo‘yicha yordam bering. Operatorga murojaatni "
        "https://t.me/AliKuryerBot manziliga yo‘naltiring. "
        "Tibbiy maslahat yoki kafolatlangan yetkazish va’dasini bermang."
    )
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            response = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": data.message},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            payload = response.json()
        answer = payload["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("empty response")
        return {"reply": answer[:2200]}
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="AI xizmati vaqtincha javob bermadi")
