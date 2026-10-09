
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(30), unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(30), default="customer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    address = Column(String(255), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_approved = Column(Boolean, default=False)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    name = Column(String(150), nullable=False)
    price = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"))
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"))
    courier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    address = Column(String(500), nullable=False)
    total = Column(Float, default=0)
    status = Column(String(50), default="pending")
    payment_method = Column(String(30), default="cash")
    created_at = Column(DateTime, server_default=func.now())


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"))
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)


class PartnerApplication(Base):
    __tablename__ = "partner_applications"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(20), nullable=False)
    full_name = Column(String(120), nullable=False)
    phone = Column(String(20), nullable=False)
    city = Column(String(100), nullable=False)
    detail = Column(String(1000), nullable=False, default="")
    status = Column(String(20), nullable=False, default="new")
    created_at = Column(DateTime, server_default=func.now())


class GoogleIdentity(Base):
    __tablename__ = "google_identities"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String(160), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())


# New tables only: these do not change existing production table columns.
class DeliveryInfo(Base):
    __tablename__ = "order_delivery_info"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=False)
    note = Column(String(500), nullable=False, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


class CourierPresence(Base):
    __tablename__ = "courier_presence"
    courier_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_available = Column(Boolean, nullable=False, default=False)
    tracking_consent = Column(Boolean, nullable=False, default=False)
    last_seen_at = Column(DateTime, server_default=func.now(), nullable=False)


class RestaurantGeo(Base):
    __tablename__ = "restaurant_geo"
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True, index=True)
    support_customer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(String(1000), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class MenuExtra(Base):
    __tablename__ = "menu_extra"
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), primary_key=True)
    category = Column(String(60), nullable=False, default="")
    description = Column(String(400), nullable=False, default="")
