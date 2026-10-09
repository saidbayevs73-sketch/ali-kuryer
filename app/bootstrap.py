"""Create the initial admin account only when securely configured.

No default credentials. The bootstrap never promotes existing customers.
"""
import os
import re
import logging

from app.database import SessionLocal
from app import models, security

log = logging.getLogger(__name__)


def ensure_admin():
    phone = os.getenv("ADMIN_PHONE", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    if not phone or not password:
        return
    if not re.fullmatch(r"\+998\d{9}", phone) or len(password.encode("utf-8")) < 12:
        log.warning("ADMIN_PHONE or ADMIN_PASSWORD invalid; admin not created")
        return

    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.phone == phone).first()
        if user:
            if user.role != "admin":
                log.warning("ADMIN_PHONE already belongs to another role; not promoting")
            return
        db.add(models.User(
            name="Ali Kuryer Admin",
            phone=phone,
            password_hash=security.hash_password(password),
            role="admin",
            is_active=True,
        ))
        db.commit()
