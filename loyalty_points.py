"""Idempotent loyalty points on legacy delivered orders.

The approved earning rate is 10,000 UZS per point. Activation is separate.
Points have no money value or redemption behavior in this module.
"""
import re

def initialize(db):
    # User-approved earning rate; keep earning disabled until rollout.
    db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('loyalty_sum_per_point','10000')")
    db.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('loyalty_enabled','0')")
    db.execute("""CREATE TABLE IF NOT EXISTS loyalty_ledger (
        order_id INTEGER PRIMARY KEY REFERENCES orders(id),
        customer_id INTEGER NOT NULL,
        points INTEGER NOT NULL CHECK(points >= 0),
        sum_per_point INTEGER NOT NULL CHECK(sum_per_point > 0),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")

def award_delivered(db, order_id):
    settings = {r["key"]: r["value"] for r in db.execute(
        "SELECT key,value FROM settings WHERE key IN ('loyalty_enabled','loyalty_sum_per_point')")}
    if settings.get("loyalty_enabled") != "1":
        return 0
    raw = settings.get("loyalty_sum_per_point", "")
    if not re.fullmatch(r"[1-9][0-9]{0,11}", raw):
        return 0
    rate = int(raw)
    order = db.execute("SELECT id,customer_id,total,status FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order or order["status"] != "Yetkazildi" or not order["customer_id"]:
        return 0
    # Web checkout creates a fresh legacy customer row per order. Keep ledger
    # tied to the order; do not merge identities using unverified phone numbers.
    points = max(0, int(order["total"]) // rate)
    result = db.execute("""INSERT OR IGNORE INTO loyalty_ledger
        (order_id,customer_id,points,sum_per_point) VALUES(?,?,?,?)""",
        (order_id, order["customer_id"], points, rate))
    return points if result.rowcount == 1 else 0

def install(legacy):
    old_init, old_audit = legacy["init_db"], legacy["audit"]
    def init():
        old_init()
        with legacy["conn"]() as db:
            initialize(db)
    def audit(db, role, actor, action, entity, eid, before=None, after=None):
        old_audit(db, role, actor, action, entity, eid, before, after)
        if entity == "orders":
            award_delivered(db, eid)
    legacy["init_db"], legacy["audit"] = init, audit
