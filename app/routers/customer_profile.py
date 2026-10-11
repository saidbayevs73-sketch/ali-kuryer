"""Customer contact details. Social login authenticates the ACCOUNT, not the phone.
A user-entered phone is stored as unverified contact data only.
"""
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.database import Base
from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/api/customer/account", tags=["Customer Contact"])
PHONE = re.compile(r"^\+998[0-9]{9}$")


class CustomerContactProfile(Base):
    __tablename__ = "customer_contact_profiles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    first_name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    contact_phone = Column(String(13), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ContactProfileIn(BaseModel):
    first_name: str = Field(min_length=2, max_length=80)
    last_name: str = Field(min_length=2, max_length=80)
    contact_phone: str = Field(min_length=13, max_length=13)


def customer_only(user):
    if not user.is_active or user.role != "customer":
        raise HTTPException(403, "Faqat mijoz hisobiga ruxsat bor")


def view(profile):
    return {
        "first_name": profile.first_name if profile else "",
        "last_name": profile.last_name if profile else "",
        "contact_phone": profile.contact_phone if profile else "",
        "phone_verified": False,  # User-supplied number is NOT an ownership proof.
        "complete": bool(profile),
    }


@router.get("/profile")
def get_customer_profile(db: Session = Depends(get_db), user=Depends(get_current_user)):
    customer_only(user)
    return view(db.get(CustomerContactProfile, user.id))


@router.put("/profile")
def update_customer_profile(data: ContactProfileIn, db: Session = Depends(get_db),
                            user=Depends(get_current_user)):
    customer_only(user)
    first, last, phone = data.first_name.strip(), data.last_name.strip(), data.contact_phone.strip()
    if len(first) < 2 or len(last) < 2 or not PHONE.fullmatch(phone):
        raise HTTPException(422, "Ism, familiya yoki +998 telefon raqamini tekshiring")
    existing = db.get(CustomerContactProfile, user.id)
    if existing:
        existing.first_name, existing.last_name, existing.contact_phone = first, last, phone
    else:
        db.add(CustomerContactProfile(
            user_id=user.id, first_name=first, last_name=last, contact_phone=phone
        ))
    user.name = (first + " " + last)[:150]
    # Never set user.phone, VerifiedPhone, or phone_verified on an unchecked number.
    db.commit()
    return {"message": "Profil saqlandi. SMS-kod talab qilinmaydi.", **view(db.get(CustomerContactProfile, user.id))}
