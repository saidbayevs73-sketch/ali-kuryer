"""Admin-managed public contacts, planned payments, and customer registry.

This module never processes bank cards or online payments. Admin requests
are authenticated, saved configuration excludes API credentials, and public
payment methods remain disabled until audited provider integrations exist.
"""
import os
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.orm import Session

from app import models
from app.database import DATABASE_URL
from app.dependencies import get_db, get_current_user

router = APIRouter(tags=["Platform settings"])
_PHONE = re.compile(r"^\+998\d{9}$")
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_TG = re.compile(r"^https://t\.me/[A-Za-z0-9_]{5,32}/?$")
_MERCHANT_ID = re.compile(r"^[A-Za-z0-9_.\-]{0,100}$")
PROVIDERS = ("click", "payme", "bank_card")


def require_admin(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role != "admin":
        raise HTTPException(status_code=403, detail="Faqat administrator")
    return user


def require_durable_admin_writes():
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production" or (
        os.getenv("RENDER", "").lower() in ("1", "true", "yes")
    )
    if is_production and not DATABASE_URL.startswith("postgresql"):
        raise HTTPException(
            status_code=503,
            detail="Doimiy PostgreSQL tekshirilmaguncha sozlamalarni saqlab bo‘lmaydi",
        )


class Contacts(BaseModel):
    model_config = ConfigDict(extra="forbid")
    support_phone: str = Field(default="", max_length=20)
    support_email: str = Field(default="", max_length=120)
    telegram_url: str = Field(default="", max_length=150)
    office_address: str = Field(default="", max_length=200)

    @field_validator("support_phone")
    @classmethod
    def check_phone(cls, value):
        value = value.strip()
        if value and not _PHONE.fullmatch(value):
            raise ValueError("Telefon +998XXXXXXXXX shaklida bo‘lsin")
        return value

    @field_validator("support_email")
    @classmethod
    def check_email(cls, value):
        value = value.strip()
        if value and not _EMAIL.fullmatch(value):
            raise ValueError("Email manzili noto‘g‘ri")
        return value

    @field_validator("telegram_url")
    @classmethod
    def check_telegram(cls, value):
        value = value.strip()
        if value and not _TG.fullmatch(value):
            raise ValueError("Telegram https://t.me/username shaklida bo‘lsin")
        return value

    @field_validator("office_address")
    @classmethod
    def check_address(cls, value):
        return value.strip()


class ProviderDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested_enabled: bool = False
    contract_signed: bool = False
    merchant_label: str = Field(default="", max_length=80)
    merchant_id: str = Field(default="", max_length=100)

    @field_validator("merchant_id")
    @classmethod
    def check_merchant_id(cls, value):
        value = value.strip()
        if not _MERCHANT_ID.fullmatch(value):
            raise ValueError("Faqat ochiq merchant ID. Maxfiy kalit yoki parolni kiritmang")
        return value

    @field_validator("merchant_label")
    @classmethod
    def check_label(cls, value):
        return value.strip()


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contacts: Contacts
    providers: dict[Literal["click", "payme", "bank_card"], ProviderDraft]

    @field_validator("providers")
    @classmethod
    def complete_providers(cls, value):
        if set(value) != set(PROVIDERS):
            raise ValueError("Click, Payme va bank kartasi uchun alohida sozlama kerak")
        return value


def get_settings(db):
    return db.get(models.PlatformSettings, 1)


def contacts_payload(record):
    return {
        "support_phone": record.support_phone if record else "",
        "support_email": record.support_email if record else "",
        "telegram_url": record.telegram_url if record else "",
        "office_address": record.office_address if record else "",
    }


def drafts_payload(record):
    raw = record.payment_preferences if record else {}
    raw = raw if isinstance(raw, dict) else {}
    result = {}
    for name in PROVIDERS:
        try:
            result[name] = ProviderDraft.model_validate(raw.get(name, {})).model_dump()
        except ValueError:
            result[name] = ProviderDraft().model_dump()
    return result


@router.get("/api/public/platform-config")
def public_settings(db: Session = Depends(get_db)):
    record = get_settings(db)
    # The only implemented checkout option is cash. No card collection forms
    # or payment links should become active by merely saving these drafts.
    return {
        "contacts": contacts_payload(record),
        "payment_methods": [
            {"id": "cash", "title": "Naqd pul", "available": True},
            {"id": "click", "title": "Click", "available": False},
            {"id": "payme", "title": "Payme", "available": False},
            {"id": "bank_card", "title": "Bank kartasi", "available": False},
        ],
        "saved_cards_available": False,
        "online_payments_available": False,
    }


@router.get("/api/admin/platform-config")
def admin_settings(db: Session = Depends(get_db), user=Depends(require_admin)):
    record = get_settings(db)
    return {
        "contacts": contacts_payload(record),
        "providers": drafts_payload(record),
        "online_payments_available": False,
        "warning": "Shartnoma va merchant ID saqlanishi to‘lov integratsiyasini yoqmaydi. API kalitlar faqat Render Secrets orqali.",
    }


@router.put("/api/admin/platform-config")
def save_admin_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    require_durable_admin_writes()
    record = get_settings(db)
    if record is None:
        record = models.PlatformSettings(id=1)
        db.add(record)
    record.support_phone = payload.contacts.support_phone
    record.support_email = payload.contacts.support_email
    record.telegram_url = payload.contacts.telegram_url
    record.office_address = payload.contacts.office_address
    # Only public merchant identifiers and setup state, never credentials.
    record.payment_preferences = {
        key: value.model_dump() for key, value in payload.providers.items()
    }
    record.updated_by_id = user.id
    db.commit()
    return admin_settings(db=db, user=user)


@router.get("/api/admin/customers")
def registered_customers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    require_durable_admin_writes()
    query = db.query(models.User).filter(models.User.role == "customer")
    total = query.count()
    users = query.order_by(models.User.id.desc()).offset(offset).limit(limit).all()
    # Never reveal password hashes, Google subject, OTP or tokens.
    return {
        "total": total, "offset": offset, "limit": limit,
        "customers": [{
            "id": x.id, "name": x.name, "phone": x.phone,
            "is_active": x.is_active,
            "registered_at": x.created_at.isoformat() if x.created_at else None,
        } for x in users],
    }


@router.get("/api/customer/saved-cards")
def saved_cards(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role != "customer":
        raise HTTPException(403, "Faqat mijoz hisobi")
    return {"cards": [], "available": False,
            "message": "Bank bilan tasdiqlangan xavfsiz karta tokenizatsiyasi hali ulanmagan"}


@router.post("/api/customer/saved-cards")
def add_card_unavailable(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role != "customer":
        raise HTTPException(403, "Faqat mijoz hisobi")
    raise HTTPException(503, "Karta qo‘shish bankning xavfsiz sahifasi ulanganidan keyin yoqiladi")
