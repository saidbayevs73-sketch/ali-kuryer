"""Ali Kuryer Telegram Login: OIDC Authorization Code + PKCE + device-bound one-use ticket.

The Telegram OAuth client secret stays ONLY on Render. Android never receives it.
Phone numbers are accepted only when Telegram confirms verified and user consent.
"""
import base64
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import Literal

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, security
from app.database import DATABASE_URL, SessionLocal

router = APIRouter(prefix="/api/auth/telegram", tags=["Telegram Login"])
AUTH_URL = "https://oauth.telegram.org/auth"
TOKEN_URL = "https://oauth.telegram.org/token"
JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"
CALLBACK_URL = "https://ali-kuryer.onrender.com/api/auth/telegram/callback"
MOBILE_CALLBACK = "alikuryer://telegram-login"
# Browser callback ticket stays in the URL fragment (not sent in subsequent HTTP requests).
WEB_CALLBACK = "https://ali-kuryer.onrender.com/#ali-telegram-ticket="
MAX_AGE = timedelta(minutes=6)
APP_SECRET_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
UZ_PHONE_RE = re.compile(r"^\+998[0-9]{9}$")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def configured() -> bool:
    return bool(
        os.getenv("TELEGRAM_LOGIN_CLIENT_ID", "").strip().isdigit()
        and os.getenv("TELEGRAM_LOGIN_CLIENT_SECRET", "").strip()
        and os.getenv("TELEGRAM_LOGIN_ENABLED") == "1"
    )


def service_ready() -> bool:
    from app.control_center import enabled
    if not enabled("customer_telegram_login"):
        return False
    return configured() and not (
        os.getenv("RENDER", "").lower() in {"true", "1", "yes"}
        and not DATABASE_URL.startswith("postgresql")
    )


@router.get("/status")
def telegram_status():
    # Readiness only: never reveal provider secrets, database DSNs or credentials.
    return {
        "available": service_ready(),
        "message": ("Telegram orqali kirish tayyor."
                    if service_ready() else
                    "Telegram orqali kirish hozircha sozlanmoqda. "
                    "Ro‘yxatdan o‘tish uchun SMS yoki parolni tanlang."),
    }


def require_ready() -> None:
    from app.control_center import require_enabled
    require_enabled("customer_telegram_login")
    if not configured():
        raise HTTPException(503, "Telegram kirish hozircha sozlanmagan")
    if os.getenv("RENDER", "").lower() in {"true", "1", "yes"} and not DATABASE_URL.startswith("postgresql"):
        raise HTTPException(503, "Kirish uchun doimiy PostgreSQL bazasi kerak")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class TelegramStart(BaseModel):
    device_secret: str = Field(min_length=43, max_length=43)
    channel: Literal["app", "web"] = "app"


class TelegramFinish(BaseModel):
    ticket: str = Field(min_length=43, max_length=43)
    device_secret: str = Field(min_length=43, max_length=43)


@router.post("/start")
def start_telegram_login(data: TelegramStart, db: Session = Depends(get_db)):
    require_ready()
    if not APP_SECRET_RE.fullmatch(data.device_secret):
        raise HTTPException(422, "Ilova tasdiqlash kaliti noto‘g‘ri")
    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    if data.channel == "web":
        state = "web_" + state
    verifier = secrets.token_urlsafe(48)
    attempt = models.TelegramLoginAttempt(
        state=state,
        nonce=nonce,
        code_verifier=verifier,
        device_hash=digest(data.device_secret),
        status="pending",
    )
    db.add(attempt)
    db.commit()
    challenge = b64(hashlib.sha256(verifier.encode("ascii")).digest())
    params = {
        "client_id": os.environ["TELEGRAM_LOGIN_CLIENT_ID"].strip(),
        "redirect_uri": CALLBACK_URL,
        "response_type": "code",
        "scope": "openid profile phone",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return {"authorization_url": AUTH_URL + "?" + urlencode(params)}


def verify_telegram_id_token(raw: str, nonce: str) -> dict:
    """Only an RSA signature from Telegram JWKS is accepted."""
    try:
        header = jwt.get_unverified_header(raw)
        if header.get("alg") != "RS256" or not header.get("kid"):
            raise ValueError("unexpected alg")
        response = requests.get(JWKS_URL, timeout=7)
        response.raise_for_status()
        keys = response.json()["keys"]
        signing_key = next(
            key for key in keys if key.get("kid") == header["kid"]
            and key.get("kty") == "RSA" and key.get("use", "sig") == "sig"
        )
        claims = jwt.decode(
            raw, signing_key, algorithms=["RS256"],
            audience=os.environ["TELEGRAM_LOGIN_CLIENT_ID"].strip(),
            issuer="https://oauth.telegram.org",
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        if claims.get("nonce") != nonce:
            raise ValueError("nonce mismatch")
        now = datetime.utcnow().timestamp()
        issued = claims.get("iat")
        if not isinstance(issued, (int, float)) or issued > now + 30 or issued < now - 600:
            raise ValueError("stale Telegram token")
        return claims
    except Exception:
        # Never leak Telegram tokens, keys, or exceptions to the browser.
        raise HTTPException(401, "Telegram tasdiqlash ma’lumotlari yaroqsiz") from None


def simple_page(text: str) -> HTMLResponse:
    from html import escape
    return HTMLResponse(
        '<!doctype html><html lang="uz"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Ali Kuryer</title>'
        '<div style="font-family:sans-serif;max-width:420px;margin:50px auto;padding:22px">'
        '<h2>Ali Kuryer</h2><p>' + escape(text) +
        '</p><p>Ilovaga qaytib, qayta urinib ko‘ring.</p></div></html>',
        status_code=400,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/callback")
def telegram_callback(
    state: str = Query(default="", max_length=140),
    code: str = Query(default="", max_length=3000),
    error: str = Query(default="", max_length=120),
    db: Session = Depends(get_db),
):
    require_ready()
    attempt = db.query(models.TelegramLoginAttempt).filter_by(state=state).with_for_update().first()
    if (
        not attempt or attempt.status != "pending" or
        datetime.utcnow() - attempt.created_at > MAX_AGE
    ):
        return simple_page("Tasdiqlash muddati tugagan yoki avval ishlatilgan.")
    # Consume the state before contacting Telegram so a replay is rejected.
    attempt.status = "processing"
    db.commit()
    if error or not code:
        attempt.status = "failed"
        db.commit()
        return simple_page("Telegram orqali kirish bekor qilindi.")
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": CALLBACK_URL,
                "client_id": os.environ["TELEGRAM_LOGIN_CLIENT_ID"].strip(),
                "code_verifier": attempt.code_verifier,
            },
            auth=(os.environ["TELEGRAM_LOGIN_CLIENT_ID"].strip(),
                  os.environ["TELEGRAM_LOGIN_CLIENT_SECRET"].strip()),
            timeout=10,
        )
        response.raise_for_status()
        raw_token = response.json().get("id_token")
        if not isinstance(raw_token, str):
            raise ValueError("missing Telegram id_token")
        claims = verify_telegram_id_token(raw_token, attempt.nonce)
        phone = str(claims.get("phone_number", "")).strip()
        if phone.isdigit():
            phone = "+" + phone
        if not UZ_PHONE_RE.fullmatch(phone) or claims.get("phone_number_verified") is not True:
            attempt.status = "failed"
            db.commit()
            return simple_page(
                "Telefon raqami Telegram orqali ulashilmadi yoki tasdiqlanmadi. "
                "Kirishda telefon raqamini ulashishga rozilik bering."
            )
        sub = str(claims.get("sub", ""))
        if not sub or len(sub) > 160:
            raise ValueError("bad subject")
        ticket = secrets.token_urlsafe(32)
        attempt.telegram_sub = sub
        attempt.display_name = str(claims.get("name") or "Mijoz")[:150]
        attempt.verified_phone = phone
        attempt.ticket_hash = digest(ticket)
        attempt.status = "approved"
        db.commit()
        redirect = (WEB_CALLBACK + ticket) if state.startswith("web_") else (
            MOBILE_CALLBACK + "?" + urlencode({"ticket": ticket})
        )
        return RedirectResponse(redirect, status_code=303, headers={
            "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"
        })
    except Exception:
        db.rollback()
        attempt = db.get(models.TelegramLoginAttempt, state)
        if attempt:
            attempt.status = "failed"
            db.commit()
        return simple_page("Telegram bilan ulanishni yakunlab bo‘lmadi.")


@router.post("/finish")
def finish_telegram_login(data: TelegramFinish, db: Session = Depends(get_db)):
    require_ready()
    if not APP_SECRET_RE.fullmatch(data.device_secret) or not APP_SECRET_RE.fullmatch(data.ticket):
        raise HTTPException(422, "Tasdiqlash kodi noto‘g‘ri")
    attempt = db.query(models.TelegramLoginAttempt).filter_by(
        ticket_hash=digest(data.ticket)
    ).with_for_update().first()
    if (
        not attempt or attempt.status != "approved"
        or attempt.device_hash != digest(data.device_secret)
        or datetime.utcnow() - attempt.created_at > MAX_AGE
        or not attempt.telegram_sub or not attempt.verified_phone
    ):
        raise HTTPException(401, "Telegram kirishi muddati tugagan yoki mos kelmaydi")
    # Identity binding is one-to-one, and staff users are never acquired by Telegram login.
    identity = db.get(models.TelegramIdentity, attempt.telegram_sub)
    if identity:
        user = db.get(models.User, identity.user_id)
        if not user or not user.is_active or user.role != "customer":
            raise HTTPException(403, "Bu hisob orqali mijoz sifatida kirib bo‘lmaydi")
        if user.phone != attempt.verified_phone:
            raise HTTPException(409, "Telefon raqami oldingi tasdiqlangan hisobga mos emas")
    else:
        user = db.query(models.User).filter_by(phone=attempt.verified_phone).with_for_update().first()
        if user and (user.role != "customer" or not user.is_active):
            raise HTTPException(403, "Bu telefon boshqa turdagi hisobga tegishli")
        if not user:
            user = models.User(
                name=attempt.display_name or "Mijoz",
                phone=attempt.verified_phone,
                password_hash=None,
                role="customer",
                is_active=True,
            )
            db.add(user)
            db.flush()
        db.add(models.TelegramIdentity(telegram_sub=attempt.telegram_sub, user_id=user.id))
    proof = db.get(models.VerifiedPhone, attempt.verified_phone)
    if proof and proof.user_id != user.id:
        raise HTTPException(409, "Telefon boshqa hisobga bog‘langan")
    if not proof:
        db.add(models.VerifiedPhone(phone=attempt.verified_phone, user_id=user.id))
    attempt.status = "redeemed"
    attempt.redeemed_at = datetime.utcnow()
    # Do not retain token-exchange PKCE data after use.
    attempt.code_verifier = ""
    attempt.nonce = ""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Telegram hisobi band. Qayta urinib ko‘ring")
    return {
        "access_token": security.create_access_token({"sub": str(user.id), "role": "customer"}),
        "role": "customer",
        "token_type": "bearer",
        "phone": user.phone,
    }
