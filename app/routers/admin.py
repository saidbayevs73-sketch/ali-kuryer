"""Protected Super Admin dashboard API.

Only authenticated, active admin accounts can read business figures or customer
details. No admin password, recovery secret, or complete raw user record is sent
to the browser.
"""
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(user=Depends(get_current_user)):
    if not user.is_active or user.role != "admin":
        raise HTTPException(403, "Bu sahifaga faqat administrator kira oladi")
    return user


@router.get("/status")
def admin_status():
    # No private metrics or identifying information in the public health check.
    return {"status": "ok", "message": "Ali Kuryer admin API tayyor"}


@router.get("/overview")
def overview(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    total_orders = db.query(func.count(models.Order.id)).scalar() or 0
    pending_statuses = ("pending", "preparing", "ready", "assigned", "delivering")
    active_orders = db.query(func.count(models.Order.id)).filter(
        models.Order.status.in_(pending_statuses)
    ).scalar() or 0
    delivered_orders = db.query(func.count(models.Order.id)).filter(
        models.Order.status == "delivered"
    ).scalar() or 0
    delivered_value = db.query(func.coalesce(func.sum(models.Order.total), 0)).filter(
        models.Order.status == "delivered"
    ).scalar() or 0
    restaurants_total = db.query(func.count(models.Restaurant.id)).scalar() or 0
    restaurants_pending = db.query(func.count(models.Restaurant.id)).filter(
        models.Restaurant.is_approved.is_(False)
    ).scalar() or 0
    customers_total = db.query(func.count(models.User.id)).filter(
        models.User.role == "customer"
    ).scalar() or 0
    couriers_total = db.query(func.count(models.User.id)).filter(
        models.User.role == "courier"
    ).scalar() or 0
    new_applications = db.query(func.count(models.PartnerApplication.id)).filter(
        models.PartnerApplication.status == "new"
    ).scalar() or 0

    today = datetime.utcnow().date()
    start = today - timedelta(days=6)
    # Small, cross-database compatible aggregation over the last seven days.
    recent = db.query(models.Order.created_at, models.Order.status, models.Order.total).filter(
        models.Order.created_at >= datetime.combine(start, datetime.min.time())
    ).all()
    buckets = {}
    for i in range(7):
        day = (start + timedelta(days=i)).isoformat()
        buckets[day] = {"date": day, "count": 0, "delivered_value": 0.0}
    for created, status, amount in recent:
        if created is None:
            continue
        day = created.date().isoformat()
        if day in buckets:
            buckets[day]["count"] += 1
            if status == "delivered":
                buckets[day]["delivered_value"] += float(amount or 0)
    for v in buckets.values():
        v["delivered_value"] = round(v["delivered_value"], 2)

    return {
        "total_orders": total_orders,
        "active_orders": active_orders,
        "delivered_orders": delivered_orders,
        "delivered_order_value": round(float(delivered_value), 2),
        "restaurants_total": restaurants_total,
        "restaurants_pending": restaurants_pending,
        "customers_total": customers_total,
        "couriers_total": couriers_total,
        "applications_pending": new_applications,
        "last_7_days": list(buckets.values()),
        "note": "Yakunlangan buyurtmalar summasi — foyda yoki hisobga tushgan mablag‘ emas.",
    }


@router.get("/people")
def people(
    role: Literal["customer", "courier", "restaurant"] = Query("customer"),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    users = db.query(models.User).filter(models.User.role == role).order_by(
        models.User.id.desc()
    ).limit(limit).all()
    customer_counts = {}
    online = {}
    if role == "customer" and users:
        ids = [x.id for x in users]
        customer_counts = dict(db.query(
            models.Order.customer_id, func.count(models.Order.id)
        ).filter(models.Order.customer_id.in_(ids)).group_by(
            models.Order.customer_id
        ).all())
    if role == "courier" and users:
        ids = [x.id for x in users]
        online = {x.courier_id: x for x in db.query(models.CourierPresence).filter(
            models.CourierPresence.courier_id.in_(ids)
        ).all()}
    now = datetime.utcnow()
    records = []
    for x in users:
        pos = online.get(x.id)
        is_online = bool(
            pos and pos.is_available and pos.last_seen_at and
            pos.last_seen_at >= now - timedelta(minutes=5)
        )
        records.append({
            "id": x.id, "name": x.name, "phone": x.phone,
            "role": x.role, "is_active": bool(x.is_active),
            "created_at": x.created_at.isoformat() if x.created_at else None,
            "order_count": int(customer_counts.get(x.id, 0)),
            "is_online": is_online,
        })
    return records


class ApplicationReview(BaseModel):
    status: Literal["new", "reviewing", "approved", "rejected"]


@router.patch("/partner-applications/{application_id}")
def review_application(
    application_id: int,
    data: ApplicationReview,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    record = db.get(models.PartnerApplication, application_id)
    if record is None:
        raise HTTPException(404, "Ariza topilmadi")
    record.status = data.status
    db.commit()
    # Approving an application does not create a staff login automatically.
    return {"id": record.id, "status": record.status}
