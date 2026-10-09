
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


# Additional tables are additive; existing order/customer records are not modified.
class DeliveryDetail(Base):
    __tablename__ = "delivery_details"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False, index=True)
    recipient_name = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)
    street = Column(String(160), nullable=False)
    house = Column(String(40), nullable=False)
    entrance = Column(String(40), default="")
    floor = Column(String(40), default="")
    apartment = Column(String(40), default="")
    note = Column(String(300), default="")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    tracking_token = Column(String(80), unique=True, nullable=False, index=True)


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(30), nullable=False)
    message = Column(String(1500), nullable=False)
    status = Column(String(30), default="new")
    reply = Column(String(2000), default="")
    created_at = Column(DateTime, server_default=func.now())


class CourierShift(Base):
    __tablename__ = "courier_shifts"

    id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    selfie_path = Column(String(300), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(30), default="pending")
    created_at = Column(DateTime, server_default=func.now())


class CourierLocation(Base):
    __tablename__ = "courier_locations"

    courier_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
