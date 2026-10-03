import os
import time
import json
import base64
import html
import sqlite3
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Lock

# =========================================================
# ALI KURYER - single file bot + admin + kitchen/courier basics
# No external packages required.
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")
DB_PATH = os.getenv("DB_PATH", "ali_kuryer.db")
PORT = int(os.getenv("PORT", "10000"))
API = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""
DB_LOCK = Lock()

if not TOKEN:
    raise SystemExit("XATO: BOT_TOKEN Render Environment Variables ichida bo'lishi kerak.")

# ------------------------- database -------------------------

def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with DB_LOCK, db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            lat REAL,
            lon REAL,
            address TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS restaurants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            username TEXT DEFAULT '',
            password TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT DEFAULT '',
            active INTEGER DEFAULT 1,
            FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            restaurant_id INTEGER NOT NULL,
            total INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Qabul qilindi',
            payment TEXT DEFAULT 'Naqd',
            lat REAL,
            lon REAL,
            address TEXT DEFAULT '',
            courier_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_id INTEGER,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        );
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT DEFAULT '',
            username TEXT DEFAULT '',
            password TEXT DEFAULT '',
            online INTEGER DEFAULT 0,
            blocked INTEGER DEFAULT 0,
            lat REAL,
            lon REAL
        );
        """)
        count = c.execute("SELECT COUNT(*) n FROM restaurants").fetchone()["n"]
        if count == 0:
            restaurants = [
                ("Ali Burger", "+998900000001", "Toshkent", "", ""),
                ("Osh Markazi", "+998900000002", "Toshkent", "", ""),
                ("Pizza House", "+998900000003", "Toshkent", "", ""),
            ]
            c.executemany("INSERT INTO restaurants(name,phone,address,username,password) VALUES(?,?,?,?,?)", restaurants)
            ids = [r[0] for r in c.execute("SELECT id FROM restaurants ORDER BY id").fetchall()]
            menus = [
                (ids[0], "Classic Burger", 30000, "Mol go'shti, pishloq, salat va sous"),
                (ids[0], "Chicken Burger", 28000, "Tovuq go'shti, salat va maxsus sous"),
                (ids[0], "Fri", 12000, "Qarsildoq kartoshka fri"),
                (ids[1], "O'zbek Palovi", 35000, "Guruch, go'sht, sabzi va no'xat"),
                (ids[1], "Chuchvara", 25000, "Uy uslubidagi chuchvara"),
                (ids[1], "Achichuk", 10000, "Pomidor, piyoz va ko'katlar"),
                (ids[2], "Pepperoni Pizza", 65000, "Pishloq, pepperoni va pomidor sousi"),
                (ids[2], "Chicken Pizza", 60000, "Tovuq go'shti, pishloq va sous"),
                (ids[2], "Margherita", 50000, "Pishloq, pomidor va maxsus sous"),
            ]
            c.executemany("INSERT INTO menu(restaurant_id,name,price,description) VALUES(?,?,?,?)", menus)

# ------------------------- telegram -------------------------

def telegram(method, data=None):
    try:
        req = urllib.request.Request(
            f"{API}/{method}",
            data=urllib.parse.urlencode(data or {}).encode("utf-8") if data else None
        )
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("Telegram API xatosi:", e)
        return None


def send_message(chat_id, text, keyboard=None):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return telegram("sendMessage", data)


def answer_callback(cid, text=""):
    return telegram("answerCallbackQuery", {"callback_query_id": cid, "text": text})


def main_keyboard():
    return {"keyboard": [
        [{"text": "🍔 Buyurtma berish"}, {"text": "🍽 Restoranlar"}],
        [{"text": "📦 Buyurtmalarim"}, {"text": "📍 Buyurtmani kuzatish"}],
        [{"text": "👤 Profilim"}, {"text": "💬 Yordam"}],
        [{"text": "🛵 Kuryer bo‘lish"}, {"text": "🏪 Restoran hamkorligi"}],
    ], "resize_keyboard": True}


def restaurants_keyboard():
    with db() as c:
        rows = c.execute("SELECT id,name FROM restaurants WHERE active=1 ORDER BY name").fetchall()
    return {"inline_keyboard": [[{"text": r["name"], "callback_data": f"restaurant:{r['id']}"}] for r in rows]}


def menu_keyboard(rid):
    with db() as c:
        rows = c.execute("SELECT id,name,price FROM menu WHERE restaurant_id=? AND active=1 ORDER BY id", (rid,)).fetchall()
    buttons = [[{"text": f"{r['name']} — {r['price']:,} so'm", "callback_data": f"item:{rid}:{r['id']}"}] for r in rows]
    buttons.append([{"text": "🛒 Savat", "callback_data": "cart"}])
    return {"inline_keyboard": buttons}


def cart_get(uid):
    return carts.setdefault(uid, [])

carts = {}


def cart_text(uid):
    cart = cart_get(uid)
    if not cart:
        return "🛒 Savatingiz hozircha bo‘sh."
    total = sum(x["price"] * x.get("qty", 1) for x in cart)
    text = "🛒 SAVAT\n\n"
    for i, x in enumerate(cart, 1):
        q = x.get("qty", 1)
        text += f"{i}. {x['name']} × {q} — {x['price']*q:,} so'm\n"
    return text + f"\n💰 Jami: {total:,} so'm"


def cart_keyboard(uid):
    if not cart_get(uid):
        return {"inline_keyboard": [[{"text": "🍔 Buyurtma berish", "callback_data": "restaurants"}]]}
    return {"inline_keyboard": [
        [{"text": "📍 Manzilni yuborish", "callback_data": "location_help"}],
        [{"text": "💵 Naqd — tasdiqlash", "callback_data": "checkout:cash"}],
        [{"text": "🗑 Savatni tozalash", "callback_data": "clear_cart"}],
    ]}


def save_user(message):
    u = message.get("from", {})
    uid = u.get("id")
    if not uid:
        return
    with DB_LOCK, db() as c:
        c.execute("""INSERT INTO users(id,first_name,username) VALUES(?,?,?)
                     ON CONFLICT(id) DO UPDATE SET first_name=excluded.first_name, username=excluded.username""",
                  (uid, u.get("first_name", "Mijoz"), u.get("username", "")))


def handle_location(message):
    uid = message.get("from", {}).get("id")
    loc = message.get("location") or {}
    if not uid or not loc:
        return
    with DB_LOCK, db() as c:
        c.execute("UPDATE users SET lat=?,lon=? WHERE id=?", (loc.get("latitude"), loc.get("longitude"), uid))
    send_message(message["chat"]["id"], "📍 Joylashuvingiz saqlandi. Endi buyurtmani tasdiqlashingiz mumkin.", main_keyboard())


def handle_contact(message):
    uid = message.get("from", {}).get("id")
    phone = (message.get("contact") or {}).get("phone_number", "")
    if uid and phone:
        with DB_LOCK, db() as c:
            c.execute("UPDATE users SET phone=? WHERE id=?", (phone, uid))
        send_message(message["chat"]["id"], "📱 Telefon raqamingiz saqlandi.", main_keyboard())


def create_order(uid, payment="Naqd"):
    cart = cart_get(uid)
    if not cart:
        return None
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not user:
            return None
        rid = cart[0]["restaurant_id"]
        total = sum(x["price"] * x.get("qty", 1) for x in cart)
        cur = c.execute("""INSERT INTO orders(user_id,restaurant_id,total,payment,lat,lon,address)
                           VALUES(?,?,?,?,?,?,?)""",
                        (uid, rid, total, payment, user["lat"], user["lon"], user["address"]))
        oid = cur.lastrowid
        for x in cart:
            c.execute("INSERT INTO order_items(order_id,menu_id,name,price,qty) VALUES(?,?,?,?,?)",
                      (oid, x["menu_id"], x["name"], x["price"], x.get("qty", 1)))
    carts[uid] = []
    return oid


def order_text(oid):
    with db() as c:
        o = c.execute("""SELECT o.*,r.name restaurant,r.phone restaurant_phone,u.first_name,u.phone
                        FROM orders o JOIN restaurants r ON r.id=o.restaurant_id
                        JOIN users u ON u.id=o.user_id WHERE o.id=?""", (oid,)).fetchone()
        items = c.execute("SELECT name,price,qty FROM order_items WHERE order_id=?", (oid,)).fetchall()
    if not o:
        return "Buyurtma topilmadi."
    text = f"📦 Buyurtma №{o['id']}\n🏪 {o['restaurant']}\n\n"
    for x in items:
        text += f"• {x['name']} × {x['qty']} — {x['price']*x['qty']:,} so'm\n"
    text += f"\n💰 Jami: {o['total']:,} so'm\n📌 Holati: {o['status']}\n💳 To‘lov: {o['payment']}\n📞 Restoran: {o['restaurant_phone'] or 'Kiritilmagan'}"
    if o["courier_id"]:
        with db() as c:
            cr = c.execute("SELECT name,phone FROM couriers WHERE id=?", (o["courier_id"],)).fetchone()
        if cr:
            text += f"\n🛵 Kuryer: {cr['name']}\n📞 Kuryer: {cr['phone'] or 'Kiritilmagan'}"
    return text

# ------------------------- handlers -------------------------

def handle_message(message):
    save_user(message)
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return
    if message.get("location"):
        handle_location(message); return
    if message.get("contact"):
        handle_contact(message); return
    uid = message.get("from", {}).get("id")
    first = message.get("from", {}).get("first_name", "Mijoz")
    text = message.get("text", "").strip()

    if text == "/start":
        send_message(chat_id, f"👋 Assalomu alaykum, {first}!\n\n🛵 Ali Kuryer botiga xush kelibsiz.", main_keyboard()); return
    if text in ["/order", "🍔 Buyurtma berish", "/restaurants", "🍽 Restoranlar"]:
        send_message(chat_id, "🍽 Restoranni tanlang:", restaurants_keyboard()); return
    if text in ["/orders", "📦 Buyurtmalarim", "/track", "📍 Buyurtmani kuzatish"]:
        with db() as c:
            rows = c.execute("SELECT id FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
        if not rows:
            send_message(chat_id, "📦 Sizda hozircha buyurtmalar yo‘q.", main_keyboard())
        else:
            send_message(chat_id, "\n\n".join(order_text(r["id"]) for r in rows), main_keyboard())
        return
    if text in ["/profile", "👤 Profilim"]:
        with db() as c: u = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        phone = u["phone"] or "Kiritilmagan"; loc = "Kiritilmagan" if u["lat"] is None else f"{u['lat']}, {u['lon']}"
        send_message(chat_id, f"👤 PROFILIM\n\nIsm: {u['first_name']}\nTelefon: {phone}\nLokatsiya: {loc}", main_keyboard()); return
    if text in ["/support", "💬 Yordam"]:
        send_message(chat_id, "💬 YORDAM\n\nAdministrator bilan bog‘lanish uchun Ali Kuryer qo‘llab-quvvatlash xizmatiga murojaat qiling.", main_keyboard()); return
    if text in ["/courier", "🛵 Kuryer bo‘lish"]:
        send_message(chat_id, "🛵 KURYER BO‘LISH\n\nIsm-familiya, telefon, transport turi va ishlash hududingizni yuboring. Administrator arizani ko‘rib chiqadi.", main_keyboard()); return
    if text in ["/partner", "🏪 Restoran hamkorligi"]:
        send_message(chat_id, "🏪 RESTORAN HAMKORLIGI\n\nRestoran nomi, telefon raqami va manzilni yuboring. Administrator siz bilan bog‘lanadi.", main_keyboard()); return
    send_message(chat_id, "👇 Kerakli bo‘limni tanlang:", main_keyboard())


def handle_callback(cb):
    cid = cb.get("id"); data = cb.get("data", ""); msg = cb.get("message", {})
    chat_id = msg.get("chat", {}).get("id"); uid = cb.get("from", {}).get("id")
    if not chat_id: return
    answer_callback(cid)
    if data in ["restaurants", "location_help"]:
        if data == "restaurants": send_message(chat_id, "🍽 Restoranni tanlang:", restaurants_keyboard())
        else: send_message(chat_id, "📍 Telegramdagi 📎/menyu orqali joylashuvingizni yuboring.", main_keyboard())
        return
    if data.startswith("restaurant:"):
        rid = int(data.split(":")[1])
        with db() as c: r = c.execute("SELECT name FROM restaurants WHERE id=? AND active=1", (rid,)).fetchone()
        if r: send_message(chat_id, f"🍽 {r['name']}\n\nMenyudan taom tanlang:", menu_keyboard(rid))
        return
    if data.startswith("item:"):
        _, rid, mid = data.split(":")
        with db() as c: x = c.execute("SELECT * FROM menu WHERE id=? AND restaurant_id=?", (mid, rid)).fetchone()
        if x:
            kb = {"inline_keyboard":[[{"text":"➕ Savatga qo‘shish","callback_data":f"add:{rid}:{mid}"}],[{"text":"🛒 Savatni ko‘rish","callback_data":"cart"}]]}
            send_message(chat_id, f"🍽 {x['name']}\n\n💰 Narxi: {x['price']:,} so'm\n\n📝 {x['description']}", kb)
        return
    if data.startswith("add:"):
        _, rid, mid = data.split(":")
        with db() as c: x = c.execute("SELECT * FROM menu WHERE id=? AND restaurant_id=? AND active=1", (mid, rid)).fetchone()
        if not x: return
        cart = cart_get(uid)
        found = next((z for z in cart if z["menu_id"] == x["id"]), None)
        if found: found["qty"] += 1
        else: cart.append({"restaurant_id": x["restaurant_id"], "menu_id": x["id"], "name": x["name"], "price": x["price"], "qty": 1})
        send_message(chat_id, f"✅ {x['name']} savatga qo‘shildi.\n\n" + cart_text(uid), cart_keyboard(uid)); return
    if data == "cart": send_message(chat_id, cart_text(uid), cart_keyboard(uid)); return
    if data == "clear_cart": carts[uid] = []; send_message(chat_id, "🗑 Savat tozalandi.", main_keyboard()); return
    if data.startswith("checkout:"):
        with db() as c: u = c.execute("SELECT phone,lat FROM users WHERE id=?", (uid,)).fetchone()
        if not u or not u["phone"]:
            send_message(chat_id, "📱 Avval telefon raqamingizni yuboring.", {"keyboard":[[{"text":"📱 Telefon raqamimni yuborish","request_contact":True}]],"resize_keyboard":True}); return
        if u["lat"] is None:
            send_message(chat_id, "📍 Avval lokatsiyangizni yuboring. Buyurtma aniq manzil bilan qabul qilinadi.", {"keyboard":[[{"text":"📍 Lokatsiyamni yuborish","request_location":True}]],"resize_keyboard":True}); return
        oid = create_order(uid, data.split(":")[1])
        if oid:
            send_message(chat_id, "✅ BUYURTMA QABUL QILINDI!\n\n" + order_text(oid) + "\n\n🛵 Kuryer tayinlangach xabar beramiz.", main_keyboard())
        return

# ------------------------- bot loop -------------------------

def bot_loop():
    print("Ali Kuryer bot ishga tushdi")
    offset = 0
    while True:
        try:
            res = telegram("getUpdates", {"offset": offset, "timeout": 30})
            if not res or not res.get("ok"):
                time.sleep(3); continue
            for u in res.get("result", []):
                offset = u["update_id"] + 1
                try:
                    if "message" in u: handle_message(u["message"])
                    elif "callback_query" in u: handle_callback(u["callback_query"])
                except Exception as e: print("Update xatosi:", e)
        except Exception as e:
            print("Bot loop xatosi:", e); time.sleep(5)

# ------------------------- admin web -------------------------

def esc(v): return html.escape(str(v or ""))


def admin_auth(h):
    header = h.headers.get("Authorization", "")
    if not header.startswith("Basic "): return False
    try:
        raw = base64.b64decode(header[6:]).decode("utf-8")
        user, password = raw.split(":", 1)
        return user == ADMIN_USER and password == ADMIN_PASSWORD
    except Exception:
        return False


def page(title, body):
    # IMPORTANT: this is a normal triple-quoted string, not an f-string.
    # Dynamic values are inserted with replace() to avoid unterminated f-string errors.
    template = """<!doctype html>
<html lang='uz'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Ali Kuryer - TITLE</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f3f4f6;color:#111}header{background:#111;color:#fff;padding:18px;font-size:22px}nav{background:#fff;padding:12px;position:sticky;top:0;border-bottom:1px solid #ddd}nav a{display:inline-block;margin:4px;padding:9px 12px;background:#111;color:#fff;text-decoration:none;border-radius:7px}.wrap{max-width:1100px;margin:18px auto;padding:0 12px}.card{background:#fff;padding:16px;margin:12px 0;border-radius:10px;box-shadow:0 1px 5px #ddd}input,select{padding:10px;margin:4px;width:calc(100% - 30px);max-width:500px}button{padding:10px 14px;border:0;border-radius:7px;background:#e11;color:#fff}table{width:100%;border-collapse:collapse}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.stat{font-size:28px;font-weight:bold}.muted{color:#666}</style></head>
<body><header>🛵 Ali Kuryer — Admin panel</header><nav>
<a href='/admin'>Dashboard</a><a href='/admin?tab=orders'>Buyurtmalar</a><a href='/admin?tab=restaurants'>Restoranlar</a><a href='/admin?tab=menu'>Menyu</a><a href='/admin?tab=couriers'>Kuryerlar</a><a href='/kitchen'>Oshxona</a>
</nav><div class='wrap'>BODY</div></body></html>"""
    return template.replace("TITLE", esc(title)).replace("BODY", body)


def admin_dashboard():
    with db() as c:
        users = c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
        restaurants = c.execute("SELECT COUNT(*) n FROM restaurants WHERE active=1").fetchone()["n"]
        orders = c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
        couriers = c.execute("SELECT COUNT(*) n FROM couriers").fetchone()["n"]
        recent = c.execute("""SELECT o.id,o.total,o.status,r.name restaurant,u.first_name
                            FROM orders o JOIN restaurants r ON r.id=o.restaurant_id
                            JOIN users u ON u.id=o.user_id ORDER BY o.id DESC LIMIT 10""").fetchall()
    body = "<h2>Dashboard</h2><div class='grid'>"
    for label,val in [("Mijozlar",users),("Restoranlar",restaurants),("Buyurtmalar",orders),("Kuryerlar",couriers)]: body += f"<div class='card'><div class='muted'>{label}</div><div class='stat'>{val}</div></div>"
    body += "</div><div class='card'><h3>Oxirgi buyurtmalar</h3><table><tr><th>№</th><th>Mijoz</th><th>Restoran</th><th>Summa</th><th>Holat
