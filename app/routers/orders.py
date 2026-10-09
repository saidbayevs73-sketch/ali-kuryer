"""Customer checkout and private order tracking.

Online card payments are intentionally NOT accepted until an acquiring provider
is configured. All totals are recalculated from current menu prices.
"""
import math
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_db

router = APIRouter(prefix="/api/orders", tags=["Orders"])


class CartItem(BaseModel):
    id: int = Field(gt=0)
    qty: int = Field(ge=1, le=30)


class CheckoutRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    phone: str = Field(pattern=r"^\+998\d{9}$")
    street: str = Field(min_length=2, max_length=160)
    house: str = Field(min_length=1, max_length=40)
    entrance: str = Field(default="", max_length=40)
    floor: str = Field(default="", max_length=40)
    apartment: str = Field(default="", max_length=40)
    note: str = Field(default="", max_length=300)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    payment: Literal["cash"] = "cash"
    items: list[CartItem] = Field(min_length=1, max_length=30)


@router.get("/status")
def orders_status():
    return {"status": "ok", "message": "Ali Kuryer buyurtmalar API tayyor"}


@router.post("", status_code=201)
@router.post("/", status_code=201, include_in_schema=False)
def create_order(data: CheckoutRequest, db: Session = Depends(get_db)):
    if not (math.isfinite(data.lat) and math.isfinite(data.lng)):
        raise HTTPException(422, "GPS koordinatalari noto‘g‘ri")

    name, street, house = data.name.strip(), data.street.strip(), data.house.strip()
    if not all((name, street, house)):
        raise HTTPException(422, "Ism, ko‘cha va uy raqami majburiy")

    quantities = {}
    for item in data.items:
        quantities[item.id] = quantities.get(item.id, 0) + item.qty
        if quantities[item.id] > 30:
            raise HTTPException(422, "Bir xil taomdan juda ko‘p tanlangan")

    price_items = []
    restaurant_id = None
    total = 0
    for item_id, qty in quantities.items():
        menu = db.get(models.MenuItem, item_id)
        if menu is None or not menu.is_available or not math.isfinite(menu.price) or menu.price <= 0:
            raise HTTPException(400, "Savatdagi taom hozir mavjud emas")
        if restaurant_id is None:
            restaurant_id = menu.restaurant_id
        if menu.restaurant_id != restaurant_id:
            raise HTTPException(400, "Bir buyurtmada bitta oshxona taomlari bo‘lishi mumkin")
        unit_price = round(menu.price)
        total += unit_price * qty
        price_items.append((menu, qty, unit_price))

    restaurant = db.get(models.Restaurant, restaurant_id)
    if restaurant is None or not restaurant.is_approved:
        raise HTTPException(400, "Oshxona hozir buyurtma qabul qilmayapti")

    token = secrets.token_urlsafe(32)
    address = ", ".join(
        filter(None, [
            street, "uy " + house,
            ("xonadon " + data.apartment.strip()) if data.apartment.strip() else "",
            data.note.strip(),
        ])
    )
    try:
        order = models.Order(
            restaurant_id=restaurant_id,
            address=address,
            total=total,
            status="pending",
            payment_method="cash",
        )
        db.add(order)
        db.flush()
        db.add(models.DeliveryDetail(
            order_id=order.id,
            recipient_name=name,
            phone=data.phone,
            street=street,
            house=house,
            entrance=data.entrance.strip(),
            floor=data.floor.strip(),
            apartment=data.apartment.strip(),
            note=data.note.strip(),
            latitude=data.lat,
            longitude=data.lng,
            tracking_token=token,
        ))
        for menu, qty, unit_price in price_items:
            db.add(models.OrderItem(
                order_id=order.id,
                menu_item_id=menu.id,
                quantity=qty,
                price=unit_price,
            ))
        db.commit()
        return {"order_id": order.id, "total": total, "status": order.status,
                "tracking_token": token, "payment": "cash"}
    except Exception:
        db.rollback()
        raise


@router.get("/{order_id}/track")
def track_order(
    order_id: int,
    token: str = Query(min_length=20, max_length=100),
    db: Session = Depends(get_db),
):
    detail = db.query(models.DeliveryDetail).filter_by(order_id=order_id).first()
    if not detail or not secrets.compare_digest(detail.tracking_token, token):
        raise HTTPException(404, "Buyurtma topilmadi")

    order = db.get(models.Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi")

    result = {"order_id": order.id, "status": order.status, "total": order.total}
    if order.courier_id and order.status in ("on_the_way", "picked_up"):
        position = db.get(models.CourierLocation, order.courier_id)
        if position:
            result["courier_location"] = {
                "lat": position.latitude, "lng": position.longitude,
                "updated_at": position.updated_at.isoformat() if position.updated_at else None,
            }
    return result
