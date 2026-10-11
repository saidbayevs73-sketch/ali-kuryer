"""Ali Kuryer platform controls, customer rewards and audit events.

Production rules:
- administrator actions require server-verified admin JWT;
- feature changes use an allowlist (never arbitrary code execution);
- public config reveals only safe marketing/content settings;
- an entered phone number is never evidence of phone ownership;
- bonus points are informational, NOT cash or electronic money;
- identity-provider passwords, tokens and Google data are never exposed.
"""
import json
import re
from datetime import datetime
from urllib.parse import urlsplit
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Session

from app.database import Base
from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(tags=["Platform controls"])

# These tables are additive: never alter or truncate production identity/order tables.
class PlatformFlag(Base):
    __tablename__ = "platform_feature_flags"
    key = Column(String(50), primary_key=True)
    enabled = Column(Boolean, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class PromotionalBanner(Base):
    __tablename__ = "platform_promotional_banners"
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    subtitle = Column(String(220), nullable=False, default="")
    image_url = Column(String(600), nullable=False, default="")
    cta_label = Column(String(35), nullable=False, default="Ko‘rish")
    is_active = Column(Boolean, nullable=False, default=False)
    changed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class AdminAuditEvent(Base):
    __tablename__ = "platform_admin_audit"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(70), nullable=False)
    target = Column(String(100), nullable=False)
    detail = Column(String(400), nullable=False, default="")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# A feature may hide a client button; essential authorization always remains server-side.
FEATURE_DEFAULTS = {
    "orders": True,
    "bonus": True,
    "promotions": True,
    "ai_assistant": True,
    "support_chat": True,
    "courier_tracking": True,
    "reviews": False,  # not available until reviews API and moderation are built
    "wallet": False,  # no deposit, payout or real-money wallet is implemented
}
FEATURE_LABELS = {
    "orders": "Buyurtma berish",
    "bonus": "Bonus ballar",
    "promotions": "Reklama va aksiyalar",
    "ai_assistant": "Muhammadali AI yordamchi",
    "support_chat": "Yordam markazi",
    "courier_tracking": "Buyurtma kuzatuvi",
    "reviews": "Reyting va sharhlar (hali ulanmagan)",
    "wallet": "Haqiqiy pul hamyoni (hali ulanmagan)",
}
# Disabled because there is no backend: never pretend to enable by toggling a checkbox.
NOT_IMPLEMENTED = {"wallet", "reviews"}


def admin_required(user=Depends(get_current_user)):
    if not user.is_active or user.role != "admin":
        raise HTTPException(403, "Faqat Super Admin")
    return user


def customer_required(user=Depends(get_current_user)):
    if not user.is_active or user.role != "customer":
        raise HTTPException(403, "Mijoz hisobi kerak")
    return user


def audit(db: Session, actor_id: int, action: str, target: str, detail: str = "") -> None:
    """Call inside the same DB transaction as the mutation."""
    db.add(AdminAuditEvent(actor_id=actor_id, action=action, target=target,
                           detail=detail[:400]))


def flags(db: Session) -> dict:
    answer = FEATURE_DEFAULTS.copy()
    for row in db.query(PlatformFlag).all():
        if row.key in answer and row.key not in NOT_IMPLEMENTED:
            answer[row.key] = bool(row.enabled)
    return answer


def banner_data(banner):
    return {"id": banner.id, "title": banner.title, "subtitle": banner.subtitle,
            "image_url": banner.image_url, "cta_label": banner.cta_label,
            "is_active": bool(banner.is_active)}


def valid_image_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise HTTPException(422, "Rasm uchun HTTPS manzilini kiriting")
    if len(value) > 600 or re.search(r"[\x00-\x1f]", value):
        raise HTTPException(422, "Rasm manzili noto‘g‘ri")
    return value


class FlagChange(BaseModel):
    enabled: bool


class BannerIn(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    subtitle: str = Field(default="", max_length=220)
    image_url: str = Field(default="", max_length=600)
    cta_label: str = Field(default="Ko‘rish", min_length=1, max_length=35)
    is_active: bool = False


@router.get("/api/platform/public")
def public_platform_configuration(db: Session = Depends(get_db)):
    enabled = flags(db)
    promos = db.query(PromotionalBanner).filter(
        PromotionalBanner.is_active.is_(True)
    ).order_by(PromotionalBanner.id.desc()).limit(12).all()
    return {"features": enabled, "banners": [banner_data(b) for b in promos]}


@router.get("/api/admin/platform/features")
def admin_feature_list(db: Session = Depends(get_db), _=Depends(admin_required)):
    enabled = flags(db)
    return [{"key": k, "label": FEATURE_LABELS[k], "enabled": enabled[k],
             "available": k not in NOT_IMPLEMENTED}
            for k in FEATURE_DEFAULTS]


@router.put("/api/admin/platform/features/{feature_key}")
def update_feature(feature_key: str, data: FlagChange,
                   db: Session = Depends(get_db), admin=Depends(admin_required)):
    if feature_key not in FEATURE_DEFAULTS:
        raise HTTPException(404, "Bunday funksiya mavjud emas")
    if feature_key in NOT_IMPLEMENTED:
        raise HTTPException(409, "Bu funksiya uchun haqiqiy xizmat hali ulanmagan")
    row = db.get(PlatformFlag, feature_key)
    if row is None:
        row = PlatformFlag(key=feature_key, enabled=data.enabled)
        db.add(row)
    row.enabled = data.enabled
    row.changed_at = datetime.utcnow()
    row.changed_by = admin.id
    audit(db, admin.id, "feature_changed", feature_key,
          "enabled=" + str(data.enabled).lower())
    db.commit()
    return {"key": feature_key, "enabled": data.enabled}


@router.get("/api/admin/platform/banners")
def admin_banners(db: Session = Depends(get_db), _=Depends(admin_required)):
    return [banner_data(x) for x in db.query(PromotionalBanner).order_by(
        PromotionalBanner.id.desc()).limit(100).all()]


@router.post("/api/admin/platform/banners", status_code=201)
def create_banner(data: BannerIn, db: Session = Depends(get_db),
                  admin=Depends(admin_required)):
    image_url = valid_image_url(data.image_url.strip())
    banner = PromotionalBanner(title=data.title.strip(), subtitle=data.subtitle.strip(),
        image_url=image_url, cta_label=data.cta_label.strip(), is_active=data.is_active,
        changed_by=admin.id)
    db.add(banner)
    db.flush()
    audit(db, admin.id, "banner_created", "banner:" + str(banner.id),
          "active=" + str(data.is_active).lower())
    db.commit()
    db.refresh(banner)
    return banner_data(banner)


@router.put("/api/admin/platform/banners/{banner_id}")
def update_banner(banner_id: int, data: BannerIn, db: Session = Depends(get_db),
                  admin=Depends(admin_required)):
    banner = db.get(PromotionalBanner, banner_id)
    if not banner:
        raise HTTPException(404, "Banner topilmadi")
    banner.title = data.title.strip()
    banner.subtitle = data.subtitle.strip()
    banner.image_url = valid_image_url(data.image_url.strip())
    banner.cta_label = data.cta_label.strip()
    banner.is_active = data.is_active
    banner.changed_by = admin.id
    banner.changed_at = datetime.utcnow()
    audit(db, admin.id, "banner_updated", "banner:" + str(banner.id),
          "active=" + str(data.is_active).lower())
    db.commit()
    return banner_data(banner)


@router.get("/api/admin/platform/audit")
def audit_list(limit: int = Query(100, ge=1, le=200),
               db: Session = Depends(get_db), _=Depends(admin_required)):
    events = db.query(AdminAuditEvent).order_by(
        AdminAuditEvent.id.desc()).limit(limit).all()
    return [{"id": x.id, "actor_id": x.actor_id, "action": x.action,
             "target": x.target, "detail": x.detail,
             "created_at": x.created_at.isoformat() if x.created_at else None}
            for x in events]


@router.get("/api/admin/platform/linked-accounts")
def linked_accounts(provider: Literal["google", "telegram"] = Query("google"),
                    limit: int = Query(100, ge=1, le=100),
                    db: Session = Depends(get_db), _=Depends(admin_required)):
    identity = models.GoogleIdentity if provider == "google" else models.TelegramIdentity
    links = db.query(identity, models.User).join(models.User,
        identity.user_id == models.User.id).filter(
        models.User.role == "customer"
    ).order_by(models.User.id.desc()).limit(limit).all()
    # Only account linkage, NOT email inbox, OAuth tokens, account passwords or provider IDs.
    return [{"user_id": user.id, "name": user.name,
             "phone": user.phone, "provider": provider, "active": bool(user.is_active),
             "linked_at": link.created_at.isoformat() if link.created_at else None}
            for link, user in links]


@router.get("/api/customer/me/summary")
def my_summary(db: Session = Depends(get_db), user=Depends(customer_required)):
    orders = db.query(models.Order).filter(
        models.Order.customer_id == user.id
    ).order_by(models.Order.id.desc()).limit(100).all()
    # Bonus is computed over ALL completed orders, not only the 100 shown in history.
    completed_amounts = db.query(models.Order.total).filter(
        models.Order.customer_id == user.id,
        models.Order.status == "delivered"
    ).yield_per(250)
    bonus_points = sum(
        int(max(0.0, float(total or 0)) // 10000) for (total,) in completed_amounts
    )
    # Do not falsely call points money. No deposit/wallet accounting system exists.
    return {
        "user": {"id": user.id, "name": user.name, "phone": user.phone},
        "history": [
            {"id": o.id, "restaurant_id": o.restaurant_id, "total": o.total,
             "status": o.status, "address": o.address,
             "created_at": o.created_at.isoformat() if o.created_at else None}
            for o in orders
        ],
        "bonus": {"points": bonus_points,
                  "rule": "Yetkazilgan har 10 000 so‘mlik xarid uchun 1 ball",
                  "basis": "Barcha yakunlangan buyurtmalar",
                  "redeemable": False},
        "wallet": {"available": False, "display": "Hali ulanmagan",
                   "message": "Pul balansi va pul o‘tkazish tizimi hali ishga tushmagan"},
    }
