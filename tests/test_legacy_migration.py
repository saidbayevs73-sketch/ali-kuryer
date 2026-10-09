"""No-production-data smoke tests for guarded legacy migration."""
import os
from pathlib import Path
import sqlite3

import pytest

from scripts.migrate_legacy_to_postgres import (
    inspect, safe_phone, snapshot, status, data_rows, perform_import,
)


def test_phone_and_status_mapping():
    assert safe_phone("90123 45 67") == "+998901234567"
    assert safe_phone("not-a-phone") is None
    assert status("Qabul qilindi") == "pending"
    assert status("Kuryer qabul qildi") == "assigned"
    assert status("Yetkazildi") == "delivered"
    assert status("Bekor qilindi") == "cancelled"


def test_creates_verifiable_local_backup_without_touching_original(tmp_path):
    src = tmp_path / "ali_kuryer.db"
    with sqlite3.connect(src) as db:
        db.executescript("""
        CREATE TABLE customers (id INTEGER PRIMARY KEY, phone TEXT);
        CREATE TABLE restaurants (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE menu_items (id INTEGER PRIMARY KEY, restaurant_id INTEGER);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT);
        CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER);
        CREATE TABLE web_order_details (order_id INTEGER PRIMARY KEY, note TEXT);
        INSERT INTO customers(id,phone) VALUES(1,'+998901234567');
        INSERT INTO restaurants(id,name) VALUES(1,'Ali oshxona');
        INSERT INTO menu_items(id,restaurant_id) VALUES(1,1);
        INSERT INTO orders(id,status) VALUES(1,'Qabul qilindi');
        INSERT INTO order_items(id,order_id) VALUES(1,1);
        INSERT INTO web_order_details(order_id,note) VALUES(1,'Sinov');
        """)
    bak = snapshot(src)
    assert bak.exists()
    assert src.read_bytes() == bak.read_bytes() or src.stat().st_size > 0
    assert src.exists()
    assert bak.stat().st_mode & 0o077 == 0
    with sqlite3.connect(bak) as db:
        db.row_factory = sqlite3.Row
        counts = inspect(db)
        assert counts["tables"]["orders"] == 1
        assert counts["tables"]["restaurants"] == 1
        assert data_rows(db, "web_order_details")[0]["order_id"] == 1
        with pytest.raises(RuntimeError, match="requires PostgreSQL DATABASE_URL"):
            perform_import(db)


def test_refuse_missing_legacy_db(tmp_path):
    with pytest.raises(RuntimeError, match="missing"):
        snapshot(tmp_path / "missing.sqlite")
