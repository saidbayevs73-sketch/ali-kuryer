"""Restaurant staff endpoints with strict ownership and status transitions."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/restaurant", tags=["Restaurant"])


def current_restaurant(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user.is_active or user.role != "restaurant":
        raise HTTPException(403, "Faqat oshxona xodimlari uchun")
    restaurant = db.query(models.Restaurant).filter_by(owner_id=user.id).first()
    if not restaurant or not restaurant.is_approved:
        raise HTTPException(403, "Oshxona tasdiqlanmagan")
    return restaurant


class OrderStatusRequest(BaseModel):
    status: Literal["preparing", "ready", "canceled"]


class MenuItemRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    price: int = Field(gt=0, le=100_000_000)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool = True


@router.get("/status")
def restaurant_status():
    return {"status": "ok", "message": "Ali Kuryer restoran API tayyor"}


@router.get("/orders")
def restaurant_orders(
    restaurant: models.Restaurant = Depends(current_restaurant),
    db: Session = Depends(get_db),
):
    orders = db.query(models.Order).filter_by(
        restaurant_id=restaurant.id
    ).order_by(models.Order.id.desc()).limit(100).all()
    result = []
    for order in orders:
        items = db.query(models.OrderItem).filter_by(order_id=order.id).all()
        menu = {i.id: i.name for i in db.query(models.MenuItem).filter(
            models.MenuItem.id.in_([x.menu_item_id for x in items])
        ).all()} if items else {}
        result.append({
            "id": order.id, "status": order.status, "total": order.total,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": [
                {"name": menu.get(i.menu_item_id, "Taom"), "quantity": i.quantity}
                for i in items
            ],
        })
    return result


@router.post("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    data: OrderStatusRequest,
    restaurant: models.Restaurant = Depends(current_restaurant),
    db: Session = Depends(get_db),
):
    order = db.get(models.Order, order_id)
    if not order or order.restaurant_id != restaurant.id:
        raise HTTPException(404, "Buyurtma topilmadi")
    allowed = {
        "pending": {"preparing", "canceled"},
        "preparing": {"ready"},
    }
    if data.status not in allowed.get(order.status, set()):
        raise HTTPException(409, "Buyurtma holatini bunday o‘zgartirib bo‘lmaydi")
    order.status = data.status
    db.commit()
    return {"order_id": order.id, "status": order.status}


@router.get("/menu")
def restaurant_menu(
    restaurant: models.Restaurant = Depends(current_restaurant),
    db: Session = Depends(get_db),
):
    return db.query(models.MenuItem).filter_by(restaurant_id=restaurant.id).all()


@router.post("/menu", status_code=201)
def add_menu_item(
    data: MenuItemRequest,
    restaurant: models.Restaurant = Depends(current_restaurant),
    db: Session = Depends(get_db),
):
    image_url = (data.image_url or "").strip()
    if image_url and not image_url.startswith("https://"):
        raise HTTPException(422, "Rasm havolasi HTTPS bilan boshlanishi kerak")
    item = models.MenuItem(
        restaurant_id=restaurant.id,
        name=data.name.strip(),
        price=data.price,
        image_url=image_url or None,
        is_available=data.is_available,
    )
    db.add(item)
    db.commit()
    return {"id": item.id, "name": item.name}
