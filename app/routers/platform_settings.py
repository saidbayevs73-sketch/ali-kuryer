"""Admin-managed public contacts, planned payments, and customer registry.

This module never processes bank cards or online payments. Admin requests
are authenticated, saved configuration excludes API credentials, and public
payment methods remain disabled until audited provider integrations exist.
"""
import os
import re
from typing import Literal
from datetime import datetime, timezone

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


# Payment support issues. No transactions, charges, refunds, or merchant
# settings are changed by these endpoints.
_PROVIDERS = {"click", "payme", "bank_card", "cash", "other"}
_CATEGORIES = {
    "payment_failed", "duplicate_charge", "refund_request",
    "provider_setup", "settlement", "other",
}
_ISSUE_STATUS = {"new", "investigating", "awaiting_provider", "resolved", "closed"}
_CARD_NUMBER = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SENSITIVE_TERMS = re.compile(
    r"\b(?:cvv|cvc|pin|parol|password|secret[_ -]?key|api[_ -]?key)\b",
    re.IGNORECASE,
)


def safe_ticket_text(text):
    text = str(text).strip()
    if _CARD_NUMBER.search(text) or _SENSITIVE_TERMS.search(text):
        raise ValueError("Karta raqami, CVV, PIN yoki maxfiy kalit kiritmang")
    return text


class PaymentIssueCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["click", "payme", "bank_card", "cash", "other"]
    category: Literal[
        "payment_failed", "duplicate_charge", "refund_request",
        "provider_setup", "settlement", "other",
    ]
    order_id: int | None = Field(default=None, gt=0)
    description: str = Field(min_length=8, max_length=500)

    @field_validator("description")
    @classmethod
    def check_description(cls, text):
        return safe_ticket_text(text)


class PaymentIssueUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["new", "investigating", "awaiting_provider", "resolved", "closed"]
    note: str = Field(min_length=5, max_length=800)
    assign_to_self: bool = False

    @field_validator("note")
    @classmethod
    def check_note(cls, text):
        return safe_ticket_text(text)


def payment_issue_dict(issue, include_private=False):
    data = {
        "id": issue.id,
        "order_id": issue.order_id,
        "provider": issue.provider,
        "category": issue.category,
        "description": issue.description,
        "status": issue.status,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
    }
    if include_private:
        data["customer_id"] = issue.customer_id
        data["assigned_admin_id"] = issue.assigned_admin_id
        data["resolution_note"] = issue.resolution_note
    return data


@router.post("/api/customer/payment-issues", status_code=201)
def report_payment_issue(
    payload: PaymentIssueCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if not user.is_active or user.role != "customer":
        raise HTTPException(403, "Faqat mijoz hisobidan xabar yuboring")
    require_durable_admin_writes()
    if payload.order_id is None:
        raise HTTPException(422, "Mijoz murojaati uchun buyurtma raqami talab qilinadi")
    order = db.get(models.Order, payload.order_id)
    if not order or order.customer_id != user.id:
        raise HTTPException(404, "Buyurtma topilmadi")
    # Avoid duplicate unresolved claims submitted by repeated taps.
    duplicate = db.query(models.PaymentSupportIssue).filter(
        models.PaymentSupportIssue.order_id == order.id,
        models.PaymentSupportIssue.customer_id == user.id,
        models.PaymentSupportIssue.category == payload.category,
        models.PaymentSupportIssue.status.in_(("new", "investigating", "awaiting_provider")),
    ).first()
    if duplicate:
        return payment_issue_dict(duplicate)
    issue = models.PaymentSupportIssue(
        provider=payload.provider, category=payload.category,
        order_id=order.id, customer_id=user.id,
        description=payload.description, status="new",
    )
    db.add(issue)
    db.flush()
    db.add(models.PaymentSupportAudit(
        issue_id=issue.id, actor_id=user.id, old_status=None,
        new_status="new", note="Mijoz murojaati",
    ))
    db.commit()
    db.refresh(issue)
    return payment_issue_dict(issue)


@router.get("/api/customer/payment-issues")
def my_payment_issues(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if not user.is_active or user.role != "customer":
        raise HTTPException(403, "Faqat mijoz hisobidan")
    require_durable_admin_writes()
    issues = db.query(models.PaymentSupportIssue).filter_by(
        customer_id=user.id
    ).order_by(models.PaymentSupportIssue.id.desc()).limit(50).all()
    return {"issues": [payment_issue_dict(item) for item in issues]}


@router.post("/api/admin/payment-issues", status_code=201)
def create_admin_payment_issue(
    payload: PaymentIssueCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    require_durable_admin_writes()
    if payload.order_id and not db.get(models.Order, payload.order_id):
        raise HTTPException(404, "Buyurtma topilmadi")
    issue = models.PaymentSupportIssue(
        provider=payload.provider, category=payload.category,
        order_id=payload.order_id, description=payload.description,
        assigned_admin_id=user.id, status="new",
    )
    db.add(issue)
    db.flush()
    db.add(models.PaymentSupportAudit(
        issue_id=issue.id, actor_id=user.id, old_status=None,
        new_status="new", note="Administrator murojaati",
    ))
    db.commit()
    db.refresh(issue)
    return payment_issue_dict(issue, include_private=True)


@router.get("/api/admin/payment-issues")
def list_admin_payment_issues(
    status: Literal["new", "investigating", "awaiting_provider", "resolved", "closed"] | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    require_durable_admin_writes()
    query = db.query(models.PaymentSupportIssue)
    if status:
        query = query.filter_by(status=status)
    return {
        "total": query.count(), "offset": offset, "limit": limit,
        "issues": [
            payment_issue_dict(item, include_private=True)
            for item in query.order_by(models.PaymentSupportIssue.id.desc()).offset(offset).limit(limit)
        ],
    }


@router.patch("/api/admin/payment-issues/{issue_id}")
def update_admin_payment_issue(
    issue_id: int, payload: PaymentIssueUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    require_durable_admin_writes()
    issue = db.query(models.PaymentSupportIssue).filter_by(id=issue_id).with_for_update().first()
    if not issue:
        raise HTTPException(404, "Murojaat topilmadi")
    if payload.status == "resolved" and len(payload.note) < 10:
        raise HTTPException(422, "Hal qilindi holati uchun sababni batafsil yozing")
    # This is a SUPPORT TICKET status only. Never mark an order paid,
    # call a payment provider, or imply a refund was actually sent.
    prior = issue.status
    issue.status = payload.status
    issue.resolution_note = payload.note
    if payload.assign_to_self:
        issue.assigned_admin_id = user.id
    db.add(models.PaymentSupportAudit(
        issue_id=issue.id, actor_id=user.id,
        old_status=prior, new_status=payload.status, note=payload.note,
    ))
    db.commit()
    db.refresh(issue)
    return payment_issue_dict(issue, include_private=True)


@router.get("/api/admin/payment-issues/{issue_id}/audit")
def payment_issue_audit(
    issue_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_admin),
):
    require_durable_admin_writes()
    if not db.get(models.PaymentSupportIssue, issue_id):
        raise HTTPException(404, "Murojaat topilmadi")
    events = db.query(models.PaymentSupportAudit).filter_by(issue_id=issue_id).order_by(
        models.PaymentSupportAudit.id.asc()
    ).all()
    return {"events": [
        {"actor_id": event.actor_id, "from": event.old_status,
         "to": event.new_status, "note": event.note,
         "at": event.occurred_at.isoformat() if event.occurred_at else None}
        for event in events
    ]}
