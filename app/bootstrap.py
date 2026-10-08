import os

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models


def ensure_admin():
    phone = os.getenv("ADMIN_PHONE")
    password = os.getenv("ADMIN_PASSWORD")

    if not phone or not password:
        return

    # Administratorni yaratish uchun foydalanuvchi modeli
    # va parolni xavfsiz xeshlash tizimi kerak.
    # Hozircha administrator avtomatik yaratilmaydi.
    return
