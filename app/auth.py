
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import SessionLocal
from app import models, schemas, security

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", status_code=201)
def register(data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    phone = data.phone.strip()

    if not phone.startswith("+998") or len(phone) != 13 or not phone[1:].isdigit():
        raise HTTPException(status_code=400, detail="Telefon raqami noto'g'ri")

    existing = db.query(models.User).filter(models.User.phone == phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Bu raqam ro'yxatdan o'tgan")

    user = models.User(
        phone=phone,
        name=data.name.strip(),
        password_hash=security.hash_password(data.password),
        role="customer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Ro'yxatdan o'tildi", "user_id": user.id}


@router.post("/login")
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.phone == data.phone.strip()).first()

    if not user or not user.is_active or not user.password_hash or not security.verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Telefon yoki parol noto'g'ri")

    token = security.create_access_token({"sub": str(user.id), "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
    }
