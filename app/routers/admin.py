"""Role-protected admin dashboard API.

Admin can review complaints, provision staff, approve shift selfies,
and inspect active orders. Private selfies are never served by /static.
"""
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models, security
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def require_admin(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role != "admin":
        raise HTTPException(status_code=403, detail="Faqat administrator uchun")
    return user


class ComplaintReply(BaseModel):
    reply: str = Field(min_length=2, max_length=2000)
    status: Literal["answered", "closed"] = "answered"


class StaffCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(pattern=r"^\+998\d{9}$")
    password: str = Field(min_length=12, max_length=72)
    role: Literal["courier", "restaurant"]
    restaurant_name: str | None = Field(default=None, max_length=150)
    restaurant_address: str | None = Field(default=None, max_length=255)


class ShiftReview(BaseModel):
    status: Literal["approved", "rejected"]


@router.get("/status")
def admin_status():
    return {"status": "ok", "message": "Ali Kuryer admin API tayyor"}


@router.get("/complaints")
def list_complaints(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    complaints = db.query(models.Complaint).order_by(models.Complaint.id.desc()).limit(200).all()
    return [{
        "id": c.id, "order_id": c.order_id, "name": c.name,
        "phone": c.phone, "message": c.message, "status": c.status,
        "reply": c.reply,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in complaints]


@router.post("/complaints/{complaint_id}/reply")
def reply_to_complaint(
    complaint_id: int,
    data: ComplaintReply,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    complaint = db.get(models.Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(404, "Murojaat topilmadi")
    complaint.reply = data.reply.strip()
    complaint.status = data.status
    db.commit()
    return {"complaint_id": complaint_id, "status": complaint.status}


@router.get("/orders")
def all_orders(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    orders = db.query(models.Order).order_by(models.Order.id.desc()).limit(200).all()
    result = []
    for order in orders:
        detail = db.query(models.DeliveryDetail).filter_by(order_id=order.id).first()
        restaurant = db.get(models.Restaurant, order.restaurant_id)
        result.append({
            "id": order.id, "status": order.status, "total": order.total,
            "restaurant": restaurant.name if restaurant else "",
            "recipient": detail.recipient_name if detail else "",
            "phone": detail.phone if detail else "",
            "address": order.address,
            "courier_id": order.courier_id,
        })
    return result


@router.get("/staff")
def list_staff(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    staff = db.query(models.User).filter(
        models.User.role.in_(("courier", "restaurant"))
    ).order_by(models.User.id.desc()).limit(100).all()
    return [{"id": u.id, "name": u.name, "phone": u.phone, "role": u.role,
             "is_active": u.is_active} for u in staff]


@router.post("/staff", status_code=201)
def add_staff(
    data: StaffCreate,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not data.password or len(data.password.encode("utf-8")) > 72:
        raise HTTPException(422, "Parol 12–72 bayt bo‘lishi kerak")
    if db.query(models.User).filter_by(phone=data.phone).first():
        raise HTTPException(409, "Bu telefon raqami ro‘yxatdan o‘tgan")
    if data.role == "restaurant" and not (data.restaurant_name or "").strip():
        raise HTTPException(422, "Oshxona nomini kiriting")
    try:
        staff = models.User(
            name=data.name.strip(), phone=data.phone,
            password_hash=security.hash_password(data.password),
            role=data.role, is_active=True,
        )
        db.add(staff)
        db.flush()
        restaurant_id = None
        if data.role == "restaurant":
            restaurant = models.Restaurant(
                name=data.restaurant_name.strip(),
                address=(data.restaurant_address or "").strip(),
                owner_id=staff.id, is_approved=True,
            )
            db.add(restaurant)
            db.flush()
            restaurant_id = restaurant.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": staff.id, "role": staff.role, "restaurant_id": restaurant_id}


@router.get("/courier-shifts")
def list_courier_shifts(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    shifts = db.query(models.CourierShift).order_by(
        models.CourierShift.id.desc()
    ).limit(100).all()
    return [{
        "id": s.id, "courier_id": s.courier_id, "status": s.status,
        "lat": s.latitude, "lng": s.longitude,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    } for s in shifts]


@router.post("/courier-shifts/{shift_id}/review")
def review_shift(
    shift_id: int,
    data: ShiftReview,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    shift = db.get(models.CourierShift, shift_id)
    if not shift:
        raise HTTPException(404, "Kuryer smenasi topilmadi")
    if shift.status != "pending":
        raise HTTPException(409, "Smena avval ko‘rib chiqilgan")
    shift.status = data.status
    db.commit()
    return {"shift_id": shift_id, "status": shift.status}


@router.get("/courier-shifts/{shift_id}/photo")
def get_shift_photo(
    shift_id: int,
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    shift = db.get(models.CourierShift, shift_id)
    if not shift:
        raise HTTPException(404, "Smena topilmadi")
    path = Path(shift.selfie_path)
    if not path.is_file():
        raise HTTPException(404, "Rasm topilmadi")
    extension = path.suffix.lower()
    mime = {".jpg": "image/jpeg", ".png": "image/png",
            ".webp": "image/webp"}.get(extension)
    if not mime:
        raise HTTPException(404, "Rasm mavjud emas")
    return FileResponse(
        path, media_type=mime,
        headers={"Cache-Control": "private, no-store",
                 "X-Content-Type-Options": "nosniff"},
    )


@router.get("/active-couriers")
def active_couriers(
    user: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    orders = db.query(models.Order).filter(
        models.Order.courier_id.is_not(None),
        models.Order.status.in_(("picked_up", "on_the_way")),
    ).all()
    result = []
    for order in orders:
        position = db.get(models.CourierLocation, order.courier_id)
        if position:
            result.append({
                "order_id": order.id, "courier_id": order.courier_id,
                "latitude": position.latitude,
                "longitude": position.longitude,
                "updated_at": position.updated_at.isoformat() if position.updated_at else None,
            })
    return result
