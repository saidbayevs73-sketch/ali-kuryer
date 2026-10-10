"""Explicitly provision an administrator in the database used by the API.

Never derive administrator permissions from client input and never overwrite the
password or role of an existing account. Bootstrap is disabled by default.
"""
import os
import re
import hashlib
from sqlalchemy.exc import IntegrityError


from app.database import SessionLocal
from app import models
from app.security import hash_password




def maybe_reset_existing_admin(session, existing):
    """Owner-initiated one-time recovery via Render secret variables.

    Requires an explicit unpredictable reset ID and strong new password.
    Reusing a reset ID never resets again, even after user changes it in-app.
    """
    reset_id = os.getenv("ALI_ADMIN_RESET_REQUEST_ID", "").strip()
    proposed = os.getenv("ALI_ADMIN_RESET_PASSWORD", "")
    if not reset_id or not proposed:
        return
    if not re.fullmatch(r"[a-zA-Z0-9_-]{20,128}", reset_id):
        print("Ali Kuryer admin recovery: invalid request ID", flush=True)
        return
    from app.auth import validate_strong_admin_password
    from fastapi import HTTPException
    try:
        validate_strong_admin_password(proposed)
    except HTTPException:
        print("Ali Kuryer admin recovery: password policy not met", flush=True)
        return
    from app.auth import require_durable_admin_password_store
    try:
        require_durable_admin_password_store()
    except HTTPException:
        print("Ali Kuryer admin recovery: persistent PostgreSQL database required", flush=True)
        return
    record_id = hashlib.sha256(reset_id.encode("utf-8")).hexdigest()
    if session.get(models.AdminPasswordResetEvent, record_id):
        print("Ali Kuryer admin recovery: request already applied", flush=True)
        return
    existing.password_hash = hash_password(proposed)
    session.add(models.AdminPasswordResetEvent(id=record_id))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        print("Ali Kuryer admin recovery: request already completed", flush=True)
        return
    print("Ali Kuryer admin recovery: one-time password rotation completed", flush=True)

def ensure_admin():
    if os.getenv("ALI_ADMIN_BOOTSTRAP_ENABLED") != "1":
        return

    # A transient account that disappears at the next Render restart is
    # worse than a configuration error. Never create or rotate production
    # administrator credentials on nonpersistent SQLite storage.
    from app.auth import require_durable_admin_password_store
    from fastapi import HTTPException
    try:
        require_durable_admin_password_store()
    except HTTPException:
        print("Ali Kuryer admin bootstrap: persistent PostgreSQL database required", flush=True)
        return

    phone = os.getenv("ADMIN_PHONE", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")
    # An existing admin may recover via one-time reset even when the old
    # ADMIN_PASSWORD value is no longer available. Never create a weak admin.
    if not re.fullmatch(r"\+998[0-9]{9}", phone):
        print("Ali Kuryer admin bootstrap: valid ADMIN_PHONE required", flush=True)
        return

    with SessionLocal() as session:
        existing = session.query(models.User).filter_by(phone=phone).first()
        if existing:
            if existing.role == "admin":
                print("Ali Kuryer admin bootstrap: existing admin retained", flush=True)
                maybe_reset_existing_admin(session, existing)
            else:
                print("Ali Kuryer admin bootstrap: phone belongs to another role", flush=True)
            return

        # Only a brand-new admin requires ADMIN_PASSWORD. Existing admins are
        # changed solely by a strong, one-time recovery request.
        from app.auth import validate_strong_admin_password
        from fastapi import HTTPException
        try:
            validate_strong_admin_password(password)
        except HTTPException:
            print("Ali Kuryer admin bootstrap: strong initial password required", flush=True)
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
        # Initial admin remains provisioned using ADMIN_PASSWORD. A reset
        # request is recorded only if a separately approved rotation occurs.
        if os.getenv("ALI_ADMIN_RESET_REQUEST_ID") and os.getenv("ALI_ADMIN_RESET_PASSWORD"):
            maybe_reset_existing_admin(session, admin)
