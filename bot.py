import os
import time
import json
import base64
import sqlite3
import html
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Lock

# =========================================================
# ALI KURYER — BOT + SQLITE + ADMIN PANEL
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")
DB_PATH = os.getenv("DB_PATH", "ali_kuryer.db")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    print("XATO: BOT_TOKEN topilmadi.")
    raise SystemExit(1)

API = f"https://api.telegram.org/bot{TOKEN}"
DB_LOCK = Lock()

# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK:
        conn = db()
        conn.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            latitude REAL,
            longitude REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL DEFAULT 0,
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            restaurant_id INTEGER,
            total INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Yangi',
            courier_id INTEGER,
            address TEXT DEFAULT '',
            latitude REAL,
            longitude REAL,
            payment_method TEXT DEFAULT 'Naqd',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_id INTEGER,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            telegram_id INTEGER UNIQUE,
            active INTEGER DEFAULT 1,
            online INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()

        count = conn.execute("SELECT COUNT(*) AS c FROM restaurants").fetchone()["c"]
        if count == 0:
            restaurants = [
                ("Ali Burger", "+998900000001", "Toshkent", 1),
                ("Osh Markazi", "+998900000002", "Toshkent", 1),
                ("Pizza House", "+998900000003", "Toshkent", 1),
            ]
            conn.executemany(
                "INSERT INTO restaurants(name,phone,address,active) VALUES(?,?,?,?)",
                restaurants
            )
            ids = [r["id"] for r in conn.execute("SELECT id FROM restaurants ORDER BY id").fetchall()]
            items = [
                (ids[0], "Classic Burger", 30000, "Mol go'shti, pishloq, salat va sous", "", 1),
                (ids[0], "Chicken Burger", 28000, "Tovuq go'shti, salat va maxsus sous", "", 1),
                (ids[0], "Fri", 12000, "Qarsildoq kartoshka fri", "", 1),
                (ids[1], "O'zbek Palovi", 35000, "Guruch, go'sht, sabzi va no'xat", "", 1),
                (ids[1], "Chuchvara", 25000, "Uy uslubidagi chuchvara", "", 1),
                (ids[1], "Achichuk", 10000, "Pomidor, piyoz va ko'katlar", "", 1),
                (ids[2], "Pepperoni Pizza", 65000, "Pishloq, pepperoni va pomidor sousi", "", 1),
                (ids[2], "Chicken Pizza", 60000, "Tovuq go'shti, pishloq va sous", "", 1),
                (ids[2], "Margherita", 50000, "Pishloq, pomidor va maxsus sous", "", 1),
            ]
            conn.executemany(
                """INSERT INTO items
                   (restaurant_id,name,price,description,image_url,active)
                   VALUES(?,?,?,?,?,?)""",
                items
            )
            conn.commit()
        conn.close()


# =========================================================
# TELEGRAM
# =========================================================

def telegram(method, data=None):
    try:
        url = f"{API}/{method}"
        if data:
            encoded = urllib.parse.urlencode(data).encode("utf-8")
            request = urllib.request.Request(url, data=encoded)
        else:
            request = urllib.request.Request(url)
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print("Telegram API xatosi:", e)
        return None


def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return telegram("sendMessage", data)


def answer_callback(callback_id, text=""):
    telegram("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })


# =========================================================
# DATA HELPERS
# =========================================================

def get_restaurants():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM restaurants WHERE active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def get_items(restaurant_id):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM items WHERE restaurant_id=? AND active=1 ORDER BY id",
        (restaurant_id,)
    ).fetchall()
    conn.close()
    return rows


def get_item(item_id):
    conn = db()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return row


def save_user(message):
    user = message.get("from", {})
    user_id = user.get("id")
    if not user_id:
        return
    name = user.get("first_name", "Mijoz")
    username = user.get("username", "")
    with DB_LOCK:
        conn = db()
        conn.execute("""
            INSERT INTO users(id,name,username)
            VALUES(?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                username=excluded.username
        """, (user_id, name, username))
        conn.commit()
        conn.close()


# =========================================================
# TELEGRAM KEYBOARDS
# =========================================================

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🍔 Buyurtma berish"}, {"text": "🍽 Restoranlar"}],
            [{"text": "📦 Buyurtmalarim"}, {"text": "📍 Buyurtmani kuzatish"}],
            [{"text": "👤 Profilim"}, {"text": "💬 Yordam"}],
            [{"text": "🛵 Kuryer bo‘lish"}, {"text": "🏪 Restoran hamkorligi"}]
        ],
        "resize_keyboard": True
    }


def restaurants_keyboard():
    buttons = []
    for r in get_restaurants():
        buttons.append([{
            "text": r["name"],
            "callback_data": f"restaurant:{r['id']}"
        }])
    return {"inline_keyboard": buttons}


def menu_keyboard(restaurant_id):
    buttons = []
    for item in get_items(restaurant_id):
        buttons.append([{
            "text": f"{item['name']} — {item['price']:,} so'm",
            "callback_data": f"item:{restaurant_id}:{item['id']}"
        }])
    buttons.append([{"text": "🛒 Savat", "callback_data": "cart"}])
    return {"inline_keyboard": buttons}


def item_keyboard(restaurant_id, item_id):
    return {
        "inline_keyboard": [
            [{"text": "➕ Savatga qo‘shish",
              "callback_data": f"add:{restaurant_id}:{item_id}"}],
            [{"text": "🛒 Savatni ko‘rish", "callback_data": "cart"}]
        ]
    }


# =========================================================
# CART
# =========================================================

carts = {}


def get_cart(user_id):
    if user_id not in carts:
        carts[user_id] = []
    return carts[user_id]


def cart_text(user_id):
    cart = get_cart(user_id)
    if not cart:
        return "🛒 Savatingiz hozircha bo‘sh."

    total = 0
    text = "🛒 SAVATINGIZ\n\n"
    for i, product in enumerate(cart, 1):
        total += product["price"]
        text += f"{i}. {product['name']}\n   {product['price']:,} so'm\n\n"
    text += f"💰 Jami: {total:,} so'm"
    return text


def cart_keyboard(user_id):
    if not get_cart(user_id):
        return {"inline_keyboard": [
            [{"text": "🍔 Buyurtma berish", "callback_data": "restaurants"}]
        ]}
    return {"inline_keyboard": [
        [{"text": "✅ Buyurtmani tasdiqlash", "callback_data": "checkout"}],
        [{"text": "🗑 Savatni tozalash", "callback_data": "clear_cart"}]
    ]}


def create_order(user_id):
    cart = get_cart(user_id)
    if not cart:
        return None

    restaurant_id = cart[0].get("restaurant_id")
    total = sum(x["price"] for x in cart)

    with DB_LOCK:
        conn = db()
        cur = conn.execute("""
            INSERT INTO orders(user_id,restaurant_id,total,status)
            VALUES(?,?,?,?)
        """, (user_id, restaurant_id, total, "Yangi"))
        order_id = cur.lastrowid

        for x in cart:
            conn.execute("""
                INSERT INTO order_items(order_id,item_id,name,price,quantity)
                VALUES(?,?,?,?,1)
            """, (order_id, x.get("item_id"), x["name"], x["price"]))
        conn.commit()

        order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        conn.close()

    carts[user_id] = []
    return order


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):
    save_user(message)

    chat_id = message.get("chat", {}).get("id")
    user = message.get("from", {})
    user_id = user.get("id")
    first_name = user.get("first_name", "Mijoz")
    text = message.get("text", "").strip()

    if not chat_id:
        return

    if text == "/start":
        send_message(
            chat_id,
            f"👋 Assalomu alaykum, {first_name}!\n\n"
            "🛵 Ali Kuryer botiga xush kelibsiz.\n\n"
            "Tez, xavfsiz va ishonchli yetkazib berish xizmati.",
            main_keyboard()
        )
        return

    if text in ["/order", "🍔 Buyurtma berish", "/restaurants", "🍽 Restoranlar"]:
        send_message(chat_id, "🍽 Restoranni tanlang:", restaurants_keyboard())
        return

    if text in ["/orders", "📦 Buyurtmalarim"]:
        conn = db()
        rows = conn.execute("""
            SELECT o.id,o.total,o.status,r.name AS restaurant
            FROM orders o
            LEFT JOIN restaurants r ON r.id=o.restaurant_id
            WHERE o.user_id=?
            ORDER BY o.id DESC LIMIT 10
        """, (user_id,)).fetchall()
        conn.close()

        if not rows:
            send_message(chat_id, "📦 Sizda hozircha buyurtmalar yo‘q.", main_keyboard())
        else:
            out = "📦 BUYURTMALARIM\n\n"
            for o in rows:
                out += (
                    f"№{o['id']} — {o['restaurant'] or '-'}\n"
                    f"💰 {o['total']:,} so'm\n"
                    f"📌 {o['status']}\n\n"
                )
            send_message(chat_id, out, main_keyboard())
        return

    if text in ["/track", "📍 Buyurtmani kuzatish"]:
        conn = db()
        o = conn.execute("""
            SELECT o.*, r.name AS restaurant
            FROM orders o LEFT JOIN restaurants r ON r.id=o.restaurant_id
            WHERE o.user_id=? ORDER BY o.id DESC LIMIT 1
        """, (user_id,)).fetchone()
        conn.close()

        if not o:
            send_message(chat_id, "📍 Kuzatish uchun avval buyurtma bering.", main_keyboard())
        else:
            send_message(
                chat_id,
                f"📍 BUYURTMA №{o['id']}\n\n"
                f"🍽 Restoran: {o['restaurant'] or '-'}\n"
                f"💰 Jami: {o['total']:,} so'm\n"
                f"📌 Holati: {o['status']}",
                main_keyboard()
            )
        return

    if text in ["/profile", "👤 Profilim"]:
        conn = db()
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        send_message(
            chat_id,
            "👤 PROFILIM\n\n"
            f"Ism: {u['name'] if u else first_name}\n"
            f"Telefon: {u['phone'] if u and u['phone'] else 'Kiritilmagan'}\n"
            f"Lokatsiya: {'Kiritilgan' if u and u['latitude'] else 'Kiritilmagan'}",
            main_keyboard()
        )
        return

    if text in ["/support", "💬 Yordam"]:
        send_message(
            chat_id,
            "💬 YORDAM\n\n"
            "Savol yoki muammo bo‘lsa administrator bilan bog‘laning.\n"
            "🕐 Har kuni 09:00–23:00",
            main_keyboard()
        )
        return

    if text in ["/courier", "🛵 Kuryer bo‘lish"]:
        send_message(
            chat_id,
            "🛵 KURYER BO‘LISH\n\n"
            "Ism-familiya, telefon, transport turi va ishlash hududingizni yuboring.",
            main_keyboard()
        )
        return

    if text in ["/partner", "🏪 Restoran hamkorligi"]:
        send_message(
            chat_id,
            "🏪 RESTORAN HAMKORLIGI\n\n"
            "Restoraningizni Ali Kuryer platformasiga ulang.\n"
            "Admin panel orqali menyu va buyurtmalar boshqariladi.",
            main_keyboard()
        )
        return

    send_message(chat_id, "👇 Kerakli bo‘limni tanlang:", main_keyboard())


# =========================================================
# CALLBACK HANDLER
# =========================================================

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    if not chat_id:
        return

    answer_callback(callback_id)

    if data == "restaurants":
        send_message(chat_id, "🍽 Restoranni tanlang:", restaurants_keyboard())
        return

    if data.startswith("restaurant:"):
        rid = int(data.split(":")[1])
        conn = db()
        r = conn.execute(
            "SELECT * FROM restaurants WHERE id=? AND active=1", (rid,)
        ).fetchone()
        conn.close()
        if r:
            send_message(
                chat_id,
                f"🍽 {r['name']}\n\nMenyudan taom tanlang:",
                menu_keyboard(rid)
            )
        return

    if data.startswith("item:"):
        _, rid, iid = data.split(":")
        item = get_item(int(iid))
        if item:
            send_message(
                chat_id,
                f"🍽 {item['name']}\n\n"
                f"💰 Narxi: {item['price']:,} so'm\n\n"
                f"📝 {item['description'] or 'Tavsif kiritilmagan.'}",
                item_keyboard(int(rid), int(iid))
            )
        return

    if data.startswith("add:"):
        _, rid, iid = data.split(":")
        item = get_item(int(iid))
        conn = db()
        r = conn.execute("SELECT * FROM restaurants WHERE id=?", (int(rid),)).fetchone()
        conn.close()
        if item and r and item["active"] and r["active"]:
            get_cart(user_id).append({
                "restaurant_id": int(rid),
                "item_id": int(iid),
                "restaurant": r["name"],
                "name": item["name"],
                "price": item["price"]
            })
            send_message(
                chat_id,
                f"✅ {item['name']} savatga qo‘shildi!\n\n" + cart_text(user_id),
                cart_keyboard(user_id)
            )
        return

    if data == "cart":
        send_message(chat_id, cart_text(user_id), cart_keyboard(user_id))
        return

    if data == "clear_cart":
        carts[user_id] = []
        send_message(chat_id, "🗑 Savat tozalandi.", main_keyboard())
        return

    if data == "checkout":
        order = create_order(user_id)
        if not order:
            send_message(chat_id, "🛒 Savat bo‘sh.", main_keyboard())
            return

        conn = db()
        r = conn.execute(
            "SELECT * FROM restaurants WHERE id=?", (order["restaurant_id"],)
        ).fetchone()
        conn.close()

        send_message(
            chat_id,
            f"✅ BUYURTMA QABUL QILINDI!\n\n"
            f"📦 Buyurtma №{order['id']}\n"
            f"🍽 Restoran: {r['name'] if r else '-'}\n"
            f"💰 Jami: {order['total']:,} so'm\n"
            f"📌 Holati: Yangi\n\n"
            "🏪 Restoran buyurtmani ko‘rib chiqadi.\n"
            "🛵 Kuryer tayinlangach sizga xabar beramiz.",
            main_keyboard()
        )
        return


# =========================================================
# BOT LOOP
# =========================================================

def bot_loop():
    print("Ali Kuryer bot ishga tushdi...")
    offset = 0

    while True:
        try:
            result = telegram("getUpdates", {
                "offset": offset,
                "timeout": 30
            })

            if not result or not result.get("ok"):
                time.sleep(3)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                try:
                    if "message" in update:
                        handle_message(update["message"])
                    elif "callback_query" in update:
                        handle_callback(update["callback_query"])
                except Exception as e:
                    print("Update xatosi:", e)

        except Exception as e:
            print("Bot loop xatosi:", e)
            time.sleep(5)


# =========================================================
# ADMIN PANEL
# =========================================================

def esc(value):
    return html.escape(str(value or ""))


def admin_auth(handler):
    header = handler.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(header[6:]).decode("utf-8")
        user, password = raw.split(":", 1)
        return user == ADMIN_USER and password == ADMIN_PASSWORD
    except Exception:
        return False


def admin_html(title, body):
    return f"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ali Kuryer — {esc(title)}</title>
<style>
body{{font-family:Arial,sans-serif;background:#f4f4f4;margin:0;color:#111}}
header{{background:#111;color:#fff;padding:18px;font-size:22px;font-weight:700}}
nav{{background:#fff;padding:12px;position:sticky;top:0;border-bottom:1px solid #ddd}}
nav a{{display:inline-block;margin:5px;padding:10px 14px;background:#e9e9e9;border-radius:8px;color:#111;text-decoration:non
