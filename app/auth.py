
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import SessionLocal
from app import models, schemas, security, otp
from app.dependencies import get_current_user as shared_get_current_user
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PhoneRequest(BaseModel):
    phone: str = Field(min_length=13, max_length=13)


class PhoneConfirmation(PhoneRequest):
    otp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("/otp/request")
def request_registration_sms(data: PhoneRequest, db: Session = Depends(get_db)):
    """Send an SMS only to a phone not already registered."""
    phone = data.phone.strip()
    otp.validate_phone(phone)
    if db.query(models.User).filter_by(phone=phone).first():
        raise HTTPException(409, "Bu telefon raqami oldin ro‘yxatdan o‘tgan")
    return otp.request_otp(db, phone)


@router.get("/phone/status")
def phone_status(user: models.User = Depends(shared_get_current_user),
                 db: Session = Depends(get_db)):
    verified = db.get(models.VerifiedPhone, user.phone) if user.phone else None
    return {"phone": user.phone, "verified": bool(verified and verified.user_id == user.id)}


@router.post("/phone/request")
def request_existing_customer_sms(
    data: PhoneRequest,
    user: models.User = Depends(shared_get_current_user),
    db: Session = Depends(get_db),
):
    """For existing/unverified or Google customer accounts."""
    if user.role != "customer" or not user.is_active:
        raise HTTPException(403, "Faqat mijoz hisobi")
    phone = data.phone.strip()
    otp.validate_phone(phone)
    if user.phone and user.phone != phone:
        raise HTTPException(403, "Telefon raqamini almashtirish alohida tasdiq talab qiladi")
    other = db.query(models.User).filter_by(phone=phone).first()
    if other and other.id != user.id:
        raise HTTPException(409, "Telefon boshqa hisobga tegishli")
    return otp.request_otp(db, phone)


@router.post("/phone/confirm")
def confirm_existing_customer_phone(
    data: PhoneConfirmation,
    user: models.User = Depends(shared_get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "customer" or not user.is_active:
        raise HTTPException(403, "Faqat mijoz hisobi")
    phone = data.phone.strip()
    if user.phone and user.phone != phone:
        raise HTTPException(403, "Telefon raqami mos emas")
    other = db.query(models.User).filter_by(phone=phone).first()
    if other and other.id != user.id:
        raise HTTPException(409, "Telefon boshqa hisobga tegishli")
    otp.consume_otp(db, phone, data.otp_code)
    if not user.phone:
        user.phone = phone
    otp.mark_verified(db, phone, user.id)
    from sqlalchemy.exc import IntegrityError
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bu telefon raqami band")
    return {"verified": True}


@router.post("/register", status_code=201)
def register(data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    phone = data.phone.strip()

    if not phone.startswith("+998") or len(phone) != 13 or not phone[1:].isdigit():
        raise HTTPException(status_code=400, detail="Telefon raqami noto'g'ri")

    existing = db.query(models.User).filter(models.User.phone == phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="Bu raqam ro'yxatdan o'tgan")

    # Reject fabricated phone numbers: a server-generated SMS OTP must be
    # valid, unexpired and entered by the user before the account is created.
    otp.consume_otp(db, phone, data.otp_code)
    user = models.User(
        phone=phone,
        name=data.name.strip(),
        password_hash=security.hash_password(data.password),
        role="customer",
    )
    from sqlalchemy.exc import IntegrityError
    try:
        db.add(user)
        db.flush()
        otp.mark_verified(db, phone, user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bu raqam allaqachon band")
    db.refresh(user)

    return {"message": "Telefon SMS orqali tasdiqlandi", "user_id": user.id}


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



class GoogleCredentialRequest(BaseModel):
    credential: str


@router.post("/google")
def google_login(data: GoogleCredentialRequest, db: Session = Depends(get_db)):
    """Verify a Google Identity Services ID token on the server, then sign in."""
    import os

    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token
    from sqlalchemy.exc import IntegrityError

    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google orqali kirish hali sozlanmagan")
    try:
        claims = id_token.verify_oauth2_token(
            data.credential, GoogleRequest(), audience=client_id
        )
    except Exception:
        # Never include the token or token-verifier error in API responses.
        raise HTTPException(status_code=401, detail="Google tasdiqlashi muvaffaqiyatsiz") from None

    if claims.get("email_verified") is not True or not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Google hisob tasdiqlanmagan")

    subject = str(claims["sub"])
    identity = db.query(models.GoogleIdentity).filter_by(google_sub=subject).first()
    if identity:
        user = db.get(models.User, identity.user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Hisob faol emas")
    else:
        # Do not silently link an existing phone/password account on email alone.
        user = models.User(
            name=str(claims.get("name") or "Mijoz")[:150],
            phone=None,
            role="customer",
            is_active=True,
        )
        db.add(user)
        try:
            db.flush()
            db.add(models.GoogleIdentity(google_sub=subject, user_id=user.id))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Kirishni qayta urinib ko‘ring")
    access_token = security.create_access_token(
        {"sub": str(user.id), "role": "customer"}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "customer",
        "name": user.name,
    }


@router.get("/me")
def profile(user: models.User = Depends(shared_get_current_user)):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hisob faol emas")
    return {
        "id": user.id,
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
    }
