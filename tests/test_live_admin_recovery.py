"""Regression tests for legacy-startup resilience and safe existing admin recovery.

These tests use only the local test SQLite database.
"""
import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/ali_kuryer_ci_customer.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "only-for-regression-tests")

from app.bootstrap import ensure_admin
from app.database import SessionLocal
from app.models import User, AdminPasswordResetEvent
from app.security import hash_password, verify_password
from legacy_customer_api import _protect_missing_legacy_admin, _strong_legacy_admin_password
import hashlib


def test_legacy_site_starts_without_exposing_admin_if_secret_missing():
    legacy = {"ADMIN_PASSWORD": "ChangeMe_123!"}
    assert _protect_missing_legacy_admin(legacy) is False
    assert legacy["ADMIN_PASSWORD"] != "ChangeMe_123!"
    assert legacy["ADMIN_PASSWORD"] != "admin"
    assert len(legacy["ADMIN_PASSWORD"]) >= 20
    invalid = {"ADMIN_PASSWORD": "admin"}
    assert _protect_missing_legacy_admin(invalid) is False
    assert len(invalid["ADMIN_PASSWORD"]) >= 20
    valid = {"ADMIN_PASSWORD": "StrongOwner-Secret-2026!"}
    assert _protect_missing_legacy_admin(valid) is True
    assert valid["ADMIN_PASSWORD"] == "StrongOwner-Secret-2026!"
    assert _strong_legacy_admin_password("admin") is False


def test_existing_admin_can_be_recovered_even_if_old_bootstrap_secret_missing(monkeypatch):
    phone = "+998901118898"
    reset_id = "Recovery_20261011_Test_OneTime_783684"
    new_password = "NewAdmin-Recovery-Test#2026!"
    event_id = hashlib.sha256(reset_id.encode()).hexdigest()
    monkeypatch.setenv("ALI_ADMIN_BOOTSTRAP_ENABLED", "1")
    monkeypatch.setenv("ADMIN_PHONE", phone)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("ALI_ADMIN_RESET_REQUEST_ID", reset_id)
    monkeypatch.setenv("ALI_ADMIN_RESET_PASSWORD", new_password)
    with SessionLocal() as db:
        db.query(AdminPasswordResetEvent).filter_by(id=event_id).delete()
        db.query(User).filter_by(phone=phone).delete()
        db.add(User(name="Existing test admin", phone=phone,
                    role="admin", is_active=True,
                    password_hash=hash_password("OldAdmin-Test-2026!")))
        db.commit()
    try:
        ensure_admin()
        with SessionLocal() as db:
            user = db.query(User).filter_by(phone=phone).first()
            assert user is not None
            assert verify_password(new_password, user.password_hash)
        ensure_admin()
        with SessionLocal() as db:
            assert db.query(AdminPasswordResetEvent).filter_by(id=event_id).count() == 1
    finally:
        with SessionLocal() as db:
            db.query(AdminPasswordResetEvent).filter_by(id=event_id).delete()
            db.query(User).filter_by(phone=phone).delete()
            db.commit()
