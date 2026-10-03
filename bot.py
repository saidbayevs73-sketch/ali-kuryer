import os
import time
import json
import html
import sqlite3
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread, Lock

# =========================================================
# ALI KURYER — BOT + DATABASE + ADMIN PANEL
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "AliKuryer@2026")
DB_PATH = os.getenv("DB_PATH", "ali_kuryer.db")
PORT = int(os.getenv("PORT", "10000"))

if not TOKEN:
    print("XATO: BOT_TOKEN topilmadi.")
    raise SystemExit

API = f"https://api.telegram.org/bot{TOKEN}"
DB_LOCK = Lock()

# =========================================================
# DATABASE
# =========================================================

def db():
    con = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with DB_LOCK, db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL DEFAULT '',
            last_name TEXT NOT NULL DEFAULT '',
            username TEXT NOT NULL DEFAULT '',
            phone TEXT NOT NULL DEFAULT '',
            latitude REAL,
            longitude REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            price INTEGER NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            image_url TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
        );
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT NOT NULL,
            phone TEXT NOT NULL DEFAULT '',
            transport TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'offline',
            blocked INTEGER NOT NULL DEFAULT 0,
            latitude REAL,
            longitude REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            restaurant_id INTEGER,
            items_json TEXT NOT NULL,
            total INTEGER NOT NULL,
            delivery_fee INTEGER NOT NULL DEFAULT 0,
            payment_method TEXT NOT NULL DEFAULT 'cash',
            status TEXT NOT NULL DEFAULT 'new',
            courier_id INTEGER,
            customer_phone TEXT NOT NULL DEFAULT '',
            latitude REAL,
            longitude REAL,
            address TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)
        seed(con)


def seed(con):
    count = con.execute("SELECT COUNT(*) AS n FROM restaurants").fetchone()["n"]
    if count == 0:
        restaurants = [
            ("Ali Burger", "+998 90 000 00 01", "Toshkent"),
            ("Osh Markazi", "+998 90 000 00 02", "Toshkent"),
            ("Pizza House", "+998 90 000 00 03", "Toshkent"),
        ]
        con.executemany("INSERT INTO restaurants(name,phone,address) VALUES(?,?,?)", restaurants)
        ids = [r[0] for r in con.execute("SELECT id FROM restaurants ORDER BY id").fetchall()]
        menus = [
            (ids[0], "Classic Burger", 30000, "Mol go'shti, pishloq, salat va sous", ""),
            (ids[0], "Chicken Burger", 28000, "Tovuq go'shti, salat va maxsus sous", ""),
            (ids[0], "Fri", 12000, "Qarsildoq kartoshka fri", ""),
            (ids[1], "O'zbek Palovi", 35000, "Guruch, go'sht, sabzi va no'xat", ""),
            (ids[1], "Chuchvara", 25000, "Uy uslubidagi chuchvara", ""),
            (ids[1], "Achichuk", 10000, "Pomidor, piyoz va ko'katlar", ""),
            (ids[2], "Pepperoni Pizza", 65000, "Pishloq, pepperoni va pomidor sousi", ""),
            (ids[2], "Chicken Pizza", 60000, "Tovuq go'shti, pishloq va sous", ""),
            (ids[2], "Margherita", 50000, "Pishloq, pomidor va maxsus sous", ""),
        ]
        con.executemany("INSERT INTO menu_items(restaurant_id,name,price,description,image_url) VALUES(?,?,?,?,?)", menus)
        con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES('delivery_fee','5000')")
        con.commit()


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):
    try:
        url = f"{API}/{method}"
        if data is not None:
            encoded = urllib.parse.urlencode(data).encode("utf-8")
            req = urllib.request.Request(url, data=encoded)
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=40) as response:
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
    return telegram("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


# =========================================================
# USER STATE
# =========================================================
state = {}


def get_state(uid):
    return state.setdefault(uid, {"cart": [], "checkout": False})


def save_user(message):
    u = message.get("from", {})
    uid = u.get("id")
    if not uid:
        return None
    with DB_LOCK, db() as con:
        con.execute("""
            INSERT INTO users(id,first_name,last_name,username,updated_at)
            VALUES(?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
              first_name=excluded.first_name,
              last_name=excluded.last_name,
              username=excluded.username,
              updated_at=CURRENT_TIMESTAMP
        """, (uid, u.get("first_name", ""), u.get("last_name", ""), u.get("username", "")))
        con.commit()
    return uid


def update_phone(uid, phone):
    with DB_LOCK, db() as con:
        con.execute("UPDATE users SET phone=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (phone, uid))
        con.commit()


def update_location(uid, lat, lon):
    with DB_LOCK, db() as con:
        con.execute("UPDATE users SET latitude=?,longitude=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (lat, lon, uid))
        con.commit()


def user_row(uid):
    with db() as con:
        return con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard():
    return {"keyboard": [
        [{"text":"🍔 Buyurtma berish"},{"text":"🍽 Restoranlar"}],
        [{"text":"📦 Buyurtmalarim"},{"text":"📍 Buyurtmani kuzatish"}],
        [{"text":"👤 Profilim"},{"text":"💬 Yordam"}],
        [{"text":"🛵 Kuryer bo‘lish"},{"text":"🏪 Restoran hamkorligi"}],
    ], "resize_keyboard": True}


def phone_keyboard():
    return {"keyboard":[
        [{"text":"📞 Telefon raqamimni yuborish", "request_contact":True}],
        [{"text":"❌ Bekor qilish"}]
    ], "resize_keyboard":True, "one_time_keyboard":True}


def location_keyboard():
    return {"keyboard":[
        [{"text":"📍 Lokatsiyamni yuborish", "request_location":True}],
        [{"text":"❌ Bekor qilish"}]
    ], "resize_keyboard":True, "one_time_keyboard":True}


def restaurants_keyboard():
    with db() as con:
        rows = con.execute("SELECT id,name FROM restaurants WHERE active=1 ORDER BY id").fetchall()
    return {"inline_keyboard":[[{"text":r["name"],"callback_data":f"restaurant:{r['id']}"}] for r in rows]}


def menu_keyboard(rid):
    with db() as con:
        rows = con.execute("SELECT id,name,price FROM menu_items WHERE restaurant_id=? AND active=1 ORDER BY id",(rid,)).fetchall()
    buttons = [[{"text":f"{r['name']} — {r['price']:,} so'm","callback_data":f"item:{rid}:{r['id']}"}] for r in rows]
    buttons.append([{"text":"🛒 Savat","callback_data":"cart"}])
    return {"inline_keyboard":buttons}


def item_keyboard(rid,iid):
    return {"inline_keyboard":[
        [{"text":"➕ Savatga qo‘shish","callback_data":f"add:{rid}:{iid}"}],
        [{"text":"🛒 Savatni ko‘rish","callback_data":"cart"}]
    ]}


def cart_keyboard():
    return {"inline_keyboard":[
        [{"text":"✅ Buyurtmani tasdiqlash","callback_data":"checkout"}],
        [{"text":"🗑 Savatni tozalash","callback_data":"clear_cart"}]
    ]}


def payment_keyboard():
    return {"inline_keyboard":[
        [{"text":"💵 Naqd","callback_data":"pay:cash"}],
        [{"text":"💳 Bank karta","callback_data":"pay:card"}],
        [{"text":"🌐 Online to‘lov","callback_data":"pay:online"}]
    ]}


# =========================================================
# CART / ORDERS
# =========================================================

def cart_text(uid):
    cart = get_state(uid)["cart"]
    if not cart:
        return "🛒 Savatingiz hozircha bo‘sh."
    total = sum(x["price"] for x in cart)
    lines = ["🛒 SAVATINGIZ",""]
    for i,x in enumerate(cart,1):
        lines.append(f"{i}. {x['name']} — {x['price']:,} so'm")
    lines += ["",f"💰 Jami: {total:,} so'm"]
    return "\n".join(lines)


def create_order(uid, payment):
    s = get_state(uid)
    cart = s["cart"]
    row = user_row(uid)
    if not cart or not row:
        return None
    delivery = int(get_setting("delivery_fee","5000"))
    total = sum(x["price"] for x in cart) + delivery
    rid = cart[0].get("restaurant_id") if cart else None
    payload = json.dumps(cart, ensure_ascii=False)
    with DB_LOCK, db() as con:
        cur = con.execute("""
            INSERT INTO orders(customer_id,restaurant_id,items_json,total,delivery_fee,payment_method,
            status,customer_phone,latitude,longitude)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (uid,rid,payload,total,delivery,payment,row["phone"],row["latitude"],row["longitude"]))
        oid = cur.lastrowid
        con.commit()
    s["cart"] = []
    s["checkout"] = False
    return oid, total, delivery


def get_setting(key, default=""):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?",(key,)).fetchone()
        return row["value"] if row else default


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):
    chat_id = message.get("chat",{}).get("id")
    if not chat_id:
        return
    uid = save_user(message)
    u = message.get("from",{})
    first = u.get("first_name","Mijoz")
    s = get_state(uid)

    contact = message.get("contact")
    if contact and contact.get("phone_number"):
        update_phone(uid, contact["phone_number"])
        if s.get("checkout"):
            send_message(chat_id,"✅ Telefon raqamingiz saqlandi.\n\nEndi aniq lokatsiyangizni yuboring:",location_keyboard())
        else:
            send_message(chat_id,"✅ Telefon raqamingiz saqlandi.",main_keyboard())
        return

    location = message.get("location")
    if location:
        update_location(uid, location["latitude"], location["longitude"])
        if s.get("checkout"):
            send_message(chat_id,"📍 Lokatsiya qabul qilindi.\n\nTo‘lov usulini tanlang:",payment_keyboard())
        else:
            send_message(chat_id,"📍 Lokatsiyangiz saqlandi.",main_keyboard())
        return

    text = message.get("text","").strip()
    if text == "❌ Bekor qilish":
        s["checkout"] = False
        send_message(chat_id,"Bekor qilindi.",main_keyboard())
        return

    if text == "/start":
        send_message(chat_id,f"👋 Assalomu alaykum, {first}!\n\n🛵 Ali Kuryer botiga xush kelibsiz!\nTez, xavfsiz va ishonchli yetkazib berish xizmati.",main_keyboard()); return
    if text in ["/order","🍔 Buyurtma berish","/restaurants","🍽 Restoranlar"]:
        send_message(chat_id,"🍽 Restoranni tanlang:",restaurants_keyboard()); return
    if text in ["/orders","📦 Buyurtmalarim"]:
        with db() as con:
            rows=con.execute("SELECT id,total,status,created_at FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 10",(uid,)).fetchall()
        if not rows:
            send_message(chat_id,"📦 Sizda hozircha buyurtmalar yo‘q.",main_keyboard()); return
        lines=["📦 BUYURTMALARIM",""]
        for r in rows: lines.append(f"№{r['id']} — {r['total']:,} so'm — {status_uz(r['status'])}")
        send_message(chat_id,"\n".join(lines),main_keyboard()); return
    if text in ["/track","📍 Buyurtmani kuzatish"]:
        with db() as con:
            r=con.execute("SELECT id,status,courier_id,latitude,longitude FROM orders WHERE customer_id=? ORDER BY id DESC LIMIT 1",(uid,)).fetchone()
        if not r: send_message(chat_id,"📍 Kuzatish uchun avval buyurtma bering.",main_keyboard()); return
        msg=f"📍 Buyurtma №{r['id']}\nHolati: {status_uz(r['status'])}"
        if r["latitude"] is not None: msg += f"\n\n🗺 https://maps.google.com/?q={r['latitude']},{r['longitude']}"
        send_message(chat_id,msg,main_keyboard()); return
    if text in ["/profile","👤 Profilim"]:
        r=user_row(uid)
        send_message(chat_id,f"👤 PROFILIM\n\nIsm: {r['first_name']} {r['last_name']}\nTelefon: {r['phone'] or 'Kiritilmagan'}\nTelegram ID: {uid}",main_keyboard()); return
    if text in ["/support","💬 Yordam"]:
        send_message(chat_id,"💬 YORDAM\n\nMuammo yoki shikoyat bo‘lsa, shu yerga yozing. Administrator panelida ko‘rib chiqiladi.",main_keyboard()); return
    if text in ["/courier","🛵 Kuryer bo‘lish"]:
        with DB_LOCK, db() as con:
            con.execute("INSERT OR IGNORE INTO couriers(telegram_id,name) VALUES(?,?)",(uid,first)); con.commit()
        send_message(chat_id,"🛵 Kuryer arizangiz qabul qilindi. Administrator siz bilan bog‘lanadi.",main_keyboard()); return
    if text in ["/partner","🏪 Restoran hamkorligi"]:
        send_message(chat_id,"🏪 RESTORAN HAMKORLIGI\n\nRestoraningizni Ali Kuryer platformasiga ulash uchun administratorga murojaat qiling.",main_keyboard()); return
    if s.get("checkout") and text:
        send_message(chat_id,"Buyurtmani davom ettirish uchun telefon va lokatsiyani yuboring.",phone_keyboard()); return
    send_message(chat_id,"👇 Kerakli bo‘limni tanlang:",main_keyboard())


def status_uz(s):
    return {"new":"Qabul qilindi","confirmed":"Tasdiqlandi","preparing":"Tayyorlanmoqda","courier_search":"Kuryer qidirilmoqda","picked_up":"Kuryer oldi","delivering":"Yetkazilmoqda","delivered":"Yetkazildi","cancelled":"Bekor qilindi"}.get(s,s)


# =========================================================
# CALLBACK HANDLER
# =========================================================

def handle_callback(cb):
    cid=cb.get("id"); data=cb.get("data",""); msg=cb.get("message",{}); chat_id=msg.get("chat",{}).get("id"); uid=cb.get("from",{}).get("id")
    if not chat_id: return
    answer_callback(cid)
    if data=="restaurants": send_message(chat_id,"🍽 Restoranni tanlang:",restaurants_keyboard()); return
    if data.startswith("restaurant:"):
        rid=int(data.split(":")[1])
        with db() as con: r=con.execute("SELECT name,phone,address FROM restaurants WHERE id=?",(rid,)).fetchone()
        if r: send_message(chat_id,f"🍽 {r['name']}\n📞 {r['phone']}\n📍 {r['address']}\n\nMenyudan taom tanlang:",menu_keyboard(rid))
        return
    if data.startswith("item:"):
        _,rid,iid=data.split(":")
        with db() as con: r=con.execute("SELECT name,price,description FROM menu_items WHERE id=? AND restaurant_id=?",(iid,rid)).fetchone()
        if r: send_message(chat_id,f"🍽 {r['name']}\n\n💰 {r['price']:,} so'm\n📝 {r['description']}",item_keyboard(rid,iid))
        return
    if data.startswith("add:"):
        _,rid,iid=data.split(":")
        with db() as con: r=con.execute("SELECT name,price,description FROM menu_items WHERE id=? AND restaurant_id=?",(iid,rid)).fetchone()
        if r:
            get_state(uid)["cart"].append({"restaurant_id":int(rid),"name":r["name"],"price":r["price"],"description":r["description"]})
            send_message(chat_id,f"✅ {r['name']} savatga qo‘shildi!\n\n{cart_text(uid)}",cart_keyboard())
        return
    if data=="cart": send_message(chat_id,cart_text(uid),cart_keyboard()); return
    if data=="clear_cart": get_state(uid)["cart"]=[]; send_message(chat_id,"🗑 Savat tozalandi.",main_keyboard()); return
    if data=="checkout":
        if not get_state(uid)["cart"]: send_message(chat_id,"🛒 Savat bo‘sh.",main_keyboard()); return
        get_state(uid)["checkout"]=True
        r=user_row(uid)
        if not r["phone"]: send_message(chat_id,"📞 Buyurtma uchun telefon raqamingizni yuboring:",phone_keyboard()); return
        if r["latitude"] is None: send_message(chat_id,"📍 Endi aniq lokatsiyangizni yuboring:",location_keyboard()); return
        send_message(chat_id,"💳 To‘lov usulini tanlang:",payment_keyboard()); return
    if data.startswith("pay:"):
        pay=data.split(":")[1]
        r=user_row(uid)
        if not r or not r["phone"]: send_message(chat_id,"📞 Avval telefon raqamingizni yuboring.",phone_keyboard()); return
        if r["latitude"] is None: send_message(chat_id,"📍 Avval lokatsiyangizni yuboring.",location_keyboard()); return
        result=create_order(uid,pay)
        if not result: send_message(chat_id,"Savat bo‘sh.",main_keyboard()); return
        oid,total,delivery=result
        send_message(chat_id,f"✅ BUYURTMA QABUL QILINDI!\n\n📦 Buyurtma №{oid}\n💰 Mahsulotlar + yetkazib berish: {total:,} so'm\n🚚 Yetkazib berish: {delivery:,} so'm\n💳 To‘lov: {pay}\n📌 Holati: Qabul qilindi\n\n📍 Lokatsiyangiz kuryerga beriladi.",main_keyboard()); notify_admin_new_order(oid)


def notify_admin_new_order(oid):
    admin_chat=os.getenv("ADMIN_CHAT_ID")
    if not admin_chat: return
    with db() as con:
        r=con.execute("SELECT o.*,u.first_name,u.last_name FROM orders o LEFT JOIN users u ON u.id=o.customer_id WHERE o.id=?",(oid,)).fetchone()
    if not r: return
    send_message(admin_chat,f"🔔 YANGI BUYURTMA №{oid}\n👤 {r['first_name']} {r['last_name']}\n📞 {r['customer_phone']}\n💰 {r['total']:,} so'm\n📌 {status_uz(r['status'])}")


# =========================================================
# ADMIN WEB PANEL
# =========================================================

def esc(v): return html.escape(str(v if v is not None else ""))

def admin_page(title, body):
    return f"""<!doctype html><html lang='uz'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><t
