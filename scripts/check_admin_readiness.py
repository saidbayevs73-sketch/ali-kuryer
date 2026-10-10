"""Read-only, secret-free Ali Kuryer API admin readiness diagnostic.

Execute inside the API service/container with its existing environment:
    python scripts/check_admin_readiness.py

Never print connection strings, phone numbers, passwords, database rows,
hashes or reset identifiers. It makes no database writes.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text
from app.database import DATABASE_URL, engine


def _is_valid_phone(phone):
    return bool(re.fullmatch(r"\+998[0-9]{9}", phone or ""))


def _strong_password(password):
    return (
        14 <= len(password) <= 72
        and len(password.encode("utf-8")) <= 72
        and bool(re.search(r"[A-Z]", password))
        and bool(re.search(r"[a-z]", password))
        and bool(re.search(r"[0-9]", password))
        and bool(re.search(r"[^A-Za-z0-9]", password))
    )


def nonsecret_configuration():
    reset_id = os.getenv("ALI_ADMIN_RESET_REQUEST_ID", "").strip()
    reset_password = os.getenv("ALI_ADMIN_RESET_PASSWORD", "")
    phone = os.getenv("ADMIN_PHONE", "").strip()
    return {
        "database_type": "postgresql" if DATABASE_URL.startswith("postgresql") else
                         ("sqlite" if DATABASE_URL.startswith("sqlite") else "other"),
        "admin_login": "admin",
        "bootstrap_enabled": os.getenv("ALI_ADMIN_BOOTSTRAP_ENABLED", "") == "1",
        "admin_phone_valid": _is_valid_phone(phone),
        "initial_password_valid": _strong_password(os.getenv("ADMIN_PASSWORD", "")),
        "recovery_id_valid": bool(re.fullmatch(r"[a-zA-Z0-9_-]{20,128}", reset_id)),
        "recovery_password_valid": _strong_password(reset_password),
        "recovery_requested": bool(reset_id and reset_password),
        # For diagnostic use inside a service; do not print the secrets.
        "_reset_digest": hashlib.sha256(reset_id.encode("utf-8")).hexdigest() if reset_id else None,
        "_owner_phone": phone if _is_valid_phone(phone) else None,
    }


def readiness_report():
    config = nonsecret_configuration()
    report = {key: value for key, value in config.items() if not key.startswith("_")}
    report.update({
        "database_connected": False, "has_users_table": False,
        "has_reset_events_table": False,
        "owner_admin_active": False, "reset_request_already_applied": False,
        "schema_error": None,
    })
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1")).scalar()
            report["database_connected"] = True
            inspector = inspect(conn)
            has_users = inspector.has_table("users")
            has_reset_events = inspector.has_table("admin_password_reset_events")
            report["has_users_table"] = has_users
            report["has_reset_events_table"] = has_reset_events
            if has_users and config["_owner_phone"]:
                row = conn.execute(
                    text("SELECT role, is_active, password_hash FROM users WHERE phone=:phone"),
                    {"phone": config["_owner_phone"]},
                ).first()
                report["owner_admin_active"] = bool(
                    row and row.role == "admin" and row.is_active and row.password_hash
                )
            if has_reset_events and config["_reset_digest"]:
                row = conn.execute(
                    text("SELECT id FROM admin_password_reset_events WHERE id=:digest"),
                    {"digest": config["_reset_digest"]},
                ).first()
                report["reset_request_already_applied"] = bool(row)
    except Exception as exc:
        # Only the exception class; database exceptions often embed private URLs.
        report["schema_error"] = type(exc).__name__
    # Ephemeral database is never considered ready for production rotation.
    report["safe_for_production_admin_password_rotation"] = bool(
        report["database_connected"]
        and report["database_type"] == "postgresql"
        and report["has_users_table"]
        and report["has_reset_events_table"]
        and report["owner_admin_active"]
    )
    return report


if __name__ == "__main__":
    result = readiness_report()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    sys.exit(0 if result["database_connected"] else 2)
