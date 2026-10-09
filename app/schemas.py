from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    # Used by app/auth.py
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=13, max_length=13)
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    # Used by app/auth.py
    phone: str
    password: str


# Preserve older schema names for callers that already import them.
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=9, max_length=20)


class UserLogin(LoginRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RestaurantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class MenuItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: int
    description: Optional[str] = None


class OrderCreate(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(min_length=5)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    payment_method: str = "cash"
