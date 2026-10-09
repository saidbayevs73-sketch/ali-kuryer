"""Courier shift photos, claimable orders and consent-based active GPS updates."""
from datetime import datetime, timedelta
import os
from pathlib import Path
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/courier", tags=["Courier"])
MAX_PHOTO = 5 * 1024 * 1024
PRIVATE_UPLOAD_DIR = Path(os.getenv(
    "PRIVATE_UPLOAD_DIR",
    str(Path(__file__).resolve().parents[2] / "private_uploads"),
))


def require_courier(user: models.User = Depends(get_current_user)):
    if not user.is_active or user.role != "courier":
        raise HTTPException(403, "Faqat kuryer uchun")
    return user


def approved_shift(db: Session, courier_id: int):
    shift = db.query(models.CourierShift).filter_by(
        courier_id=courier_id
    ).order_by(models.CourierShift.id.desc()).first()
    if (
        shift is None or shift.status != "approved" or not shift.created_at
        or shift.created_at < datetime.utcnow() - timedelta(hours=24)
    ):
        raise HTTPException(403, "Smena uchun selfieni yuboring va admin tasdig‘ini kuting")
    return shift


class CourierLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class TransitionRequest(BaseModel):
    status: str = Field(pattern="^(on_the_way|delivered)$")


@router.get("/status")
def courier_status():
    return {"status": "ok", "message": "Ali Kuryer kuryer API tayyor"}


@router.post("/shifts/start", status_code=201)
async def start_shift(
    latitude: float = Form(ge=-90, le=90),
    longitude: float = Form(ge=-180, le=180),
    selfie: UploadFile = File(...),
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    raw = await selfie.read(MAX_PHOTO + 1)
    await selfie.close()
    if len(raw) > MAX_PHOTO:
        raise HTTPException(413, "Rasm 5 MB dan katta bo‘lmasligi kerak")
    if raw.startswith(b"\xff\xd8\xff"):
        extension = ".jpg"
    elif raw.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = ".png"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        extension = ".webp"
    else:
        raise HTTPException(422, "JPG, PNG yoki WebP rasm yuklang")
    # Photos stay outside the public /static directory.
    PRIVATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    photo_path = PRIVATE_UPLOAD_DIR / (secrets.token_hex(20) + extension)
    photo_path.write_bytes(raw)
    try:
        shift = models.CourierShift(
            courier_id=user.id, selfie_path=str(photo_path),
            latitude=latitude, longitude=longitude, status="pending",
        )
        db.add(shift)
        db.commit()
        return {"shift_id": shift.id, "status": "pending"}
    except Exception:
        db.rollback()
        photo_path.unlink(missing_ok=True)
        raise


@router.get("/shifts/current")
def current_shift(
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    shift = db.query(models.CourierShift).filter_by(
        courier_id=user.id
    ).order_by(models.CourierShift.id.desc()).first()
    return {"status": shift.status if shift else "not_started",
            "created_at": shift.created_at.isoformat() if shift and shift.created_at else None}


@router.get("/orders/available")
def available_orders(
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    approved_shift(db, user.id)
    orders = db.query(models.Order).filter(
        models.Order.status == "ready",
        models.Order.courier_id.is_(None),
    ).order_by(models.Order.id).limit(60).all()
    result = []
    for o in orders:
        restaurant = db.get(models.Restaurant, o.restaurant_id)
        result.append({
            "id": o.id,
            "restaurant": restaurant.name if restaurant else "Oshxona",
            "pickup_address": restaurant.address if restaurant else "",
        })
    return result


@router.post("/orders/{order_id}/claim")
def claim_order(
    order_id: int,
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    approved_shift(db, user.id)
    updated = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.courier_id.is_(None),
        models.Order.status == "ready",
    ).update({
        models.Order.courier_id: user.id,
        models.Order.status: "picked_up",
    }, synchronize_session=False)
    db.commit()
    if updated != 1:
        raise HTTPException(409, "Buyurtma olingan yoki hali tayyor emas")
    return {"order_id": order_id, "status": "picked_up"}


@router.get("/orders/mine")
def my_orders(
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    orders = db.query(models.Order).filter_by(courier_id=user.id).order_by(
        models.Order.id.desc()
    ).limit(80).all()
    result = []
    for order in orders:
        detail = db.query(models.DeliveryDetail).filter_by(order_id=order.id).first()
        restaurant = db.get(models.Restaurant, order.restaurant_id)
        items = db.query(models.OrderItem).filter_by(order_id=order.id).all()
        name_map = {m.id: m.name for m in db.query(models.MenuItem).filter(
            models.MenuItem.id.in_([i.menu_item_id for i in items])
        ).all()} if items else {}
        result.append({
            "id": order.id, "status": order.status, "total": order.total,
            "pickup": restaurant.address if restaurant else "",
            "delivery_address": order.address,
            "recipient_name": detail.recipient_name if detail else "",
            "phone": detail.phone if detail else "",
            "latitude": detail.latitude if detail else None,
            "longitude": detail.longitude if detail else None,
            "items": [
                {"name": name_map.get(i.menu_item_id, "Taom"), "quantity": i.quantity}
                for i in items
            ],
        })
    return result


@router.post("/orders/{order_id}/status")
def courier_order_status(
    order_id: int,
    data: TransitionRequest,
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    order = db.get(models.Order, order_id)
    if order is None or order.courier_id != user.id:
        raise HTTPException(404, "Buyurtma topilmadi")
    allowed = {"picked_up": "on_the_way", "on_the_way": "delivered"}
    if allowed.get(order.status) != data.status:
        raise HTTPException(409, "Buyurtma holati mos kelmaydi")
    approved_shift(db, user.id)
    order.status = data.status
    db.commit()
    return {"order_id": order.id, "status": order.status}


@router.post("/location")
def update_location(
    data: CourierLocationRequest,
    user: models.User = Depends(require_courier),
    db: Session = Depends(get_db),
):
    approved_shift(db, user.id)
    active = db.query(models.Order).filter(
        models.Order.courier_id == user.id,
        models.Order.status.in_(("picked_up", "on_the_way")),
    ).first()
    if not active:
        raise HTTPException(403, "GPS faqat faol buyurtma davomida yuboriladi")
    point = db.get(models.CourierLocation, user.id)
    if point is None:
        point = models.CourierLocation(courier_id=user.id)
        db.add(point)
    point.latitude = data.latitude
    point.longitude = data.longitude
    point.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
