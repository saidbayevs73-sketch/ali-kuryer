"""Provision the first API administrator only when explicitly enabled in Render.

Never derive admin accounts from client input, expose credentials or reset an
existing administrator on every restart.
"""
import os
import re
from app.database import SessionLocal, DATABASE_URL
from app import models
from app.security import hash_password


def ensure_admin():
    if os.getenv("ALI_ADMIN_BOOTSTRAP_ENABLED") != "1":
        return
    if not DATABASE_URL.startswith("postgresql"):
        raise RuntimeError("Admin bootstrap requires the persistent PostgreSQL database")
    phone = os.getenv("ADMIN_PHONE", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not re.fullmatch(r"\+998[0-9]{9}", phone) or len(password) < 12:
        raise RuntimeError("Admin bootstrap requires a valid ADMIN_PHONE and strong ADMIN_PASSWORD")
    with SessionLocal() as session:
        exists = session.query(models.User).filter_by(phone=phone).first()
        if exists:
            if exists.role != "admin":
                raise RuntimeError("ADMIN_PHONE already belongs to a non-admin account")
            return
        admin = models.User(
            name="Ali Kuryer Administrator", phone=phone,
            password_hash=hash_password(password), role="admin", is_active=True
        )
        session.add(admin)
        session.commit()
        # Do not print phone, password, hashes or token.
        print("Ali Kuryer: first admin account provisioned", flush=True)
