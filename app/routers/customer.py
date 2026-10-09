"""Public restaurant catalog and customer-to-admin complaint intake."""
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_db

router = APIRouter(prefix="/api/customer", tags=["Customer"])


class ComplaintRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(pattern=r"^\+998\d{9}$")
    message: str = Field(min_length=10, max_length=1500)
    order_id: int | None = Field(default=None, gt=0)
    tracking_token: str | None = Field(default=None, max_length=100)


@router.get("/restaurants")
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(models.Restaurant).all()


@router.get("/restaurants/{restaurant_id}/menu")
def restaurant_menu(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.get(models.Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")

    items = db.query(models.MenuItem).filter(
        models.MenuItem.restaurant_id == restaurant_id,
        models.MenuItem.is_available.is_(True),
    ).all()
    return {"restaurant_id": restaurant_id, "items": items}


@router.post("/complaints", status_code=201)
def submit_complaint(data: ComplaintRequest, db: Session = Depends(get_db)):
    name, message = data.name.strip(), data.message.strip()
    if len(name) < 2 or len(message) < 10:
        raise HTTPException(status_code=422, detail="Ism va murojaat matnini to‘ldiring")

    if data.order_id is not None:
        detail = db.query(models.DeliveryDetail).filter_by(order_id=data.order_id).first()
        if (
            not detail or not data.tracking_token
            or not secrets.compare_digest(detail.tracking_token, data.tracking_token)
        ):
            raise HTTPException(404, "Buyurtma topilmadi")
        if detail.phone != data.phone:
            raise HTTPException(422, "Buyurtma telefon raqami mos emas")

    # Lightweight abuse limit; deploy a provider-side IP limit/CAPTCHA for public scale.
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent = db.query(models.Complaint).filter(
        models.Complaint.phone == data.phone,
        models.Complaint.created_at >= hour_ago,
    ).count()
    if recent >= 3:
        raise HTTPException(429, "Bir soatda 3 tadan ortiq murojaat yuborib bo‘lmaydi")

    complaint = models.Complaint(
        order_id=data.order_id,
        name=name,
        phone=data.phone,
        message=message,
        status="new",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return {"complaint_id": complaint.id, "status": "new"}
