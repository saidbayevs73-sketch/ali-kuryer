"""Explicitly provision an administrator in the database used by the API.

Never derive administrator permissions from client input and never overwrite the
password or role of an existing account. Bootstrap is disabled by default.
"""
import os
import re

from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app import models
from app.security import hash_password


def ensure_admin():
    if os.getenv("ALI_ADMIN_BOOTSTRAP_ENABLED") != "1":
        return

    phone = os.getenv("ADMIN_PHONE", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    # Misconfiguration must not take the ordering site offline.
    if not re.fullmatch(r"\+998[0-9]{9}", phone) or len(password) < 12:
        print("Ali Kuryer admin bootstrap: configuration incomplete", flush=True)
        return

    with SessionLocal() as session:
        existing = session.query(models.User).filter_by(phone=phone).first()
        if existing:
            if existing.role == "admin":
                print("Ali Kuryer admin bootstrap: existing admin retained", flush=True)
            else:
                print("Ali Kuryer admin bootstrap: phone belongs to another role", flush=True)
            return

        admin = models.User(
            name="Ali Kuryer Administrator",
            phone=phone,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        session.add(admin)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print("Ali Kuryer admin bootstrap: account already created", flush=True)
            return
        # Do not log usernames, phone numbers, passwords, hashes or tokens.
        print("Ali Kuryer: first admin account provisioned", flush=True)
