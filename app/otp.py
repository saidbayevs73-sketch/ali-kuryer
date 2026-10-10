"""Ali Kuryer SMS OTP: production fail-closed, rate limited and never logged.

The server never returns the OTP in API responses. Do not enable SMS delivery
until an authorized SMS provider has been configured via Render secrets.
"""
import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import DATABASE_URL

log = logging.getLogger(__name__)
PHONE_RE = re.compile(r"^\+998\d{9}$")
CODE_RE = re.compile(r"^\d{6}$")
LIFETIME = timedelta(minutes=5)
COOLDOWN = timedelta(seconds=60)
MAX_SENDS_PER_DAY = 5
MAX_TRIES = 5


def is_production():
    return settings.ENVIRONMENT.lower() == "production" or os.getenv("RENDER", "").lower() in {"true", "1", "yes"}


def require_otp_ready():
    if is_production() and not DATABASE_URL.startswith("postgresql"):
        raise HTTPException(503, "SMS tasdiqlash uchun doimiy PostgreSQL bazasi hali ulanmagan")
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 24:
        if is_production():
            raise HTTPException(503, "SMS tasdiqlash serverining maxfiy kaliti sozlanmagan")
    if os.getenv("ALI_SMS_PROVIDER", "").lower() != "eskiz":
        raise HTTPException(503, "SMS jo‘natish xizmati hali ulanmagan")
    if not (os.getenv("ESKIZ_API_TOKEN") or (os.getenv("ESKIZ_EMAIL") and os.getenv("ESKIZ_PASSWORD"))):
        raise HTTPException(503, "SMS yuborish hisobiga ulanish ma’lumotlari kiritilmagan")
    if not os.getenv("ALI_SMS_SENDER", "").strip():
        raise HTTPException(503, "SMS jo‘natuvchi nomi sozlanmagan")


def digest(phone: str, nonce: str, code: str) -> str:
    secret = settings.SECRET_KEY
    if not secret:
        raise HTTPException(503, "SMS tekshiruvi sozlanmagan")
    return hmac.new(secret.encode("utf-8"), f"sms:registration:{phone}:{nonce}:{code}".encode(), hashlib.sha256).hexdigest()


def send_sms(phone: str, code: str):
    """Eskiz gateway; never expose a token, code or recipient to the logs."""
    require_otp_ready()
    token = os.getenv("ESKIZ_API_TOKEN", "")
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        if not token:
            login = client.post(
                "https://notify.eskiz.uz/api/auth/login",
                data={"email": os.environ["ESKIZ_EMAIL"], "password": os.environ["ESKIZ_PASSWORD"]}
            )
            login.raise_for_status()
            token = login.json().get("data", {}).get("token", "")
            if not token:
                raise RuntimeError("Eskiz authorization did not return a token")
        reply = client.post(
            "https://notify.eskiz.uz/api/message/sms/send",
            headers={"Authorization": "Bearer " + token},
            data={
                "mobile_phone": phone[1:],
                "message": f"Ali Kuryer tasdiqlash kodi: {code}. Kodni hech kimga bermang.",
                "from": os.environ["ALI_SMS_SENDER"],
            },
        )
        reply.raise_for_status()


def validate_phone(phone: str):
    if not PHONE_RE.fullmatch(phone):
        raise HTTPException(422, "Telefon +998XXXXXXXXX shaklida bo‘lsin")


def request_otp(db: Session, phone: str):
    validate_phone(phone)
    require_otp_ready()
    now = datetime.utcnow()
    challenge = db.query(models.SmsChallenge).filter_by(phone=phone).with_for_update().first()
    if challenge is not None:
        if challenge.sent_at and now - challenge.sent_at < COOLDOWN:
            raise HTTPException(429, "Yangi kodni 60 soniyadan keyin so‘rang")
        if not challenge.window_start or now - challenge.window_start >= timedelta(days=1):
            challenge.window_start = now
            challenge.sent_today = 0
        if challenge.sent_today >= MAX_SENDS_PER_DAY:
            raise HTTPException(429, "Bu raqam uchun kunlik SMS limiti tugagan")
    else:
        challenge = models.SmsChallenge(phone=phone, window_start=now, sent_today=0)
        db.add(challenge)

    code = f"{secrets.randbelow(1000000):06d}"
    nonce = secrets.token_hex(16)
    try:
        send_sms(phone, code)
    except (httpx.HTTPError, RuntimeError, KeyError, ValueError):
        db.rollback()
        log.warning("Ali Kuryer SMS gateway refused or failed to accept a verification request")
        raise HTTPException(503, "SMS hozircha jo‘natilmadi. Keyinroq urinib ko‘ring") from None

    challenge.code_digest = digest(phone, nonce, code)
    challenge.nonce = nonce
    challenge.expires_at = now + LIFETIME
    challenge.sent_at = now
    challenge.attempts = 0
    challenge.sent_today = (challenge.sent_today or 0) + 1
    db.commit()
    return {"sent": True, "expires_in_seconds": 300, "retry_after_seconds": 60}


def consume_otp(db: Session, phone: str, code: str):
    validate_phone(phone)
    if not CODE_RE.fullmatch(code):
        raise HTTPException(422, "6 xonali SMS kodini kiriting")
    challenge = db.query(models.SmsChallenge).filter_by(phone=phone).with_for_update().first()
    now = datetime.utcnow()
    if challenge is None or challenge.expires_at is None or challenge.expires_at <= now:
        raise HTTPException(400, "SMS kodi eskirgan. Yangisini so‘rang")
    if challenge.attempts >= MAX_TRIES:
        raise HTTPException(429, "Urinishlar limiti tugagan. Yangi SMS kodini so‘rang")
    supplied = digest(phone, challenge.nonce, code)
    if not hmac.compare_digest(supplied, challenge.code_digest):
        challenge.attempts += 1
        db.commit()
        raise HTTPException(400, "Tasdiqlash kodi noto‘g‘ri")
    # Keep the daily send counter even after consuming the code.
    challenge.code_digest = None
    challenge.nonce = None
    challenge.expires_at = None
    db.flush()


def mark_verified(db: Session, phone: str, user_id: int):
    verified = db.get(models.VerifiedPhone, phone)
    if verified is not None and verified.user_id != user_id:
        raise HTTPException(409, "Bu raqam boshqa hisobda tasdiqlangan")
    if verified is None:
        db.add(models.VerifiedPhone(phone=phone, user_id=user_id))
