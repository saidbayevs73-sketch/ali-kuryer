

import os
import time
import json
import html
import sqlite3
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

# =========================================================
# ALI KURYER - Telegram bot + SQLite + Admin panel
# Only Python standard library is required.
# =========================================================

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_USER = os.getenv("ADMIN_USER", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-12345").strip()
DB_PATH = os.getenv("DB_PATH", "ali_kuryer.db")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    raise SystemExit("XATO: BOT_TOKEN Render Environment Variables ichida topilmadi.")

API = f"https://api.telegram.org/bot{TOKEN}"

# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL DEFAULT '',
        username TEXT NOT NULL DEFAULT '',
        phone TEXT NOT NULL DEFAULT '',
        lat REAL,
        lon REAL,
        address TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL DEFAULT '',
        address TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        price INTEGER NOT NULL DEFAULT 0,
        description TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        restaurant_id INTEGER,
        items_json TEXT NOT NULL,
        total INTEGER NOT NULL DEFAULT 0,
        payment_method TEXT NOT NULL DEFAULT 'Naqd',
        status TEXT NOT NULL DEFAULT 'Qabul qilindi',
        courier_name TEXT NOT NULL DEFAULT '',
        courier_phone TEXT NOT NULL DEFAULT '',
        delivery_fee INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    count = cur.execute("SELECT COUNT(*) AS c FROM restaurants").fetchone()["c"]
    if count == 0:
        restaurants = [
            ("Ali Burger", "+998 90 000 00 01", "Toshkent"),
            ("Osh Markazi", "+998 90 000 00 02", "Toshkent"),
            ("Pizza House", "+998 90 000 00 03", "Toshkent"),
        ]
        cur.executemany(
            "INSERT INTO restaurants(name, phone, address) VALUES(?,?,?)",
            restaurants,
        )
        rids = [row["id"] for row in cur.execute("SELECT id FROM restaurants ORDER BY id")]
        items = [
            (rids[0], "Classic Burger", 30000, "Mol go'shti, pishloq, salat va sous"),
            (rids[0], "Chicken Burger", 28000, "Tovuq go'shti, salat va maxsus sous"),
            (rids[0], "Fri", 12000, "Qarsildoq kartoshka fri"),
            (rids[1], "O'zbek Palovi", 35000, "Guruch, go'sht, sabzi va no'xat"),
            (rids[1], "Chuchvara", 25000, "Uy uslubidagi chuchvara"),
            (rids[1], "Achichuk", 10000, "Pomidor, piyoz va ko'katlar"),
            (rids[2], "Pepperoni Pizza", 65000, "Pishloq, pepperoni va pomidor sousi"),
            (rids[2], "Chicken Pizza", 60000, "Tovuq go'shti, pishloq va sous"),
            (rids[2], "Margherita", 50000, "Pishloq, pomidor va maxsus sous"),
        ]
        cur.executemany(
            "INSERT INTO menu_items(restaurant_id,name,price,description) VALUES(?,?,?,?)",
            items,
        )
    conn.commit()
    conn.close()

init_db()

# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):
    try:
        url = f"{API}/{method}"
        if data:
            encoded = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=encoded)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print("Telegram API xatosi:", exc)
        return None

def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard is not None:
        data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return telegram("sendMessage", data)

def answer_callback(callback_id, text=""):
    return telegram("answerCallbackQuery", {
        "callback_query_id": callback_id,
        "text": text
    })

# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🍔 Buyurtma berish"}, {"text": "🍽 Restoranlar"}],
            [{"text": "📦 Buyurtmalarim"}, {"text": "📍 Buyurtmani kuzatish"}],
            [{"text": "👤 Profilim"}, {"text": "💬 Yordam"}],
            [{"text": "🛵 Kuryer bo‘lish"}, {"text": "🏪 Restoran hamkorligi"}],
        ],
        "resize_keyboard": True
    }

def phone_keyboard():
    return {
        "keyboard": [
            [{"text": "📱 Telefon raqamimni yuborish", "request_contact": True}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def location_keyboard():
    return {
        "keyboard": [
            [{"text": "📍 Lokatsiyamni yuborish", "request_location": True}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def payment_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "💵 Naqd", "callback_data": "pay:Naqd"}],
            [{"text": "💳 Bank karta", "callback_data": "pay:Bank karta"}],
            [{"text": "🌐 Online to‘lov", "callback_data": "pay:Online to‘lov"}],
        ]
    }

def restaurants_keyboard():
    conn = db()
    rows = conn.execute(
        "SELECT id,name FROM restaurants WHERE active=1 ORDER BY name"
    ).fetchall()
    conn.close()
    return {
        "inline_keyboard": [
            [{"text": row["name"], "callback_data": f"restaurant:{row['id']}"}]
            for row in rows
        ]
    }

def menu_keyboard(restaurant_id):
    conn = db()
    rows = conn.execute(
        "SELECT id,name,price FROM menu_items WHERE restaurant_id=? AND active=1 ORDER BY id",
        (restaurant_id,),
    ).fetchall()
    conn.close()
    buttons = [
        [{"text": f"{row['name']} — {row['price']:,} so'm",
          "callback_data": f"item:{restaurant_id}:{row['id']}"}]
        for row in rows
    ]
    buttons.append([{"text": "🛒 Savat", "callback_data": "cart"}])
    return {"inline_keyboard": buttons}

def item_keyboard(restaurant_id, item_id):
    return {
        "inline_keyboard": [
            [{"text": "➕ Savatga qo‘shish",
              "callback_data": f"add:{restaurant_id}:{item_id}"}],
            [{"text": "🛒 Savatni ko‘rish", "callback_data": "cart"}],
        ]
    }

# =========================================================
# USER/CART STATE
# =========================================================

carts = {}
pending_checkout = {}

def get_cart(user_id):
    return carts.setdefault(user_id, [])

def cart_text(user_id):
    cart = get_cart(user_id)
    if not cart:
        return "🛒 Savatingiz hozircha bo‘sh."
    total = sum(x["price"] for x in cart)
    lines = ["🛒 SAVATINGIZ", ""]
    for i, item in enumerate(cart, 1):
        lines.append(f"{i}. {item['name']} — {item['price']:,} so'm")
    lines += ["", f"💰 Jami: {total:,} so'm"]
    return "\n".join(lines)

def cart_keyboard(user_id):
    if not get_cart(user_id):
        return {"inline_keyboard": [
            [{"text": "🍔 Buyurtma berish", "callback_data": "restaurants"}]
        ]}
    return {"inline_keyboard": [
        [{"text": "✅ Buyurtmani tasdiqlash", "callback_data": "checkout"}],
        [{"text": "🗑 Savatni tozalash", "callback_data": "clear_cart"}],
    ]}

# =========================================================
# USER HELPERS
# =========================================================

def save_user(user_id, first_name="", username="", phone=None, lat=None, lon=None):
    conn = db()
    old = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if old:
        conn.execute("""
            UPDATE users
            SET first_name=?, username=?,
                phone=COALESCE(?, phone),
                lat=COALESCE(?, lat),
                lon=COALESCE(?, lon)
            WHERE id=?
        """, (first_name, username, phone, lat, lon, user_id))
    else:
        conn.execute("""
            INSERT INTO users(id,first_name,username,phone,lat,lon)
            VALUES(?,?,?,?,?,?)
        """, (user_id, first_name, username, phone or "", lat, lon))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row

def make_order(user_id, payment_method):
    cart = get_cart(user_id)
    if not cart:
        return None
    user = get_user(user_id)
    restaurant_id = cart[0].get("restaurant_id")
    total = sum(x["price"] for x in cart)
    payload = json.dumps(cart, ensure_ascii=False)
    conn = db()
    cur = conn.execute("""
        INSERT INTO orders(
            user_id, restaurant_id, items_json, total, payment_method, status
        ) VALUES(?,?,?,?,?,?)
    """, (user_id, restaurant_id, payload, total, payment_method, "Qabul qilindi"))
    order_id = cur.lastrowid
    conn.commit()
    conn.close()
    carts[user_id] = []
    return order_id, total, user

# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):
    chat_id = message.get("chat", {}).get("id")
    user = message.get("from", {})
    user_id = user.get("id")
    if not chat_id or not user_id:
        return

    first_name = user.get("first_name", "Mijoz")
    username = user.get("username", "")
    save_user(user_id, first_name, username)

    contact = message.get("contact")
    if contact:
        phone = contact.get("phone_number", "")
        save_user(user_id, first_name, username, phone=phone)
        send_message(
            chat_id,
            "✅ Telefon raqamingiz saqlandi.\n\nEndi aniq yetkazib berish manzilini yuboring.",
            location_keyboard(),
        )
        return

    location = message.get("location")
    if location:
        lat = location.get("latitude")
        lon = location.get("longitude")
        save_user(user_id, first_name, username, lat=lat, lon=lon)
        send_message(
            chat_id,
            "✅ Lokatsiyangiz qabul qilindi.\n\nEndi to‘lov usulini tanlang.",
            payment_keyboard(),
        )
        return

    text = message.get("text", "").strip()

    if text == "/start":
        send_message(
            chat_id,
            f"👋 Assalomu alaykum, {first_name}!\n\n"
            "🛵 Ali Kuryer botiga xush kelibsiz!\n"
            "Tez, xavfsiz va ishonchli yetkazib berish xizmati.",
            main_keyboard(),
        )
        return

    if text in ("/order", "🍔 Buyurtma berish", "/restaurants", "🍽 Restoranlar"):
        send_message(chat_id, "🍽 Restoranni tanlang:", restaurants_keyboard())
        return

    if text in ("/orders", "📦 Buyurtmalarim"):
        conn = db()
        rows = conn.execute("""
            SELECT id,total,payment_method,status,created_at
            FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10
        """, (user_id,)).fetchall()
        conn.close()
        if not rows:
            send_message(chat_id, "📦 Sizda hozircha buyurtmalar yo‘q.", main_keyboard())
            return
        lines = ["📦 BUYURTMALARIM", ""]
        for row in rows:
            lines += [
                f"№{row['id']} — {row['status']}",
                f"💰 {row['total']:,} so'm",
                f"💳 {row['payment_method']}",
                f"🕐 {row['created_at']}",
                "",
            ]
        send_message(chat_id, "\n".join(lines), main_keyboard())
        return

    if text in ("/track", "📍 Buyurtmani kuzatish"):
        conn = db()
        row = conn.execute("""
            SELECT id,status,courier_name,courier_phone,total
            FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1
        """, (user_id,)).fetchone()
        conn.close()
        if not row:
            send_message(chat_id, "📍 Kuzatish uchun avval buyurtma bering.", main_keyboard())
            return
        courier = row["courier_name"] or "Hali tayinlanmagan"
        phone = row["courier_phone"] or "Hali mavjud emas"
        send_message(
            chat_id,
            f"📍 Buyurtma №{row['id']}\n\n"
            f"Holati: {row['status']}\n"
            f"🛵 Kuryer: {courier}\n"
            f"📞 Kuryer telefoni: {phone}\n"
            f"💰 Jami: {row['total']:,} so'm",
            main_keyboard(),
        )
        return

    if text in ("/profile", "👤 Profilim"):
        row = get_user(user_id)
        phone = row["phone"] if row else ""
        lat = row["lat"] if row else None
        lon = row["lon"] if row else None
        send_message(
            chat_id,
            "👤 PROFILIM\n\n"
            f"Ism: {first_name}\n"
            f"Username: @{username if username else 'yo‘q'}\n"
            f"📞 Telefon: {phone or 'saqlanmagan'}\n"
            f"📍 GPS: {'saqlangan' if lat is not None and lon is not None else 'saqlanmagan'}",
            main_keyboard(),
        )
        return

    if text in ("/support", "💬 Yordam"):
        send_message(
            chat_id,
            "💬 YORDAM\n\n"
            "Savol yoki muammo bo‘lsa administrator bilan bog‘laning.\n"
            "🕐 Har kuni 09:00–23:00",
            main_keyboard(),
        )
        return

    if text in ("/courier", "🛵 Kuryer bo‘lish"):
        send_message(
            chat_id,
            "🛵 KURYER BO‘LISH\n\n"
            "Ariza uchun administrator bilan bog‘laning.\n"
            "Kerakli ma’lumotlar: ism-familiya, telefon, transport turi va hudud.",
            main_keyboard(),
        )
        return

    if text in ("/partner", "🏪 Restoran hamkorligi"):
        send_message(
            chat_id,
            "🏪 RESTORAN HAMKORLIGI\n\n"
            "Restoraningizni Ali Kuryer platformasiga ulang.\n"
            "Hamkorlik uchun administrator bilan bog‘laning.",
            main_keyboard(),
        )
        return

    if pending_checkout.get(user_id) == "phone":
        send_message(
            chat_id,
            "📱 Buyurtma uchun telefon raqamingizni tugma orqali yuboring.",
            phone_keyboard(),
        )
        return

    send_message(chat_id, "👇 Kerakli bo‘limni tanlang:", main_keyboard())

# =========================================================
# CALLBACK HANDLER
# =========================================================

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")
    if not chat_id or not user_id:
        return

    answer_callback(callback_id)

    if data in ("restaurants", "back_restaurants"):
        send_message(chat_id, "🍽 Restoranni tanlang:", restaurants_keyboard())
        return

    if data.startswith("restaurant:"):
        rid = int(data.split(":")[1])
        conn = db()
        restaurant = conn.execute(
            "SELECT * FROM restaurants WHERE id=? AND active=1", (rid,)
        ).fetchone()
        conn.close()
        if not restaurant:
            send_message(chat_id, "Restoran topilmadi.")
            return
        send_message(
            chat_id,
            f"🍽 {restaurant['name']}\n"
            f"📞 {restaurant['phone'] or 'Telefon ko‘rsatilmagan'}\n"
            f"📍 {restaurant['address']}\n\n"
            "Menyudan taom tanlang:",
            menu_keyboard(rid),
        )
        return

    if data.startswith("item:"):
        _, rid, item_id = data.split(":")
        conn = db()
        row = conn.execute("""
            SELECT m.*, r.name AS restaurant_name
            FROM menu_items m JOIN restaurants r ON r.id=m.restaurant_id
            WHERE m.id=? AND m.restaurant_id=? AND m.active=1
        """, (int(item_id), int(rid))).fetchone()
        conn.close()
        if not row:
            send_message(chat_id, "Taom topilmadi.")
            return
        send_message(
            chat_id,
            f"🍽 {row['name']}\n\n"
            f"🏪 {row['restaurant_name']}\n"
            f"💰 Narxi: {row['price']:,} so'm\n"
            f"📝 {row['description']}",
            item_keyboard(int(rid), int(item_id)),
        )
        return

    if data.startswith("add:"):
        _, rid, item_id = data.split(":")
        conn = db()
        row = conn.execute("""
            SELECT m.*, r.name AS restaurant_name
            FROM menu_items m JOIN restaurants r ON r.id=m.restaurant_id
            WHERE m.id=? AND m.restaurant_id=? AND m.active=1
        """, (int(item_id), int(rid))).fetchone()
        conn.close()
        if not row:
            send_message(chat_id, "Taom topilmadi.")
            return
        cart = get_cart(user_id)
        if cart and cart[0]["restaurant_id"] != int(rid):
            send_message(
                chat_id,
                "⚠️ Savatda boshqa restoran taomlari bor.\n"
                "Avval savatni tozalang yoki shu restorandan davom eting.",
                cart_keyboard(user_id),
            )
            return
        cart.append({
            "restaurant_id": int(rid),
            "restaurant": row["restaurant_name"],
            "name": row["name"],
            "price": row["price"],
        })
        send_message(
            chat_id,
            f"✅ {row['name']} savatga qo‘shildi!\n\n{cart_text(user_id)}",
            cart_keyboard(user_id),
        )
        return

    if data == "cart":
        send_message(chat_id, cart_text(user_id), cart_keyboard(user_id))
        return

    if data == "clear_cart":
        carts[user_id] = []
        pending_checkout.pop(user_id, None)
        send_message(chat_id, "🗑 Savat tozalandi.", main_keyboard())
        return

    if data == "checkout":
        cart = get_cart(user_id)
        if not cart:
            send_message(chat_id, "🛒 Savat bo‘sh.", main_keyboard())
            return
        row = get_user(user_id)
        if not row or not row["phone"]:
            pending_checkout[user_id] = "phone"
            send_message(
                chat_id,
                "📱 Buyurtmani yakunlash uchun telefon raqamingizni yuboring.",
                phone_keyboard(),
            )
            return
        if row["lat"] is None or row["lon"] is None:
            send_message(
                chat_id,
                "📍 Buyurtmani yakunlash uchun aniq lokatsiyangizni yuboring.",
                location_keyboard(),
            )
            return
        send_message(chat_id, "💳 To‘lov usulini tanlang:", payment_keyboard())
        return

    if data.startswith("pay:"):
        method = data.split(":", 1)[1]
        row = get_user(user_id)
        if not row or not row["phone"]:
            pending_checkout[user_id] = "phone"
            send_message(chat_id, "📱 Avval telefon raqamingizni yuboring.", phone_keyboard())
            return
        if row["lat"] is None or row["lon"] is None:
            send_message(chat_id, "📍 Avval lokatsiyangizni yuboring.", location_keyboard())
            return
        result = make_order(user_id, method)
        if not result:
            send_message(chat_id, "🛒 Savat bo‘sh.", main_keyboard())
            return
        order_id, total, user_row = result
        pending_checkout.pop(user_id, None)
        send_message(
            chat_id,
            f"✅ BUYURTMA QABUL QILINDI!\n\n"
            f"📦 Buyurtma №{order_id}\n"
            f"💰 Jami: {total:,} so'm\n"
            f"💳 To‘lov: {method}\n"
            f"📞 Telefon: {user_row['phone']}\n"
            f"📍 GPS: qabul qilindi\n"
            "📌 Holati: Qabul qilindi\n\n"
            "🛵 Kuryer tayinlangach sizga xabar beramiz.",
            main_keyboard(),
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
            result = telegram("getUpdates", {"offset": offset, "timeout": 30})
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
                except Exception as exc:
                    print("Update xatosi:", exc)
        except Exception as exc:
            print("Bot loop xatosi:", exc)
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
        import base64
        raw = base64.b64decode(header[6:]).decode("utf-8")
        username, password = raw.split(":", 1)
        return username == ADMIN_USER and password == ADMIN_PASSWORD
    except Exception:
        return False

def admin_page(title, body):
    return f"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ali Kuryer — {esc(title)}</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f4f4f4;color:#111}}
header{{background:#111;color:#fff;padding:18px}}
header b{{font-size:22px}}
nav{{background:#fff;padding:12px;position:sticky;top:0;border-bottom:1px solid #ddd}}
nav a{{display:inline-block;margin:4px;padding:9px 12px;text-decoration:none;color:#111;border:1px solid #ddd;border-radius:8px}}
main{{padding:16px;max-width:1100px;margin:auto}}
.card{{background:#fff;padding:16px;margin:10px 0;border-radius:12px;box-shadow:0 1px 5px #ddd}}
table{{width:100%;border-collapse:collapse;background:#fff}}
th,td{{padding:9px;border-bottom:1px solid #eee;text-align:left;vertical-align:top}}
.badge{{display:inline-block;padding:5px 8px;border-radius:7px;background:#eee}}
.stat{{display:inline-block;min-width:150px;margin:5px;padding:15px;background:#fff;border-radius:12px}}
</style>
</head>
<body>
<header><b>🚚 Ali Kuryer Admin</b></header>
<nav>
<a href="/admin">Dashboard</a>
<a href="/admin/orders">Buyurtmalar</a>
<a href="/admin/users">Mijozlar</a>
<a href="/admin/restaurants">Restoranlar</a>
<a href="/admin/health">Tizim</a>
</nav>
<main>{body}</main>
</body></html>"""

class AppHandler(BaseHTTPRequestHandler):
    def send_html(self, status, body):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/":
            self.send_html(200, "<h1>Ali Kuryer Bot OK</h1><p>Telegram bot ishlayapti.</p>")
            return

        if path.startswith("/admin"):
            if not admin_auth(self):
                self.send_response(401)
                self.send_header("WWW-Authenticate", 'Basic realm="Ali Kuryer Admin"')
                self.end_headers()
                self.wfile.write(b"Admin login kerak.")
                return
            self.admin_get(path)
            return

        self.send_html(404, "<h1>404</h1>")

    def admin_get(self, path):
        conn = db()

        if path == "/admin":
            users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
            orders = conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
            restaurants = conn.execute(
                "SELECT COUNT(*) c FROM restaurants WHERE active=1"
            ).fetchone()["c"]
            revenue = conn.execute(
                "SELECT COALESCE(SUM(total),0) s FROM orders"
            ).fetchone()["s"]
            conn.close()
            body = f"""
            <h1>Dashboard</h1>
            <div class="stat">👤 Mijozlar<br><b>{users}</b></div>
            <div class="stat">📦 Buyurtmalar<br><b>{orders}</b></div>
            <div class="stat">🏪 Restoranlar<br><b>{restaurants}</b></div>
            <div class="stat">💰 Aylanma<br><b>{revenue:,} so'm</b></div>
            <div class="card">
              <h3>Admin panel ishlayapti</h3>
              <p>Keyingi bosqichlarda kuryerlar, GPS xarita, bloklash, shikoyatlar va to‘lov modullari ulanadi.</p>
            </div>
            """
            self.send_html(200, admin_page("Dashboard", body))
            return

        if path == "/admin/orders":
            rows = conn.execute("""
                SELECT o.*, u.first_name, u.phone, u.lat, u.lon, r.name restaurant_name
                FROM orders o
                LEFT JOIN users u ON u.id=o.user_id
                LEFT JOIN restaurants r ON r.id=o.restaurant_id
                ORDER BY o.id DESC LIMIT 100
            """).fetchall()
            conn.close()
            html_rows = ""
            for r in rows:
                gps = (
                    f'<a href="https://maps.google.com/?q={r["lat"]},{r["lon"]}" target="_blank">GPS</a>'
                    if r["lat"] is not None and r["lon"] is not None else "—"
                )
                html_rows += (
                    "<tr>"
                    f"<td>#{r['id']}</td>"
                    f"<td>{esc(r['first_name'])}<br>📞 {esc(r['phone'])}</td>"
                    f"<td>{esc(r['restaurant_name'])}</td>"
                    f"<td>{r['total']:,} so'm</td>"
                    f"<td>{esc(r['payment_method'])}</td>"
                    f"<td><span class='badge'>{esc(r['status'])}</span></td>"
                    f"<td>{gps}</td>"
                    "</tr>"
                )
            body = """
            <h1>📦 Buyurtmalar</h1>
            <table><tr>
            <th>ID</th><th>Mijoz</th><th>Restoran</th><th>Summa</th>
            <th>To‘lov</th><th>Holat</th><th>Lokatsiya</th>
            </tr>""" + html_rows + "</table>"
            self.send_html(200, admin_page("Buyurtmalar", body))
            return

        if path == "/admin/users":
            rows = conn.execute(
                "SELECT * FROM users ORDER BY id DESC LIMIT 100"
            ).fetchall()
            conn.close()
            html_rows = ""
            for r in rows:
                gps = (
                    f"{r['lat']:.6f}, {r['lon']:.6f}"
                    if r["lat"] is not None and r["lon"] is not None else "—"
                )
                html_rows += (
                    "<tr>"
                    f"<td>{r['id']}</td><td>{esc(r['first_name'])}</td>"
                    f"<td>{esc(r['username'])}</td><td>{esc(r['phone'])}</td>"
                    f"<td>{esc(gps)}</td><td>{esc(r['created_at'])}</td>"
                    "</tr>"
                )
            body = """
            <h1>👤 Mijozlar</h1>
            <table><tr><th>Telegram ID</th><th>Ism</th><th>Username</th>
            <th>Telefon</th><th>GPS</th><th>Sana</th></tr>""" + html_rows + "</table>"
            self.send_html(200, admin_page("Mijozlar", body))
            return

        if path == "/admin/restaurants":
            rows = conn.execute("SELECT * FROM restaurants ORDER BY id").fetchall()
            conn.close()
            html_rows = ""
            for r in rows:
                html_rows += (
                    "<tr>"
                    f"<td>{r['id']}</td><td>{esc(r['name'])}</td>"
                    f"<td>{esc(r['phone'])}</td><td>{esc(r['address'])}</td>"
                    f"<td>{'Faol' if r['active'] else 'O‘chiq'}</td>"
                    "</tr>"
                )
            body = """
            <h1>🏪 Restoranlar</h1>
            <table><tr><th>ID</th><th>Nomi</th><th>Telefon</th>
            <th>Manzil</th><th>Holat</th></tr>""" + html_rows + "</table>"
            self.send_html(200, admin_page("Restoranlar", body))
            return

        if path == "/admin/health":
            conn.close()
            body = """
            <h1>⚙️ Tizim</h1>
            <div class="card">
              <b>Telegram bot:</b> Ishlayapti<br>
              <b>Database:</b> SQLite<br>
              <b>Render PORT:</b> ishlatilmoqda<br>
              <b>Admin himoyasi:</b> Basic Auth
            </div>
            """
            self.send_html(200, admin_page("Tizim", body))
            return

        conn.close()
        self.send_html(404, admin_page("404", "<h1>Bo‘lim topilmadi</h1>"))

    def log_message(self, format, *args):
        pass

def run_web():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)
    print(f"Web/Admin server ishga tushdi: {PORT}")
    server.serve_forever()

# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    web_thread = Thread(target=run_web, daemon=True)
    web_thread.start()
    bot_loop()
