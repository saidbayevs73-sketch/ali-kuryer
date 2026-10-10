
import os
from fastapi import APIRouter, Depends, HTTPException, Request, status
from app.admin_login_guard import owner_login_guard
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


@router.get("/options")
def customer_auth_options():
    """Public, nonsecret readiness of customer verification providers.

    No credentials, connection strings, OTPs or personally identifying details
    are returned. Read-only: does not create users or contact SMS gateways.
    """
    import os
    from app import telegram_login
    try:
        otp.require_otp_ready()
        sms_available = True
    except HTTPException:
        sms_available = False
    telegram_available = telegram_login.service_ready()
    google_available = bool(os.getenv("GOOGLE_CLIENT_ID", "").strip())
    return {
        "password_login": True,  # existing phone/password users
        "username_signup": _username_signup_ready(),
        "contact_signup": _contact_signup_ready(),
        "sms_registration": sms_available,
        "sms_verification": sms_available,
        "telegram_login": telegram_available,
        "google_login": google_available,
        "message": (
            "SMS orqali ro‘yxatdan o‘tish mavjud."
            if sms_available else
            "SMS tasdiqlash xizmati hozircha tayyor emas. "
            "Mavjud hisobingiz bo‘lsa, parol bilan kiring. "
            "Yangi mijozlar uchun boshqa tasdiqlash usuli mavjud bo‘lsa, uni tanlang."
        ),
    }



from app.admin_login_guard import AdminLoginThrottle

customer_contact_guard = AdminLoginThrottle(max_failures=8, window_seconds=300)
customer_signup_guard = AdminLoginThrottle(max_failures=5, window_seconds=3600)


class ContactRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=13, max_length=13, pattern=r"^\+998[0-9]{9}$")
    password: str = Field(min_length=10, max_length=72)
    accepted_privacy: bool


class ContactLoginRequest(BaseModel):
    phone: str = Field(min_length=13, max_length=13, pattern=r"^\+998[0-9]{9}$")
    password: str = Field(min_length=1, max_length=72)


def _contact_signup_ready() -> bool:
    from app.database import DATABASE_URL
    production = os.getenv("RENDER", "").lower() in {"true", "1", "yes"} or (
        os.getenv("ENVIRONMENT", "").lower() == "production")
    return (
        os.getenv("ALI_CONTACT_SIGNUP_ENABLED") == "1"
        and (not production or DATABASE_URL.startswith("postgresql"))
        and (not production or len(os.getenv("SECRET_KEY", "").encode("utf-8")) >= 32)
    )


def _require_contact_signup_ready() -> None:
    if not _contact_signup_ready():
        raise HTTPException(
            503, "SMSsiz ro‘yxatdan o‘tish doimiy baza va xavfsizlik "
                 "sozlamalari tayyor bo‘lgach ishga tushadi.")


@router.post("/contact/register", status_code=201)
def register_contact_customer(data: ContactRegisterRequest, request: Request,
                              db: Session = Depends(get_db)):
    """No SMS, no false verification and no unverified phone ownership claim."""
    import os
    from sqlalchemy.exc import IntegrityError
    _require_contact_signup_ready()
    peer = request.client.host if request.client else "unknown"
    if customer_signup_guard.blocked(peer):
        raise HTTPException(429, "Ro‘yxatdan o‘tish urinishlari ko‘p. Keyinroq qayta urinib ko‘ring.")
    if not data.accepted_privacy:
        raise HTTPException(422, "Maxfiylik shartlarini qabul qiling")
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(422, "Parol 72 baytdan oshmasin")
    if len(data.name.strip()) < 2:
        raise HTTPException(422, "Ism kamida ikki belgidan iborat bo‘lsin")
    security.require_secure_jwt_key()
    # No account is linked to an existing verified customer by phone alone.
    # User.phone remains NULL; verified identities keep their own ownership.
    user = models.User(
        name=data.name.strip(), phone=None, role="customer",
        password_hash=security.hash_password(data.password), is_active=True
    )
    db.add(user)
    try:
        db.flush()
        db.add(models.UnverifiedCustomerContact(user_id=user.id, phone=data.phone))
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ro‘yxatdan o‘tish amalga oshmadi. Qayta urinib ko‘ring")
    customer_signup_guard.fail(peer)  # successful account creation also counts toward quota
    return {
        "access_token": security.create_access_token(
            {"sub": str(user.id), "role": "customer"}),
        "token_type": "bearer",
        "role": "customer",
        "phone_verified": False,
        "message": "Kabinet yaratildi. Telefon faqat aloqa uchun, tasdiqlanmagan."
    }


@router.post("/contact/login")
def login_contact_customer(data: ContactLoginRequest, request: Request,
                           db: Session = Depends(get_db)):
    """Phone + password for contact-only accounts; no proof of phone ownership."""
    _require_contact_signup_ready()
    peer = request.client.host if request.client else "unknown"
    if customer_contact_guard.blocked(peer):
        raise HTTPException(429, "Ko‘p noto‘g‘ri urinish. 5 daqiqadan keyin urinib ko‘ring.",
                            headers={"Retry-After": "300"})
    matches = db.query(models.UnverifiedCustomerContact).filter_by(phone=data.phone).limit(10).all()
    authenticated = []
    for contact in matches:
        user = db.get(models.User, contact.user_id)
        if user and user.role == "customer" and user.is_active and user.password_hash:
            if security.verify_password(data.password, user.password_hash):
                authenticated.append(user)
    if len(authenticated) != 1:
        customer_contact_guard.fail(peer)
        raise HTTPException(401, "Telefon yoki parol noto‘g‘ri")
    customer_contact_guard.success(peer)
    user = authenticated[0]
    return {
        "access_token": security.create_access_token({"sub": str(user.id), "role": "customer"}),
        "role": "customer", "token_type": "bearer", "phone_verified": False
    }


class UsernameRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=72)
    accepted_privacy: bool


class UsernameLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=72)


def _username_signup_ready() -> bool:
    import os
    from app.database import DATABASE_URL
    # A free Render instance may lose its SQLite on restart.
    production = os.getenv("RENDER", "").lower() in {"true", "1", "yes"} or (
        os.getenv("ENVIRONMENT", "").lower() == "production"
    )
    permanent = not production or DATABASE_URL.startswith("postgresql")
    return os.getenv("ALI_USERNAME_LOGIN_ENABLED") == "1" and permanent


def _require_username_signup_ready() -> None:
    if not _username_signup_ready():
        raise HTTPException(503,
            "Login nomi va parol bilan ro‘yxatdan o‘tish doimiy baza ulangandan "
            "keyin ishga tushadi. Ma’lumotlaringiz yo‘qolmasligi uchun hozir yopiq.")


def _normalize_customer_username(value: str) -> str:
    import re
    username = value.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9_.]{2,31}", username):
        raise HTTPException(422, "Login nomi 3–32 ta lotin harfi, raqam, _ yoki . dan iborat bo‘lsin; harf bilan boshlansin")
    if username in {"admin", "administrator", "support", "operator", "courier",
                    "restaurant", "root", "staff", "alikuryer", "muhammadali"}:
        raise HTTPException(422, "Bu login nomi xizmat uchun band")
    return username


@router.get("/username/status")
def customer_username_status():
    """Only a public readiness flag. No secrets, connection strings or users."""
    return {
        "available": _username_signup_ready(),
        "message": ("Login nomi va parol bilan kabinet yaratish tayyor."
                    if _username_signup_ready() else
                    "Yangi kabinetni saqlash uchun doimiy baza va xavfsiz "
                    "ro‘yxatdan o‘tish xizmati sozlanmoqda."),
    }


@router.post("/username/register", status_code=201)
def register_customer_username(data: UsernameRegisterRequest,
                               db: Session = Depends(get_db)):
    """Customer account without falsely declaring any phone number verified."""
    from sqlalchemy.exc import IntegrityError
    _require_username_signup_ready()
    if not data.accepted_privacy:
        raise HTTPException(422, "Maxfiylik shartlarini qabul qiling")
    username = _normalize_customer_username(data.username)
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(422, "Parol 72 baytdan oshmasin")
    if db.get(models.UsernameIdentity, username):
        raise HTTPException(409, "Bu login nomi band. Boshqasini tanlang")
    name = data.name.strip()
    if len(name) < 2:
        raise HTTPException(422, "Ismingizni kiriting")
    user = models.User(name=name, phone=None,
                       password_hash=security.hash_password(data.password),
                       role="customer", is_active=True)
    db.add(user)
    db.flush()
    db.add(models.UsernameIdentity(username=username, user_id=user.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Bu login nomi band. Boshqasini tanlang")
    return {
        "message": "Mijoz kabineti yaratildi. Telefon raqami hali tasdiqlanmagan.",
        "username": username,
        "phone_verified": False,
    }


@router.post("/username/login")
def login_customer_username(data: UsernameLoginRequest,
                            db: Session = Depends(get_db)):
    _require_username_signup_ready()
    username = _normalize_customer_username(data.username)
    binding = db.get(models.UsernameIdentity, username)
    user = db.get(models.User, binding.user_id) if binding else None
    if (not user or user.role != "customer" or not user.is_active
            or not user.password_hash
            or not security.verify_password(data.password, user.password_hash)):
        raise HTTPException(401, "Login nomi yoki parol noto‘g‘ri")
    return {
        "access_token": security.create_access_token(
            {"sub": str(user.id), "role": "customer"}
        ),
        "token_type": "bearer", "role": "customer",
        "phone_verified": False if not user.phone else None,
    }


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



class AdminUsernameLogin(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)


@router.post("/admin/login")
def admin_username_login(data: AdminUsernameLogin, request: Request,
                         db: Session = Depends(get_db)):
    """Owner-only role, no shared default password; limit brute-force guesses.

    Key on the ASGI client address, never on user-controlled proxy headers.
    """
    import os
    import re
    peer = request.client.host if request.client else "unknown"
    if owner_login_guard.blocked(peer):
        raise HTTPException(
            status_code=429, detail="Ko‘p noto‘g‘ri urinish. 5 daqiqadan keyin qayta urinib ko‘ring.",
            headers={"Retry-After": "300"},
        )
    if data.username.strip().lower() != "admin":
        owner_login_guard.fail(peer)
        raise HTTPException(401, "Login yoki parol noto‘g‘ri")
    owner_phone = os.getenv("ADMIN_PHONE", "").strip()
    if not re.fullmatch(r"\+998[0-9]{9}", owner_phone):
        raise HTTPException(503, "Admin hisobi sozlanmagan. Render sozlamalarini tekshiring.")
    user = db.query(models.User).filter_by(phone=owner_phone).first()
    if not user or user.role != "admin" or not user.is_active or not user.password_hash or (
            not security.verify_password(data.password, user.password_hash)):
        owner_login_guard.fail(peer)
        raise HTTPException(401, "Login yoki parol noto‘g‘ri")
    owner_login_guard.success(peer)
    return {
        "access_token": security.admin_access_token(user),
        "token_type": "bearer", "role": "admin",
    }


class AdminChangePassword(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=14, max_length=72)


def validate_strong_admin_password(value: str) -> None:
    import re
    if (len(value.encode("utf-8")) > 72 or len(value) < 14 or
            not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or
            not re.search(r"[0-9]", value) or not re.search(r"[^A-Za-z0-9]", value) or
            value.lower() in {"admin", "admin123", "adminadmin"}):
        raise HTTPException(422,
            "Yangi parol kamida 14 belgidan iborat bo‘lsin: katta-kichik harf, raqam va belgi.")


def require_durable_admin_password_store() -> None:
    """Never claim that an admin password was saved on ephemeral Render SQLite.

    An account reset/change must survive deploys and service restarts.
    Local and CI test SQLite remain supported.
    """
    import os
    from app.database import DATABASE_URL
    deployed = os.getenv("ENVIRONMENT", "").lower() == "production" or (
        os.getenv("RENDER", "").lower() in {"1", "true", "yes"})
    if deployed and DATABASE_URL.startswith("sqlite"):
        raise HTTPException(
            503, "Admin parolini xavfsiz saqlash uchun doimiy PostgreSQL bazasi ulanishi kerak."
        )


@router.post("/admin/change-password")
def change_admin_password(data: AdminChangePassword,
                          user=Depends(shared_get_current_user),
                          db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(403, "Faqat admin o‘z parolini o‘zgartira oladi")
    require_durable_admin_password_store()
    # Resolve in the same session as the mutation.
    current = db.get(models.User, user.id)
    if not current or not current.is_active:
        raise HTTPException(401, "Admin sessiyasi yaroqsiz")
    if not current.password_hash or not security.verify_password(data.current_password, current.password_hash):
        raise HTTPException(401, "Joriy parol noto‘g‘ri")
    validate_strong_admin_password(data.new_password)
    if security.verify_password(data.new_password, current.password_hash):
        raise HTTPException(422, "Yangi parol oldingisidan farq qilishi kerak")
    current.password_hash = security.hash_password(data.new_password)
    db.commit()
    # Previous JWTs cease working due to password-hash-bound admin token version.
    return {"message": "Admin paroli yangilandi. Qayta tizimga kiring."}


@router.post("/login")
def login(data: schemas.LoginRequest, request: Request,
          db: Session = Depends(get_db)):
    import os
    import hmac
    phone = data.phone.strip()
    owner_phone = os.getenv("ADMIN_PHONE", "").strip()
    owner_attempt = bool(owner_phone) and hmac.compare_digest(phone, owner_phone)
    peer = request.client.host if request.client else "unknown"

    # Legacy operator pages may still use phone/password. Apply the same
    # throttle as /admin/login or it becomes a brute-force bypass.
    if owner_attempt and owner_login_guard.blocked(peer):
        raise HTTPException(
            status_code=429, detail="Ko‘p noto‘g‘ri urinish. 5 daqiqadan keyin qayta urinib ko‘ring.",
            headers={"Retry-After": "300"},
        )
    user = db.query(models.User).filter(models.User.phone == phone).first()
    # Additional admin accounts may not authenticate with this legacy route;
    # only the owner account configured for /admin/login is recognized.
    if (not user or not user.is_active or not user.password_hash or
            (user.role == "admin" and not owner_attempt) or
            not security.verify_password(data.password, user.password_hash)):
        if owner_attempt:
            owner_login_guard.fail(peer)
        raise HTTPException(status_code=401, detail="Telefon yoki parol noto'g'ri")
    if owner_attempt:
        owner_login_guard.success(peer)

    token = (security.admin_access_token(user) if user.role == "admin" else
             security.create_access_token({"sub": str(user.id), "role": user.role}))

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
    }




class FirebasePhoneLoginRequest(BaseModel):
    id_token: str = Field(min_length=100, max_length=8192)
    name: str = Field(default="Mijoz", max_length=150)


def validate_firebase_phone_token(firebase_token: str) -> tuple[str, str]:
    """Verify signature, issuer, audience and Firebase *phone* sign-in method.

    Uses Google's public signing certificates; no service account private key,
    Firebase API key or ID token is logged or trusted without verification.
    """
    import os
    import re
    from datetime import datetime, timezone
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token as google_id_token

    project = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    if project != "ali-kuryer" or os.getenv("FIREBASE_PHONE_ENABLED") != "1":
        raise HTTPException(503, "Firebase SMS tasdiqlash hali faollashtirilmagan")
    try:
        claims = google_id_token.verify_firebase_token(
            firebase_token, GoogleRequest(), audience=project
        )
    except Exception:
        raise HTTPException(401, "Firebase tasdiqlash tokeni yaroqsiz") from None
    if (
        claims.get("iss") != "https://securetoken.google.com/" + project
        or claims.get("aud") != project
        or not claims.get("sub")
        or claims.get("firebase", {}).get("sign_in_provider") != "phone"
    ):
        raise HTTPException(401, "Firebase telefon orqali tasdiqlamagan")
    phone = claims.get("phone_number", "")
    if not isinstance(phone, str) or not re.fullmatch(r"\+998\d{9}", phone):
        raise HTTPException(403, "Faqat O‘zbekiston telefon raqami qabul qilinadi")
    # OTP proof must correspond to a recent actual phone sign-in, not a very old
    # session's refresh token. Legitimate users can simply request a new SMS.
    auth_time = claims.get("auth_time")
    now = datetime.now(timezone.utc).timestamp()
    if not isinstance(auth_time, (int, float)) or auth_time > now + 30 or now - auth_time > 600:
        raise HTTPException(401, "Telefon tasdiqlash muddati tugagan. Yangi kod oling")
    return phone, str(claims["sub"])


@router.post("/firebase/phone-login")
def firebase_phone_login(data: FirebasePhoneLoginRequest, db: Session = Depends(get_db)):
    """Sign in/create CUSTOMER ONLY after real Firebase phone verification."""
    import os
    from sqlalchemy.exc import IntegrityError
    from app.database import DATABASE_URL
    from app import models

    # Render ephemeral SQLite cannot safely persist authenticated customers.
    if os.getenv("RENDER", "").lower() in {"true", "1", "yes"} and not DATABASE_URL.startswith("postgresql"):
        raise HTTPException(503, "Doimiy PostgreSQL bazasi ulanmaguncha SMS kirish yopiq")
    phone, firebase_uid = validate_firebase_phone_token(data.id_token)
    existing = db.query(models.User).filter_by(phone=phone).with_for_update().first()
    if existing and (existing.role != "customer" or not existing.is_active):
        raise HTTPException(403, "Ushbu raqam mijoz hisobi sifatida ishlatilmaydi")
    if not existing:
        name = data.name.strip()[:150] or "Mijoz"
        existing = models.User(
            name=name, phone=phone, password_hash=None,
            role="customer", is_active=True
        )
        db.add(existing)
        db.flush()
    # The unique firebase UID must never be bound to two different accounts.
    binding = db.query(models.FirebasePhoneIdentity).filter_by(firebase_uid=firebase_uid).first()
    if binding and binding.user_id != existing.id:
        raise HTTPException(409, "Firebase hisobi boshqa mijozga bog‘langan")
    if not binding:
        db.add(models.FirebasePhoneIdentity(
            firebase_uid=firebase_uid, user_id=existing.id, phone=phone
        ))
    proof = db.get(models.VerifiedPhone, phone)
    if proof and proof.user_id != existing.id:
        raise HTTPException(409, "Telefon raqami boshqa hisobda tasdiqlangan")
    if not proof:
        db.add(models.VerifiedPhone(phone=phone, user_id=existing.id))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Telefon allaqachon ro‘yxatga olingan")
    access_token = security.create_access_token({
        "sub": str(existing.id), "role": "customer"
    })
    return {"access_token": access_token, "token_type": "bearer", "role": "customer"}




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
def profile(user: models.User = Depends(shared_get_current_user),
            db: Session = Depends(get_db)):
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hisob faol emas")
    contact = db.get(models.UnverifiedCustomerContact, user.id) if user.role == "customer" else None
    phone = user.phone or (contact.phone if contact else None)
    proof = db.get(models.VerifiedPhone, user.phone) if user.phone else None
    verified = bool(proof and proof.user_id == user.id)
    return {
        "id": user.id, "name": user.name, "phone": phone, "role": user.role,
        "phone_verified": verified,
    }
