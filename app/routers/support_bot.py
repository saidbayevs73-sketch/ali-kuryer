"""Ali Kuryer Telegram operator/helpdesk webhook.

Runs inside the existing FastAPI service; requires a separate Telegram bot
token so it cannot conflict with the pre-existing ordering bot.
"""
import asyncio
import json
import logging
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/support", tags=["telegram-support"])
log = logging.getLogger(__name__)

CATEGORIES = {
    "📦 Buyurtma bo‘yicha": ("orders", "Buyurtma"),
    "💳 To‘lov bo‘yicha": ("payment", "To‘lov"),
    "🛵 Kuryer bo‘yicha": ("courier", "Kuryer"),
    "🏪 Restoran bo‘yicha": ("restaurant", "Restoran"),
    "⚠️ Shikoyat": ("complaint", "Shikoyat"),
    "💬 Boshqa savol": ("general", "Boshqa savol"),
}
FAQ = {
    "📍 Buyurtma holati": (
        "Buyurtmangiz holatini Ali Kuryer ilovasidagi buyurtmalar "
        "bo‘limidan tekshiring. Muammo bo‘lsa «📦 Buyurtma bo‘yicha»ni tanlang."
    ),
    "💳 To‘lov usullari": (
        "Mavjud to‘lov usullari buyurtmani rasmiylashtirish vaqtida "
        "ko‘rsatiladi. To‘lov amalga oshmasa, «💳 To‘lov bo‘yicha»ni tanlang."
    ),
    "🚚 Yetkazib berish": (
        "Yetkazish narxi va muddati manzil, restoran va buyurtmaga bog‘liq. "
        "Aniq buyurtma bilan muammo bo‘lsa, operatorga yozing."
    ),
}
BACK = "🏠 Bosh menyu"
STATUS = "📨 Murojaatim holati"
CLOSE = "✅ Murojaatni yopish"
FAQ_BUTTON = "❓ Ko‘p so‘raladigan savollar"
CANCEL = "❌ Bekor qilish"


def settings():
    return {
        "token": os.getenv("SUPPORT_BOT_TOKEN", "").strip(),
        "secret": os.getenv("SUPPORT_WEBHOOK_SECRET", "").strip(),
        "base_url": os.getenv("SUPPORT_PUBLIC_URL", "").strip().rstrip("/"),
        "group": os.getenv("SUPPORT_OPERATORS_CHAT_ID", "").strip(),
        "db": os.getenv("SUPPORT_DB_PATH", "ali_kuryer_support.db"),
    }


def get_db():
    path = Path(settings()["db"])
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS support_pending (
                user_id INTEGER PRIMARY KEY,
                category TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL DEFAULT '',
                username TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                group_id INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'open',
                assigned_to INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX IF NOT EXISTS unique_open_support_ticket
                ON support_tickets(user_id) WHERE state = 'open';
            CREATE TABLE IF NOT EXISTS support_relay (
                group_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                ticket_id INTEGER NOT NULL
                    REFERENCES support_tickets(id),
                PRIMARY KEY (group_id, message_id)
            );
        """)


def tg_call(method, **params):
    token = settings()["token"]
    if not token:
        raise RuntimeError("SUPPORT_BOT_TOKEN is not set")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(params, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram {method}: not OK")
        return payload.get("result")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        log.error("Telegram %s failed: %s", method, type(exc).__name__)
        raise RuntimeError(f"Telegram {method} unavailable") from exc


def send(chat_id, text, keyboard=None, **kwargs):
    args = {"chat_id": chat_id, "text": text, **kwargs}
    if keyboard:
        args["reply_markup"] = keyboard
    return tg_call("sendMessage", **args)


def copy_message(to_chat, from_chat, message_id):
    return tg_call(
        "copyMessage", chat_id=to_chat,
        from_chat_id=from_chat, message_id=message_id,
    )


def home_keyboard():
    return {"keyboard": [
        ["📦 Buyurtma bo‘yicha", "💳 To‘lov bo‘yicha"],
        ["🛵 Kuryer bo‘yicha", "🏪 Restoran bo‘yicha"],
        ["⚠️ Shikoyat", "💬 Boshqa savol"],
        [FAQ_BUTTON, STATUS],
    ], "resize_keyboard": True}


def faq_keyboard():
    return {"keyboard": [
        ["📍 Buyurtma holati", "💳 To‘lov usullari"],
        ["🚚 Yetkazib berish"],
        [BACK],
    ], "resize_keyboard": True}


def request_keyboard():
    return {"keyboard": [
        [STATUS, CLOSE], [BACK],
    ], "resize_keyboard": True}


def group_for(category):
    env_key = {
        "orders": "SUPPORT_ORDERS_CHAT_ID",
        "payment": "SUPPORT_PAYMENT_CHAT_ID",
        "courier": "SUPPORT_COURIER_CHAT_ID",
        "restaurant": "SUPPORT_RESTAURANT_CHAT_ID",
        "complaint": "SUPPORT_COMPLAINT_CHAT_ID",
        "general": "SUPPORT_GENERAL_CHAT_ID",
    }[category]
    value = os.getenv(env_key, "").strip() or settings()["group"]
    return int(value) if value else None


def allowed_groups():
    values = set()
    for category in ["orders", "payment", "courier", "restaurant", "complaint", "general"]:
        value = group_for(category)
        if value is not None:
            values.add(value)
    return values


def open_ticket(db, user_id):
    return db.execute(
        "SELECT * FROM support_tickets WHERE user_id=? AND state='open'",
        (user_id,),
    ).fetchone()


def record_relay(db, group_id, message_id, ticket_id):
    db.execute(
        "INSERT OR IGNORE INTO support_relay(group_id,message_id,ticket_id) "
        "VALUES(?,?,?)", (group_id, message_id, ticket_id),
    )


def operator_ticket(db, group_id, reply_id):
    return db.execute("""
        SELECT t.* FROM support_relay r
        JOIN support_tickets t ON t.id=r.ticket_id
        WHERE r.group_id=? AND r.message_id=?
    """, (group_id, reply_id)).fetchone()


def set_pending(db, user_id, category):
    db.execute(
        "INSERT INTO support_pending(user_id,category) VALUES(?,?) "
        "ON CONFLICT(user_id) DO UPDATE SET category=excluded.category",
        (user_id, category),
    )


def process_private(msg):
    chat_id = msg["chat"]["id"]
    user = msg.get("from", {})
    user_id = user.get("id")
    if not user_id:
        return
    text = (msg.get("text") or "").strip()
    with get_db() as db:
        ticket = open_ticket(db, user_id)
        if text in ("/start", "/help", BACK):
            send(chat_id,
                 "Assalomu alaykum! 👋\nAli Kuryer yordam markaziga "
                 "xush kelibsiz. Murojaatingiz turini tanlang.",
                 home_keyboard())
            return
        if text == FAQ_BUTTON:
            send(chat_id, "Savolingizni tanlang:", faq_keyboard())
            return
        if text in FAQ:
            send(chat_id, FAQ[text], faq_keyboard())
            return
        if text in (STATUS, "/status"):
            if ticket:
                send(chat_id,
                     f"📨 Murojaat №{ticket['id']}: ko‘rib chiqilmoqda.\n"
                     "Qo‘shimcha ma’lumotni shu yerga yozishingiz mumkin.",
                     request_keyboard())
            else:
                send(chat_id, "Hozir ochiq murojaatingiz yo‘q.", home_keyboard())
            return
        if text in (CLOSE, "/close"):
            db.execute("DELETE FROM support_pending WHERE user_id=?", (user_id,))
            if not ticket:
                send(chat_id, "Ochiq murojaat topilmadi.", home_keyboard())
                return
            db.execute(
                "UPDATE support_tickets SET state='closed',"
                "updated_at=CURRENT_TIMESTAMP WHERE id=?", (ticket["id"],),
            )
            send(ticket["group_id"], f"✅ Murojaat №{ticket['id']} mijoz tomonidan yopildi.")
            send(chat_id, "Murojaatingiz yopildi. Rahmat!", home_keyboard())
            return
        if text in (CANCEL, "/cancel"):
            db.execute("DELETE FROM support_pending WHERE user_id=?", (user_id,))
            send(chat_id, "Tanlov bekor qilindi.", home_keyboard())
            return
        if text in CATEGORIES:
            if ticket:
                send(chat_id,
                     f"Avval №{ticket['id']} murojaatingizni yakunlang "
                     "yoki shu suhbatga ma’lumot yuboring.",
                     request_keyboard())
                return
            code, label = CATEGORIES[text]
            set_pending(db, user_id, code)
            send(chat_id,
                 f"📝 {label}: savolingizni yoki muammo tafsilotlarini "
                 "yozing. Zarur bo‘lsa surat yoki hujjat yuborishingiz mumkin.\n"
                 "Bekor qilish: /cancel",
                 {"keyboard": [[CANCEL]], "resize_keyboard": True})
            return

        if not ticket:
            pending = db.execute(
                "SELECT category FROM support_pending WHERE user_id=?", (user_id,)
            ).fetchone()
            if not pending:
                send(chat_id, "Avval murojaat bo‘limini tanlang.", home_keyboard())
                return
            category = pending["category"]
            group_id = group_for(category)
            if not group_id:
                send(chat_id, "Operator guruhi hali ulanmagan. Keyinroq qayta urinib ko‘ring.")
                return
            display_name = " ".join(
                part for part in [user.get("first_name", ""), user.get("last_name", "")]
                if part
            )[:120] or "Mijoz"
            cursor = db.execute("""
                INSERT INTO support_tickets
                (user_id,user_name,username,category,group_id)
                VALUES(?,?,?,?,?)
            """, (user_id, display_name, user.get("username", ""), category, group_id))
            ticket_id = cursor.lastrowid
            label = next((v[1] for v in CATEGORIES.values() if v[0] == category),
                         category)
            header = (
                f"🆕 Murojaat №{ticket_id}\n"
                f"📂 Bo‘lim: {label}\n"
                f"👤 Mijoz: {display_name}\n"
                f"🔗 Telegram: @{user['username']}\n" if user.get("username") else
                f"🆕 Murojaat №{ticket_id}\n📂 Bo‘lim: {label}\n👤 Mijoz: {display_name}\n"
            )
            header += (
                "↩️ Javob uchun ushbu xabar yoki mijoz xabariga Reply bosing.\n"
                "✅ Yopish: xabarga Reply qilib /close yuboring."
            )
            try:
                posted = send(group_id, header)
                record_relay(db, group_id, posted["message_id"], ticket_id)
                copied = copy_message(group_id, chat_id, msg["message_id"])
                record_relay(db, group_id, copied["message_id"], ticket_id)
            except RuntimeError:
                db.execute("UPDATE support_tickets SET state='closed' WHERE id=?",
                           (ticket_id,))
                send(chat_id, "Murojaatni yuborishda xatolik. Iltimos, qayta urinib ko‘ring.")
                return
            db.execute("DELETE FROM support_pending WHERE user_id=?", (user_id,))
            send(chat_id, f"✅ №{ticket_id} murojaat qabul qilindi. "
                 "Operator javobini shu yerda olasiz.",
                 request_keyboard())
            return

        try:
            copied = copy_message(ticket["group_id"], chat_id, msg["message_id"])
        except RuntimeError:
            send(chat_id, "Xabaringiz hozir yuborilmadi. Iltimos, qayta urinib ko‘ring.")
            return
        record_relay(db, ticket["group_id"], copied["message_id"], ticket["id"])
        db.execute("UPDATE support_tickets SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (ticket["id"],))
        send(chat_id, "✅ Xabaringiz operatorga yuborildi.", request_keyboard())


def process_operator(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if text.split("@")[0] == "/chatid":
        send(chat_id, f"Guruh ID: {chat_id}")
        return
    if chat_id not in allowed_groups():
        return
    reply_to = (msg.get("reply_to_message") or {}).get("message_id")
    if not reply_to:
        return
    with get_db() as db:
        ticket = operator_ticket(db, chat_id, reply_to)
        if not ticket:
            return
        if text.split("@")[0] == "/close":
            if ticket["state"] == "closed":
                send(chat_id, f"№{ticket['id']} allaqachon yopilgan.")
                return
            db.execute("UPDATE support_tickets SET state='closed', "
                       "updated_at=CURRENT_TIMESTAMP WHERE id=?", (ticket["id"],))
            send(ticket["user_id"],
                 f"✅ №{ticket['id']} murojaatingiz operator tomonidan yopildi. "
                 "Yangi murojaat uchun bo‘lim tanlang.", home_keyboard())
            send(chat_id, f"✅ №{ticket['id']} yopildi.")
            return
        if text.split("@")[0] == "/take":
            db.execute(
                "UPDATE support_tickets SET assigned_to=?,updated_at=CURRENT_TIMESTAMP "
                "WHERE id=? AND state='open'",
                (msg.get("from", {}).get("id"), ticket["id"]),
            )
            send(chat_id, f"👨‍💻 №{ticket['id']} murojaat sizga biriktirildi.")
            return
        if text.startswith("/"):
            return
        if ticket["state"] != "open":
            send(chat_id, f"№{ticket['id']} yopilgan. Javob yuborilmadi.")
            return
        try:
            copy_message(ticket["user_id"], chat_id, msg["message_id"])
        except RuntimeError:
            send(chat_id, f"⚠️ №{ticket['id']}: mijozga xabar yuborilmadi.")
            return
        db.execute("UPDATE support_tickets SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (ticket["id"],))
        send(chat_id, f"✅ №{ticket['id']}: mijozga yuborildi.",
             reply_to_message_id=msg["message_id"])


def process_update(update):
    msg = update.get("message")
    if not msg or not isinstance(msg, dict):
        return
    chat = msg.get("chat", {})
    if chat.get("type") == "private":
        process_private(msg)
    elif chat.get("type") in ("group", "supergroup"):
        process_operator(msg)


@router.post("/telegram")
async def telegram_support_webhook(request: Request):
    cfg = settings()
    if not cfg["token"] or not cfg["secret"]:
        raise HTTPException(status_code=503, detail="Support bot not configured")
    supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    import hmac
    if not hmac.compare_digest(supplied, cfg["secret"]):
        raise HTTPException(status_code=403, detail="Forbidden")
    update = await request.json()
    try:
        await asyncio.to_thread(init_db)
        await asyncio.to_thread(process_update, update)
    except (RuntimeError, sqlite3.Error, ValueError, KeyError) as exc:
        log.exception("Support update failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Temporary support error") from exc
    return {"ok": True}


def register_support_webhook():
    """Call on FastAPI startup; no-op until env vars are configured."""
    cfg = settings()
    if not all([cfg["token"], cfg["secret"], cfg["base_url"]]):
        log.info("Support bot not configured; skipping webhook registration")
        return
    if not cfg["base_url"].startswith("https://"):
        log.error("SUPPORT_PUBLIC_URL must use https://")
        return
    init_db()
    try:
        tg_call(
            "setWebhook",
            url=f"{cfg['base_url']}/api/support/telegram",
            secret_token=cfg["secret"],
            allowed_updates=["message"],
            drop_pending_updates=False,
        )
        log.info("Support Telegram webhook registered")
    except RuntimeError:
        log.exception("Could not register Telegram support webhook")
