"""Offline, opt-in migration: legacy Ali Kuryer SQLite -> new PostgreSQL.

Runs INSIDE the legacy Render server after legacy writes are actually frozen.
Dry-run is the default; never put a database password in source control/logs.

Steps:
    ALI_LEGACY_DB_PATH=/var/data/ali_kuryer.db python scripts/migrate_legacy_to_postgres.py
    # Inspect backup and counts and separately freeze all old write routes.
    # Only after the freeze is independently verified:
    ALI_MIGRATION_CONFIRMED=yes ALI_LEGACY_WRITES_FROZEN=1 \
      ALI_LEGACY_DB_PATH=/var/data/ali_kuryer.db \
      DATABASE_URL=<Render internal Postgres URL from SECRET env> \
      python scripts/migrate_legacy_to_postgres.py --apply

Keep the legacy SQLite DB and the verified backup until reconciliation and
production traffic cutover are complete. Do NOT remove them on success.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def tables(db):
    return {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}


REQUIRED = {"customers", "restaurants", "menu_items", "orders", "order_items"}
KNOWN = REQUIRED | {
    "couriers", "web_order_details", "audit", "ratings",
    "tickets", "ticket_messages", "settings", "logs",
}
PHONE = re.compile(r"^\+998\d{9}$")


def safe_phone(value):
    if not value:
        return None
    p = re.sub(r"[\s()\-]", "", str(value).strip())
    if p.startswith("998") and len(p) == 12:
        p = "+" + p
    if p.startswith("0") and len(p) == 10:
        p = "+998" + p[1:]
    if len(p) == 9 and p.isdigit():
        p = "+998" + p
    return p if PHONE.fullmatch(p) else None


def rowdict(row):
    return dict(row) if row is not None else {}


def dt(value):
    if not value:
        return None
    try:
        value = str(value).replace("Z", "+00:00")
        d = datetime.fromisoformat(value)
        return d.replace(tzinfo=None) if d.tzinfo is None else d.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def status(value):
    s = str(value or "").strip().lower()
    if s in {"yetkazildi", "delivered", "completed"}:
        return "delivered"
    if s in {"bekor qilindi", "cancelled", "canceled"}:
        return "cancelled"
    if "kuryer" in s and ("qabul" in s or "biriktir" in s):
        return "assigned"
    if "yo'lda" in s or "yo‘lda" in s or "yetkazilmoqda" in s:
        return "delivering"
    if "tayyor" in s or s == "ready":
        return "ready"
    if "oshxona" in s or "prepar" in s:
        return "preparing"
    return "pending"


def snapshot(source_path):
    source = Path(source_path).resolve()
    if not source.is_file():
        raise RuntimeError("SQLite database file is missing. Aborting.")
    if not source.name.endswith((".db", ".sqlite", ".sqlite3")):
        raise RuntimeError("Unexpected source filename. Aborting.")
    size = source.stat().st_size
    disk = shutil.disk_usage(source.parent)
    if disk.free < max(size * 2 + 20_000_000, 30_000_000):
        raise RuntimeError("Not enough free disk space for verified backup.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = source.parent / (source.name + ".pre-postgres-" + stamp + ".sqlite")
    if dest.exists():
        raise RuntimeError("Backup name collision.")
    fd, temporary = tempfile.mkstemp(prefix=".ali-backup-", dir=str(source.parent))
    os.chmod(temporary, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect("file:" + str(source) + "?mode=ro", uri=True) as src:
            with sqlite3.connect(temporary) as dst:
                src.backup(dst, pages=250)
                if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Snapshot failed SQLite integrity check.")
                if not REQUIRED.issubset(tables(dst)):
                    raise RuntimeError("Missing required legacy tables. Aborting.")
        os.replace(temporary, dest)
        os.chmod(dest, 0o600)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return dest


def inspect(conn):
    found = tables(conn)
    if not REQUIRED.issubset(found):
        raise RuntimeError("Unexpected legacy schema; no migration possible.")
    counts = {
        key: conn.execute("SELECT COUNT(*) FROM " + key).fetchone()[0]
        for key in sorted(KNOWN & found)
    }
    dup = conn.execute(
        "SELECT COUNT(*) FROM (SELECT phone FROM customers "
        "WHERE phone IS NOT NULL AND phone!='' GROUP BY phone HAVING COUNT(*)>1)"
    ).fetchone()[0]
    statuses = dict(Counter(
        str(r[0] or "") for r in conn.execute("SELECT status FROM orders")
    ))
    return {"tables": counts, "duplicate_customer_phones": dup,
            "legacy_order_statuses": statuses}


def data_rows(conn, table):
    if table not in tables(conn):
        return []
    key = "order_id" if table == "web_order_details" else "id"
    return [rowdict(r) for r in conn.execute("SELECT * FROM " + table + " ORDER BY " + key)]


def perform_import(conn):
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
        raise RuntimeError("Import requires PostgreSQL DATABASE_URL from a secret environment variable.")
    if os.getenv("ALI_MIGRATION_CONFIRMED") != "yes":
        raise RuntimeError("Migration not explicitly confirmed.")
    if os.getenv("ALI_LEGACY_WRITES_FROZEN") != "1":
        raise RuntimeError("Legacy write operations must be frozen and verified first.")

    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from app import models
    from app.database import Base

    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Refusing to import to non-PostgreSQL database.")
    Base.metadata.create_all(bind=engine, checkfirst=True)

    # All five core tables must be empty. Never merge into a live database.
    with Session(engine) as db:
        count = {m.__tablename__: db.scalar(select(func.count()).select_from(m)) for m in (
            models.User, models.Restaurant, models.MenuItem, models.Order, models.OrderItem,
        )}
        if any(count.values()):
            raise RuntimeError("Target database already has core data: refuse overwrite or duplication.")

        customers = data_rows(conn, "customers")
        restaurants = data_rows(conn, "restaurants")
        couriers = data_rows(conn, "couriers")
        menus = data_rows(conn, "menu_items")
        orders = data_rows(conn, "orders")
        lines = data_rows(conn, "order_items")

        # Never import the legacy SHA-256/PBKDF2 passwords as if they were bcrypt.
        # Imported users/staff require verified new account provisioning.
        phones_used = set()
        def imported_phone(value):
            p = safe_phone(value)
            if not p or p in phones_used:
                return None
            phones_used.add(p)
            return p

        usermap = {}
        for c in customers:
            user = models.User(
                name=str(c.get("first_name") or "Mijoz")[:150],
                phone=imported_phone(c.get("phone")),
                password_hash=None, role="customer", is_active=False,
            )
            db.add(user)
            db.flush()
            usermap[c["id"]] = user.id

        ownermap = {}
        for r in restaurants:
            owner = models.User(
                name=("Oshxona: " + str(r.get("name") or ""))[:150],
                phone=None, password_hash=None, role="restaurant", is_active=False,
            )
            db.add(owner)
            db.flush()
            ownermap[r["id"]] = owner.id

        couriermap = {}
        for courier in couriers:
            u = models.User(
                name=str(courier.get("name") or "Kuryer")[:150],
                phone=imported_phone(courier.get("phone")),
                password_hash=None, role="courier", is_active=False,
            )
            db.add(u)
            db.flush()
            couriermap[courier["id"]] = u.id

        restaurantmap = {}
        for r in restaurants:
            item = models.Restaurant(
                name=str(r.get("name") or "Restoran")[:150],
                address=str(r.get("address") or "")[:255],
                owner_id=ownermap[r["id"]],
                is_approved=r.get("status") == "active",
            )
            db.add(item)
            db.flush()
            restaurantmap[r["id"]] = item.id
            if r.get("latitude") is not None and r.get("longitude") is not None:
                if -90 <= float(r["latitude"]) <= 90 and -180 <= float(r["longitude"]) <= 180:
                    db.add(models.RestaurantGeo(
                        restaurant_id=item.id,
                        latitude=float(r["latitude"]), longitude=float(r["longitude"])
                    ))

        menumap = {}
        for m in menus:
            rid = restaurantmap.get(m.get("restaurant_id"))
            if not rid:
                raise RuntimeError("Menu references unknown legacy restaurant. Aborting.")
            image_url = str(m.get("image_url") or "")
            # Local legacy upload paths cannot be served from the new FastAPI host.
            # They remain in the verified SQLite/disk backup until images are copied.
            if not image_url.startswith("https://"):
                image_url = None
            item = models.MenuItem(
                restaurant_id=rid, name=str(m.get("name") or "Taom")[:150],
                price=float(m.get("price") or 0), image_url=image_url,
                is_available=m.get("status") == "approved"
            )
            db.add(item)
            db.flush()
            menumap[m["id"]] = item.id
            db.add(models.MenuExtra(
                menu_item_id=item.id, category=str(m.get("category") or "")[:60],
                description=str(m.get("description") or "")[:400]
            ))

        details = {r["order_id"]: r for r in data_rows(conn, "web_order_details")}
        ordermap = {}
        for o in orders:
            rid = restaurantmap.get(o.get("restaurant_id"))
            if not rid:
                raise RuntimeError("Order references missing restaurant. Aborting.")
            cust = usermap.get(o.get("customer_id"))
            if not cust:
                raise RuntimeError("Order references missing customer. Aborting.")
            obj = models.Order(
                customer_id=cust, restaurant_id=rid,
                courier_id=couriermap.get(o.get("courier_id")),
                address=str(o.get("address") or "Manzil aniqlanmoqda")[:500],
                total=float(o.get("total") or 0),
                status=status(o.get("status")),
                payment_method="cash" if o.get("payment") in {"Naqd", "cash"} else "unknown",
                created_at=dt(o.get("created_at")),
            )
            db.add(obj)
            db.flush()
            ordermap[o["id"]] = obj.id
            info = details.get(o["id"], {})
            db.add(models.DeliveryInfo(
                order_id=obj.id,
                phone=str(o.get("phone") or "")[:30],
                note=str(info.get("note") or "")[:500],
                latitude=info.get("latitude"),
                longitude=info.get("longitude")
            ))

        for line in lines:
            oid = ordermap.get(line.get("order_id"))
            menu_id = menumap.get(line.get("item_id"))
            if not oid or not menu_id:
                raise RuntimeError("Order item reference mismatch. Aborting entire migration.")
            db.add(models.OrderItem(
                order_id=oid, menu_item_id=menu_id,
                quantity=int(line.get("qty") or 1),
                price=float(line.get("price") or 0),
            ))
        db.flush()
        result = {
            "users": len(usermap) + len(ownermap) + len(couriermap),
            "restaurants": len(restaurantmap), "menu_items": len(menumap),
            "orders": len(ordermap), "order_items": len(lines),
            "disabled_legacy_accounts": True,
            "legacy_site_not_switched_over": True,
        }
        # A transaction for all core records: a failure means zero partial rows.
        db.commit()
        return result


def main():
    parser = argparse.ArgumentParser(description="Ali Kuryer safe SQLite-to-Postgres plan")
    parser.add_argument("--apply", action="store_true", help="Only after verified legacy write freeze")
    args = parser.parse_args()
    source = Path(os.getenv("ALI_LEGACY_DB_PATH", "/var/data/ali_kuryer.db"))
    if args.apply and (
        os.getenv("ALI_MIGRATION_CONFIRMED") != "yes"
        or os.getenv("ALI_LEGACY_WRITES_FROZEN") != "1"
    ):
        raise SystemExit("Migration requires explicit confirmation AND verified legacy write freeze.")
    backup = snapshot(source)
    try:
        with sqlite3.connect("file:" + str(backup) + "?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            plan = inspect(conn)
            print("VERIFIED SQLITE BACKUP:", backup.name)
            print("SOURCE COUNTS:", json.dumps(plan, ensure_ascii=False, sort_keys=True))
            if not args.apply:
                print("DRY RUN ONLY: no target or production data was changed.")
            else:
                result = perform_import(conn)
                print("IMPORT COMPLETE (legacy still running separately):", json.dumps(result))
    except Exception:
        print("IMPORT NOT COMPLETED. Original and verified backup files remain untouched.")
        raise


if __name__ == "__main__":
    main()
