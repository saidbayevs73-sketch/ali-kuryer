"""Allowlisted, durable Super Admin configuration for Ali Kuryer.

Only owner/admin tokens can change settings. Never store passwords, SMS keys,
raw HTML, JavaScript, arbitrary CSS, or third-party credentials here.
"""
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

from app.database import Base, DATABASE_URL, SessionLocal
from app.dependencies import get_current_user, get_db

router = APIRouter(tags=["Super Admin"])

# Safe defaults preserve existing behavior until the owner changes it.
DEFAULTS = {
    "customer_password_login": True,
    "customer_username_login": True,
    "customer_sms": True,
    "customer_firebase_phone": True,
    "customer_google_login": True,
    "customer_telegram_login": True,
    "courier_login": True,
    "restaurant_login": True,
    "site_accent": "#ef4c38",
    "site_notice": "",
    "courier_accent": "#e50914",
    "courier_notice": "",
    "restaurant_accent": "#e50914",
    "restaurant_notice": "",
}
AUTH_KEYS = frozenset(k for k, v in DEFAULTS.items() if isinstance(v, bool))
COLOR_KEYS = frozenset(k for k in DEFAULTS if k.endswith("_accent"))
TEXT_KEYS = frozenset(k for k in DEFAULTS if k.endswith("_notice"))
COLOR_RE = re.compile(r"^#[a-fA-F0-9]{6}$")


class AdminConfiguration(Base):
    __tablename__ = "admin_configuration"
    key = Column(String(80), primary_key=True)
    value = Column(String(600), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AdminConfigAudit(Base):
    __tablename__ = "admin_configuration_audit"
    id = Column(Integer, primary_key=True)
    key = Column(String(80), nullable=False)
    before_value = Column(String(600), nullable=False)
    after_value = Column(String(600), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ConfigChanges(BaseModel):
    # Validated again per key; extra keys and arbitrarily nested objects denied.
    changes: dict[str, bool | str] = Field(min_length=1, max_length=20)


def read_settings(db: Session) -> dict:
    data = dict(DEFAULTS)
    for row in db.query(AdminConfiguration).all():
        if row.key not in DEFAULTS:
            continue
        if row.key in AUTH_KEYS:
            data[row.key] = row.value == "true"
        else:
            data[row.key] = row.value
    return data


def enabled(key: str) -> bool:
    """Server-side enforcement, not just a client-side hidden button."""
    if key not in AUTH_KEYS:
        raise ValueError("Unknown feature flag")
    with SessionLocal() as db:
        return bool(read_settings(db)[key])


def require_enabled(key: str) -> None:
    if not enabled(key):
        raise HTTPException(403, "Bu kirish usuli admin tomonidan vaqtincha o‘chirilgan")


def require_admin(user=Depends(get_current_user)):
    if user.role != "admin" or not user.is_active:
        raise HTTPException(403, "Faqat Super Admin")
    return user


def validate_change(key: str, value):
    if key not in DEFAULTS:
        raise HTTPException(422, "Noma’lum sozlama: " + key)
    if key in AUTH_KEYS:
        if type(value) is not bool:
            raise HTTPException(422, key + ": true/false bo‘lishi shart")
        return value
    if not isinstance(value, str):
        raise HTTPException(422, key + ": matn bo‘lishi kerak")
    if key in COLOR_KEYS:
        if not COLOR_RE.fullmatch(value):
            raise HTTPException(422, key + ": #RRGGBB formatini kiriting")
        return value.lower()
    if key in TEXT_KEYS:
        if len(value) > 250 or "\x00" in value or "<" in value or ">" in value:
            raise HTTPException(422, key + ": 250 belgigacha oddiy matn kiriting")
        return value.strip()
    raise HTTPException(422, "Sozlama qo‘llab-quvvatlanmaydi")


def _durable_store_ready():
    if os.getenv("RENDER", "").lower() in ("true", "1", "yes"):
        # Prevent lost changes on Render ephemeral SQLite instances.
        if DATABASE_URL.startswith("sqlite") and not DATABASE_URL.startswith("sqlite:////var/data/"):
            raise HTTPException(503, "Sozlamalarni saqlash uchun doimiy Render disk yoki PostgreSQL kerak")


def _sanitized(data):
    return {
        "customer": {k: v for k, v in data.items() if k.startswith("customer_")},
        "courier": {k: v for k, v in data.items() if k.startswith("courier_")},
        "restaurant": {k: v for k, v in data.items() if k.startswith("restaurant_")},
        "site": {k: v for k, v in data.items() if k.startswith("site_")},
    }


@router.get("/api/control-center/public")
def public_controls(db: Session = Depends(get_db)):
    """Safe config for web and mobile consumers; never expose credentials."""
    from fastapi.responses import JSONResponse
    response = JSONResponse({"settings": _sanitized(read_settings(db))})
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/api/admin/control-center")
def admin_controls(db: Session = Depends(get_db), user=Depends(require_admin)):
    return {
        "settings": read_settings(db),
        "login": "admin",
        "password_change_endpoint": "/api/auth/admin/change-password",
        "secrets_editable_here": False,
        "message": "Kirish kodlari va SMS kalitlari oshkor qilinmaydi. Faqat parametrlar boshqariladi.",
    }


@router.post("/api/admin/control-center")
def update_controls(body: ConfigChanges,
                    db: Session = Depends(get_db),
                    user=Depends(require_admin)):
    _durable_store_ready()
    incoming = {key: validate_change(key, val) for key, val in body.changes.items()}
    original = read_settings(db)
    merged = {**original, **incoming}
    # Preserve access for *existing* customers, not just new OTP registrations.
    # The Eskiz OTP endpoint signs up/verifies phones but is not a general
    # passwordless login mechanism; enabling it alone cannot replace login.
    if not merged["customer_password_login"]:
        persistent = DATABASE_URL.startswith("postgresql") or not (
            os.getenv("ENVIRONMENT") == "production" or
            os.getenv("RENDER", "").lower() in ("true", "1", "yes")
        )
        other_ready = (
            (merged["customer_username_login"] and persistent
             and os.getenv("ALI_USERNAME_LOGIN_ENABLED") == "1")
            or (merged["customer_google_login"] and bool(os.getenv("GOOGLE_CLIENT_ID")))
            or (merged["customer_telegram_login"] and persistent
                and os.getenv("TELEGRAM_LOGIN_ENABLED") == "1"
                and bool(os.getenv("TELEGRAM_LOGIN_CLIENT_ID"))
                and bool(os.getenv("TELEGRAM_LOGIN_CLIENT_SECRET")))
            or (merged["customer_firebase_phone"] and DATABASE_URL.startswith("postgresql")
                and os.getenv("FIREBASE_PHONE_ENABLED") == "1"
                and os.getenv("FIREBASE_PROJECT_ID") == "ali-kuryer")
        )
        if not other_ready:
            raise HTTPException(422, "Telefon+parolni o‘chirishdan oldin boshqa ishlaydigan mijoz kirish usulini sozlang")
    # Do not remove every supported customer sign-in method by accident.
    if not any(merged[k] for k in (
        "customer_password_login", "customer_username_login",
        "customer_sms", "customer_firebase_phone",
        "customer_google_login", "customer_telegram_login"
    )):
        raise HTTPException(422, "Mijozlar uchun kamida bitta kirish usuli ochiq qolsin")

    changed = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        for key, value in incoming.items():
            if original[key] == value:
                continue
            before = original[key]
            encoded = ("true" if value else "false") if key in AUTH_KEYS else value
            row = db.get(AdminConfiguration, key)
            if row is None:
                row = AdminConfiguration(key=key, value=encoded)
                db.add(row)
            else:
                row.value = encoded
            row.updated_by = user.id
            row.updated_at = now
            db.add(AdminConfigAudit(
                key=key, before_value=str(before), after_value=str(value),
                actor_id=user.id, created_at=now,
            ))
            changed.append(key)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"settings": read_settings(db), "changed": changed}


@router.get("/api/admin/control-center/history")
def control_history(db: Session = Depends(get_db), user=Depends(require_admin)):
    records = db.query(AdminConfigAudit).order_by(
        AdminConfigAudit.id.desc()
    ).limit(40).all()
    return {"events": [
        {"key": row.key, "from": row.before_value, "to": row.after_value,
         "at": row.created_at.isoformat() if row.created_at else None}
        for row in records
    ]}
