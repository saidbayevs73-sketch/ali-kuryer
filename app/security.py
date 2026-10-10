
from datetime import datetime, timedelta, timezone
import hmac
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

def create_access_token(data: dict, expires_minutes: int = 60 * 24):
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def admin_password_version(password_hash: str) -> str:
    """Bind each admin JWT to current password; changes revoke old admin JWTs."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        password_hash.encode("utf-8"), hashlib.sha256
    ).hexdigest()[:32]


def admin_access_token(user) -> str:
    return create_access_token({
        "sub": str(user.id), "role": "admin",
        "admin_pwdv": admin_password_version(user.password_hash)
    })
