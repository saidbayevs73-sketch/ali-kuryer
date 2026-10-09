
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=9, max_length=20)


class UserLogin(BaseModel):
    phone: str
    password: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=150, pattern=r"\S")
    phone: str = Field(min_length=13, max_length=30)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class LoginRequest(UserLogin):
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
