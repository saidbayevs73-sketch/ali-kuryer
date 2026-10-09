"""Ali Kuryer transactional API: authenticated orders, staff status, GPS and chat.

This router uses existing User/Restaurant/MenuItem/Order tables. New metadata
lives in additive tables, avoiding destructive changes to existing databases.
"""
import math
import io
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Response
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/v1", tags=["Commerce"])
_PHONE = re.compile(r"^\+998[0-9]{9}$")


def me(user=Depends(get_current_user)):
    if not user.is_active:
        raise HTTPException(403, "Hisob faol emas")
    return user


def role(user, *allowed):
    if user.role not in allowed:
        raise HTTPException(403, "Bu amal uchun ruxsat yo‘q")


def coords(lat, lng):
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise HTTPException(422, "Xarita koordinatalari noto‘g‘ri")


def distance_km(a_lat, a_lng, b_lat, b_lng):
    r1, r2 = math.radians(a_lat), math.radians(b_lat)
    dr = r2 - r1
    dg = math.radians(b_lng - a_lng)
    h = math.sin(dr / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dg / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def can_see_order(db, order, user):
    if user.role == "admin":
        return True
    if user.role == "customer" and order.customer_id == user.id:
        return True
    if user.role == "courier" and order.courier_id == user.id:
        return True
    if user.role == "restaurant":
        restaurant = db.get(models.Restaurant, order.restaurant_id)
        return bool(restaurant and restaurant.owner_id == user.id)
    return False


def get_allowed_order(db, order_id, user):
    order = db.get(models.Order, order_id)
    if order is None:
        raise HTTPException(404, "Buyurtma topilmadi")
    if not can_see_order(db, order, user):
        raise HTTPException(403, "Buyurtmaga kirishga ruxsat yo‘q")
    return order


class OrderLineIn(BaseModel):
    menu_item_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=30)


class NewOrderIn(BaseModel):
    restaurant_id: int = Field(gt=0)
    address: str = Field(min_length=5, max_length=500)
    phone: str
    note: str = Field(default="", max_length=500)
    latitude: float | None = None
    longitude: float | None = None
    payment_method: Literal["cash"] = "cash"
    items: list[OrderLineIn] = Field(min_length=1, max_length=40)
    privacy_accepted: bool


class PositionIn(BaseModel):
    latitude: float
    longitude: float
    available: bool
    tracking_consent: bool


class RestaurantGeoIn(BaseModel):
    latitude: float
    longitude: float


class ChangeStatusIn(BaseModel):
    status: Literal["preparing", "ready", "delivering", "delivered", "cancelled"]


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class MenuItemIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    price: float = Field(gt=0, le=100000000)
    image_url: str = Field(default="", max_length=500)
    category: str = Field(default="", max_length=60)
    description: str = Field(default="", max_length=400)
    is_available: bool = True


def serialize_order(db, order):
    items = db.query(models.OrderItem).filter_by(order_id=order.id).all()
    delivery = db.query(models.DeliveryInfo).filter_by(order_id=order.id).first()
    courier = db.get(models.User, order.courier_id) if order.courier_id else None
    position = db.get(models.CourierPresence, order.courier_id) if order.courier_id else None
    fresh = position and position.last_seen_at and position.last_seen_at >= datetime.utcnow() - timedelta(minutes=5)
    return {
        "id": order.id, "restaurant_id": order.restaurant_id,
        "status": order.status, "total": round(float(order.total or 0), 2),
        "payment_method": order.payment_method,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "address": order.address,
        "phone": delivery.phone if delivery else None,
        "courier": {"id": courier.id, "name": courier.name, "phone": courier.phone} if courier else None,
        "courier_location": {
            "latitude": position.latitude, "longitude": position.longitude,
            "updated_at": position.last_seen_at.isoformat()
        } if fresh and position.tracking_consent and order.status in {"delivering", "assigned"} else None,
        "items": [{"menu_item_id": item.menu_item_id,
                   "name": db.get(models.MenuItem, item.menu_item_id).name if db.get(models.MenuItem, item.menu_item_id) else "Taom",
                   "quantity": item.quantity, "price": item.price}
                  for item in items],
    }


@router.post("/orders", status_code=201)
def create_order(data: NewOrderIn, db: Session = Depends(get_db), user=Depends(me)):
    role(user, "customer")
    if not data.privacy_accepted:
        raise HTTPException(400, "Buyurtma va suhbatlar qayta ishlanishiga rozilik kerak")
    if not _PHONE.fullmatch(data.phone):
        raise HTTPException(422, "Telefon +998XXXXXXXXX shaklida bo‘lishi kerak")
    if (data.latitude is None) != (data.longitude is None):
        raise HTTPException(422, "GPS kenglik va uzunlik birga berilishi kerak")
    if data.latitude is not None:
        coords(data.latitude, data.longitude)
    restaurant = db.get(models.Restaurant, data.restaurant_id)
    if not restaurant or not restaurant.is_approved:
        raise HTTPException(404, "Tasdiqlangan oshxona topilmadi")
    item_ids = [line.menu_item_id for line in data.items]
    if len(set(item_ids)) != len(item_ids):
        raise HTTPException(422, "Bir xil taom ikki marta yuborilgan")
    menu = {item.id: item for item in db.query(models.MenuItem).filter(
        models.MenuItem.id.in_(item_ids),
        models.MenuItem.restaurant_id == data.restaurant_id,
        models.MenuItem.is_available.is_(True)
    ).all()}
    if len(menu) != len(item_ids):
        raise HTTPException(409, "Taom mavjud emas yoki boshqa oshxonaga tegishli")
    amount = round(sum(round(menu[line.menu_item_id].price, 2) * line.quantity
                       for line in data.items), 2)
    order = models.Order(
        customer_id=user.id, restaurant_id=data.restaurant_id,
        address=data.address.strip(), total=amount, status="pending",
        payment_method="cash"
    )
    db.add(order)
    db.flush()
    db.add(models.DeliveryInfo(
        order_id=order.id, phone=data.phone, note=data.note.strip(),
        latitude=data.latitude, longitude=data.longitude
    ))
    for line in data.items:
        db.add(models.OrderItem(
            order_id=order.id, menu_item_id=line.menu_item_id,
            quantity=line.quantity, price=round(menu[line.menu_item_id].price, 2)
        ))
    db.commit()
    db.refresh(order)
    return serialize_order(db, order)


@router.get("/orders/my")
def my_orders(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "customer")
    orders = db.query(models.Order).filter_by(customer_id=user.id).order_by(
        models.Order.id.desc()).limit(50).all()
    return [serialize_order(db, order) for order in orders]


@router.get("/orders/{order_id}")
def order_detail(order_id: int, db: Session = Depends(get_db), user=Depends(me)):
    return serialize_order(db, get_allowed_order(db, order_id, user))


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db), user=Depends(me)):
    role(user, "customer")
    order = get_allowed_order(db, order_id, user)
    if order.status != "pending":
        raise HTTPException(409, "Buyurtma tayyorlanayotganda bekor qilish uchun operatorga yozing")
    order.status = "cancelled"
    db.commit()
    return {"status": order.status}


@router.get("/staff/orders")
def staff_orders(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "admin", "restaurant", "courier")
    query = db.query(models.Order)
    if user.role == "restaurant":
        ids = [r.id for r in db.query(models.Restaurant).filter_by(owner_id=user.id).all()]
        query = query.filter(models.Order.restaurant_id.in_(ids))
    if user.role == "courier":
        query = query.filter(models.Order.courier_id == user.id)
    return [serialize_order(db, o) for o in query.order_by(models.Order.id.desc()).limit(100).all()]


@router.post("/orders/{order_id}/status")
def change_status(order_id: int, data: ChangeStatusIn,
                  db: Session = Depends(get_db), user=Depends(me)):
    role(user, "admin", "restaurant", "courier")
    order = get_allowed_order(db, order_id, user)
    if user.role != "admin":
        allowed = {
            ("restaurant", "pending"): {"preparing", "cancelled"},
            ("restaurant", "preparing"): {"ready"},
            ("courier", "assigned"): {"delivering"},
            ("courier", "delivering"): {"delivered"},
        }
        if data.status not in allowed.get((user.role, order.status), set()):
            raise HTTPException(409, "Buyurtma holatini bu bosqichda o‘zgartirib bo‘lmaydi")
    order.status = data.status
    db.commit()
    return serialize_order(db, order)


@router.post("/courier/position")
def courier_position(data: PositionIn, db: Session = Depends(get_db), user=Depends(me)):
    role(user, "courier")
    coords(data.latitude, data.longitude)
    if data.available and not data.tracking_consent:
        raise HTTPException(400, "Kuryer ish joylashuvini ulashishga rozilik berishi kerak")
    p = db.get(models.CourierPresence, user.id)
    if not p:
        p = models.CourierPresence(courier_id=user.id)
        db.add(p)
    p.latitude = data.latitude
    p.longitude = data.longitude
    p.is_available = data.available
    p.tracking_consent = data.tracking_consent
    p.last_seen_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "available": p.is_available}


@router.put("/restaurants/{restaurant_id}/geo")
def restaurant_geo(restaurant_id: int, data: RestaurantGeoIn,
                   db: Session = Depends(get_db), user=Depends(me)):
    role(user, "restaurant", "admin")
    rest = db.get(models.Restaurant, restaurant_id)
    if not rest:
        raise HTTPException(404, "Oshxona topilmadi")
    if user.role != "admin" and rest.owner_id != user.id:
        raise HTTPException(403, "Faqat o‘z oshxonangiz")
    coords(data.latitude, data.longitude)
    p = db.get(models.RestaurantGeo, restaurant_id)
    if not p:
        p = models.RestaurantGeo(restaurant_id=restaurant_id)
        db.add(p)
    p.latitude, p.longitude = data.latitude, data.longitude
    db.commit()
    return {"ok": True}


@router.get("/courier/offers")
def courier_offers(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "courier")
    p = db.get(models.CourierPresence, user.id)
    if not p or not p.tracking_consent or not p.is_available or not p.last_seen_at or (
        p.last_seen_at < datetime.utcnow() - timedelta(minutes=5)
    ):
        return []
    candidates = []
    orders = db.query(models.Order).filter_by(status="ready", courier_id=None).limit(100).all()
    for order in orders:
        geo = db.get(models.RestaurantGeo, order.restaurant_id)
        if not geo:
            continue
        d = distance_km(p.latitude, p.longitude, geo.latitude, geo.longitude)
        if d <= 15:
            candidates.append((d, order))
    return [{"distance_km": round(d, 2), "order": serialize_order(db, order)}
            for d, order in sorted(candidates, key=lambda it: it[0])[:15]]


@router.post("/courier/orders/{order_id}/accept")
def accept_order(order_id: int, db: Session = Depends(get_db), user=Depends(me)):
    role(user, "courier")
    p = db.get(models.CourierPresence, user.id)
    order = db.get(models.Order, order_id)
    if not order or order.status != "ready" or order.courier_id is not None:
        raise HTTPException(409, "Bu buyurtma mavjud emas yoki band qilingan")
    geo = db.get(models.RestaurantGeo, order.restaurant_id)
    if not geo or not p or not p.tracking_consent or not p.is_available or not p.last_seen_at or (
        p.last_seen_at < datetime.utcnow() - timedelta(minutes=5)
    ) or distance_km(p.latitude, p.longitude, geo.latitude, geo.longitude) > 15:
        raise HTTPException(403, "Buyurtma sizga yaqin emas yoki joylashuv faol emas")
    # Atomic conditional assignment protects against simultaneous couriers.
    updated = db.query(models.Order).filter(
        models.Order.id == order_id, models.Order.courier_id.is_(None),
        models.Order.status == "ready"
    ).update({"courier_id": user.id, "status": "assigned"}, synchronize_session=False)
    if not updated:
        db.rollback()
        raise HTTPException(409, "Buyurtmani boshqa kuryer oldi")
    db.commit()
    return serialize_order(db, db.get(models.Order, order_id))


def message_dict(m, db):
    sender = db.get(models.User, m.sender_id)
    return {"id": m.id, "body": m.body, "sender_id": m.sender_id,
            "sender_name": sender.name if sender else "Foydalanuvchi",
            "created_at": m.created_at.isoformat() if m.created_at else None}


@router.get("/orders/{order_id}/messages")
def order_messages(order_id: int, db: Session = Depends(get_db), user=Depends(me)):
    get_allowed_order(db, order_id, user)
    rows = db.query(models.ConversationMessage).filter_by(order_id=order_id).order_by(
        models.ConversationMessage.id.asc()).limit(250).all()
    return [message_dict(m, db) for m in rows]


@router.post("/orders/{order_id}/messages", status_code=201)
def send_order_message(order_id: int, data: MessageIn,
                       db: Session = Depends(get_db), user=Depends(me)):
    order = get_allowed_order(db, order_id, user)
    if order.status in {"cancelled", "delivered"}:
        raise HTTPException(409, "Yopilgan buyurtmada yangi xabar yuborib bo‘lmaydi")
    m = models.ConversationMessage(order_id=order_id, sender_id=user.id, body=data.body.strip())
    if not m.body:
        raise HTTPException(422, "Xabar bo‘sh")
    db.add(m)
    db.commit()
    db.refresh(m)
    return message_dict(m, db)


@router.get("/support/messages")
def support_messages(customer_id: int | None = None,
                     db: Session = Depends(get_db), user=Depends(me)):
    if user.role != "admin":
        role(user, "customer")
        customer_id = user.id
    elif customer_id is None:
        raise HTTPException(422, "Mijoz ID ni kiriting")
    rows = db.query(models.ConversationMessage).filter_by(
        support_customer_id=customer_id, order_id=None
    ).order_by(models.ConversationMessage.id.asc()).limit(250).all()
    return [message_dict(m, db) for m in rows]


@router.post("/support/messages", status_code=201)
def send_support_message(data: MessageIn, customer_id: int | None = None,
                         db: Session = Depends(get_db), user=Depends(me)):
    if user.role != "admin":
        role(user, "customer")
        customer_id = user.id
    elif customer_id is None:
        raise HTTPException(422, "Mijoz ID ni kiriting")
    if not data.body.strip():
        raise HTTPException(422, "Xabar bo‘sh")
    customer = db.get(models.User, customer_id)
    if not customer or customer.role != "customer":
        raise HTTPException(404, "Mijoz topilmadi")
    m = models.ConversationMessage(
        support_customer_id=customer_id, sender_id=user.id, body=data.body.strip()
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return message_dict(m, db)


@router.get("/admin/support/threads")
def support_threads(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "admin")
    rows = db.query(
        models.ConversationMessage.support_customer_id,
        func.max(models.ConversationMessage.id).label("last_id")
    ).filter(
        models.ConversationMessage.support_customer_id.isnot(None),
        models.ConversationMessage.order_id.is_(None)
    ).group_by(models.ConversationMessage.support_customer_id).order_by(
        func.max(models.ConversationMessage.id).desc()
    ).limit(100).all()
    return [{"customer_id": row.support_customer_id,
             "last_message_id": row.last_id} for row in rows]


@router.post("/restaurants/{restaurant_id}/menu", status_code=201)
def add_menu(restaurant_id: int, data: MenuItemIn,
             db: Session = Depends(get_db), user=Depends(me)):
    role(user, "restaurant", "admin")
    r = db.get(models.Restaurant, restaurant_id)
    if not r or (user.role != "admin" and r.owner_id != user.id):
        raise HTTPException(403, "Bu oshxonani tahrirlashga ruxsat yo‘q")
    if data.image_url and not data.image_url.startswith("https://"):
        raise HTTPException(422, "Rasm uchun HTTPS manzil kiriting")
    item = models.MenuItem(
        restaurant_id=restaurant_id, name=data.name.strip(), price=data.price,
        image_url=data.image_url or None, is_available=data.is_available
    )
    db.add(item)
    db.flush()
    db.add(models.MenuExtra(
        menu_item_id=item.id, category=data.category.strip(),
        description=data.description.strip()
    ))
    db.commit()
    return {"id": item.id, "name": item.name, "price": item.price}


@router.get("/restaurants/{restaurant_id}/statistics")
def restaurant_stats(restaurant_id: int,
                     db: Session = Depends(get_db), user=Depends(me)):
    role(user, "restaurant", "admin")
    r = db.get(models.Restaurant, restaurant_id)
    if not r or (user.role != "admin" and r.owner_id != user.id):
        raise HTTPException(403, "Bu oshxona statistikasi sizga tegishli emas")
    menu = db.query(models.MenuItem).filter_by(restaurant_id=restaurant_id).all()
    stats = db.query(
        models.OrderItem.menu_item_id,
        func.sum(models.OrderItem.quantity).label("sold")
    ).join(models.Order, models.Order.id == models.OrderItem.order_id).filter(
        models.Order.restaurant_id == restaurant_id,
        models.Order.status.notin_(["cancelled"])
    ).group_by(models.OrderItem.menu_item_id).all()
    sold = {row.menu_item_id: int(row.sold) for row in stats}
    return sorted(
        [{"menu_item_id": it.id, "name": it.name, "sold_count": sold.get(it.id, 0)}
         for it in menu],
        key=lambda row: row["sold_count"], reverse=True
    )


@router.post("/restaurants/{restaurant_id}/menu/{item_id}/photo")
def upload_menu_photo(restaurant_id: int, item_id: int, file: UploadFile = File(...),
                      db: Session = Depends(get_db), user=Depends(me)):
    """Accept restaurant photos and strip EXIF/GPS metadata before storing."""
    role(user, "restaurant", "admin")
    rest = db.get(models.Restaurant, restaurant_id)
    item = db.get(models.MenuItem, item_id)
    if not rest or not item or item.restaurant_id != restaurant_id:
        raise HTTPException(404, "Taom topilmadi")
    if user.role != "admin" and rest.owner_id != user.id:
        raise HTTPException(403, "Faqat o‘z oshxonangizga rasm yuklay olasiz")
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Faqat JPG, PNG yoki WebP rasm yuklang")
    raw = file.file.read(2_000_001)
    if len(raw) > 2_000_000:
        raise HTTPException(413, "Rasm 2 MB dan kichik bo‘lishi kerak")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((1200, 1200))
            converted = img.convert("RGB")
            out = io.BytesIO()
            converted.save(out, format="WEBP", quality=82, method=5)
            safe_bytes = out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(422, "Rasm buzilgan yoki noto‘g‘ri formatda")
    photo = db.get(models.MenuPhoto, item_id)
    if photo is None:
        photo = models.MenuPhoto(menu_item_id=item_id)
        db.add(photo)
    photo.content_type = "image/webp"
    photo.binary_data = safe_bytes
    db.commit()
    base = os.getenv("PUBLIC_BASE_URL", "https://ali-kuryer.onrender.com").rstrip("/")
    return {"ok": True, "image_url": f"{base}/api/v1/menu-photo/{item_id}"}


@router.get("/menu-photo/{item_id}")
def get_menu_photo(item_id: int, db: Session = Depends(get_db)):
    photo = db.get(models.MenuPhoto, item_id)
    item = db.get(models.MenuItem, item_id)
    rest = db.get(models.Restaurant, item.restaurant_id) if item else None
    if not photo or not rest or not rest.is_approved:
        raise HTTPException(404, "Rasm topilmadi")
    return Response(photo.binary_data, media_type=photo.content_type,
                    headers={"Cache-Control": "public, max-age=900",
                             "X-Content-Type-Options": "nosniff"})


class AssistantOptInMessage(BaseModel):
    message: str = Field(min_length=2, max_length=600)
    retain_history: bool = False


@router.post("/assistant/chat")
async def logged_customer_assistant(data: AssistantOptInMessage,
                                    db: Session = Depends(get_db), user=Depends(me)):
    role(user, "customer")
    from app.routers.customer_experience import AssistantChatIn, assistant_chat
    result = await assistant_chat(AssistantChatIn(message=data.message))
    # Retain only with informed, explicit user opt-in.
    if data.retain_history:
        db.add(models.AssistantConversationLog(
            customer_id=user.id, question=data.message, answer=result["reply"]
        ))
        db.commit()
    return {"reply": result["reply"], "saved": bool(data.retain_history)}


@router.get("/assistant/history")
def my_assistant_history(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "customer")
    cutoff = datetime.utcnow() - timedelta(days=30)
    logs = db.query(models.AssistantConversationLog).filter(
        models.AssistantConversationLog.customer_id == user.id,
        models.AssistantConversationLog.created_at >= cutoff
    ).order_by(models.AssistantConversationLog.id.desc()).limit(100).all()
    return [{"id": item.id, "question": item.question, "answer": item.answer}
            for item in logs]


@router.delete("/assistant/history")
def delete_my_assistant_history(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "customer")
    db.query(models.AssistantConversationLog).filter_by(customer_id=user.id).delete()
    db.commit()
    return {"deleted": True}


@router.get("/admin/assistant-conversations")
def admin_assistant_history(db: Session = Depends(get_db), user=Depends(me)):
    role(user, "admin")
    cutoff = datetime.utcnow() - timedelta(days=30)
    # Keep retention limited, even if a periodic cleanup task is not running.
    db.query(models.AssistantConversationLog).filter(
        models.AssistantConversationLog.created_at < cutoff
    ).delete(synchronize_session=False)
    db.commit()
    logs = db.query(models.AssistantConversationLog).order_by(
        models.AssistantConversationLog.id.desc()
    ).limit(200).all()
    return [{"id": item.id, "customer_id": item.customer_id,
             "question": item.question, "answer": item.answer,
             "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in logs]
