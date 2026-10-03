import os
import time
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import sqlite3
import base64
from html import escape

# =========================================================
# ALI KURYER BOT
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("XATO: BOT_TOKEN topilmadi.")
    raise SystemExit

API = f"https://api.telegram.org/bot{TOKEN}"

users = {}
carts = {}
orders = {}

DB_PATH = os.getenv("DB_PATH", "ali_kuryer.db")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE,
        name TEXT,
        username TEXT,
        phone TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS restaurants(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS menu_items(
        id TEXT PRIMARY KEY,
        restaurant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT,
        photo_url TEXT,
        active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS orders(
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        restaurant_name TEXT,
        items_json TEXT,
        total INTEGER,
        status TEXT,
        restaurant_phone TEXT,
        courier_phone TEXT,
        latitude REAL,
        longitude REAL,
        address TEXT,
        payment_method TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS couriers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        status TEXT DEFAULT 'offline',
        latitude REAL,
        longitude REAL,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS complaints(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_id TEXT,
        text TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS audit_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT,
        action TEXT,
        details TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    for rid, restaurant in RESTAURANTS.items():

        conn.execute(
            "INSERT OR IGNORE INTO restaurants(id,name) VALUES(?,?)",
            (rid, restaurant["name"])
        )

        for iid, item in restaurant["items"].items():

            conn.execute(
                """
                INSERT OR IGNORE INTO menu_items
                (id,restaurant_id,name,price,description)
                VALUES(?,?,?,?,?)
                """,
                (
                    iid,
                    rid,
                    item["name"],
                    item["price"],
                    item.get("description", "")
                )
            )

    conn.commit()
    conn.close()


def db_user(user_id, name, username):

    conn = db()

    conn.execute(
        """
        INSERT INTO users(telegram_id,name,username)
        VALUES(?,?,?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET
            name=excluded.name,
            username=excluded.username
        """,
        (
            user_id,
            name,
            username
        )
    )

    conn.commit()
    conn.close()


def db_order(order):

    conn = db()

    conn.execute(
        """
        INSERT OR REPLACE INTO orders
        (id,user_id,restaurant_name,items_json,total,status)
        VALUES(?,?,?,?,?,?)
        """,
        (
            order["id"],
            order["user_id"],
            order.get("restaurant_name", ""),
            json.dumps(order["items"], ensure_ascii=False),
            order["total"],
            order["status"]
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# RESTORANLAR
# =========================================================

RESTAURANTS = {

    "1": {
        "name": "Ali Burger",
        "items": {

            "101": {
                "name": "Classic Burger",
                "price": 30000,
                "description": "Mol go'shti, pishloq, salat va sous"
            },

            "102": {
                "name": "Chicken Burger",
                "price": 28000,
                "description": "Tovuq go'shti, salat va maxsus sous"
            },

            "103": {
                "name": "Fri",
                "price": 12000,
                "description": "Qarsildoq kartoshka fri"
            }
        }
    },

    "2": {
        "name": "Osh Markazi",
        "items": {

            "201": {
                "name": "O'zbek Palovi",
                "price": 35000,
                "description": "Guruch, go'sht, sabzi va no'xat"
            },

            "202": {
                "name": "Chuchvara",
                "price": 25000,
                "description": "Uy uslubidagi chuchvara"
            },

            "203": {
                "name": "Achichuk",
                "price": 10000,
                "description": "Pomidor, piyoz va ko'katlar"
            }
        }
    },

    "3": {
        "name": "Pizza House",
        "items": {

            "301": {
                "name": "Pepperoni Pizza",
                "price": 65000,
                "description": "Pishloq, pepperoni va pomidor sousi"
            },

            "302": {
                "name": "Chicken Pizza",
                "price": 60000,
                "description": "Tovuq go'shti, pishloq va sous"
            },

            "303": {
                "name": "Margherita",
                "price": 50000,
                "description": "Pishloq, pomidor va maxsus sous"
            }
        }
    }
}


# =========================================================
# TELEGRAM API
# =========================================================

def telegram(method, data=None):

    try:

        url = f"{API}/{method}"

        if data:

            encoded = urllib.parse.urlencode(data).encode("utf-8")

            request = urllib.request.Request(
                url,
                data=encoded
            )

        else:

            request = urllib.request.Request(url)

        with urllib.request.urlopen(
            request,
            timeout=40
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except Exception as e:

        print("Telegram API xatosi:", e)

        return None


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:

        data["reply_markup"] = json.dumps(
            keyboard,
            ensure_ascii=False
        )

    return telegram(
        "sendMessage",
        data
    )


def answer_callback(callback_id, text=""):

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id,
            "text": text
        }
    )


# =========================================================
# KEYBOARD
# =========================================================

def main_keyboard():

    return {
        "keyboard": [

            [
                {
                    "text": "🍔 Buyurtma berish"
                },
                {
                    "text": "🍽 Restoranlar"
                }
            ],

            [
                {
                    "text": "📦 Buyurtmalarim"
                },
                {
                    "text": "📍 Buyurtmani kuzatish"
                }
            ],

            [
                {
                    "text": "👤 Profilim"
                },
                {
                    "text": "💬 Yordam"
                }
            ],

            [
                {
                    "text": "🛵 Kuryer bo‘lish"
                },
                {
                    "text": "🏪 Restoran hamkorligi"
                }
            ]

        ],

        "resize_keyboard": True
    }


def restaurants_keyboard():

    buttons = []

    for rid, restaurant in RESTAURANTS.items():

        buttons.append(
            [
                {
                    "text": restaurant["name"],
                    "callback_data": f"restaurant:{rid}"
                }
            ]
        )

    return {
        "inline_keyboard": buttons
    }


# =========================================================
# RESTORAN MENYUSI
# =========================================================

def restaurant_menu_keyboard(restaurant_id):

    restaurant = RESTAURANTS[restaurant_id]

    buttons = []

    for item_id, item in restaurant["items"].items():

        buttons.append(
            [
                {
                    "text": f"{item['name']} — {item['price']:,} so'm",
                    "callback_data": f"item:{restaurant_id}:{item_id}"
                }
            ]
        )

    buttons.append(
        [
            {
                "text": "🛒 Savat",
                "callback_data": "cart"
            }
        ]
    )

    return {
        "inline_keyboard": buttons
    }


def item_keyboard(restaurant_id, item_id):

    return {
        "inline_keyboard": [

            [
                {
                    "text": "➕ Savatga qo‘shish",
                    "callback_data": f"add:{restaurant_id}:{item_id}"
                }
            ],

            [
                {
                    "text": "🛒 Savatni ko‘rish",
                    "callback_data": "cart"
                }
            ]

        ]
    }


# =========================================================
# BUYURTMA
# =========================================================

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

    for index, product in enumerate(cart, 1):

        price = product["price"]

        total += price

        text += (
            f"{index}. {product['name']}\n"
            f"   {price:,} so'm\n\n"
        )

    text += f"💰 Jami: {total:,} so'm"

    return text


def cart_keyboard(user_id):

    cart = get_cart(user_id)

    if not cart:

        return {
            "inline_keyboard": [
                [
                    {
                        "text": "🍔 Buyurtma berish",
                        "callback_data": "restaurants"
                    }
                ]
            ]
        }

    return {
        "inline_keyboard": [

            [
                {
                    "text": "✅ Buyurtmani tasdiqlash",
                    "callback_data": "checkout"
                }
            ],

            [
                {
                    "text": "🗑 Savatni tozalash",
                    "callback_data": "clear_cart"
                }
            ]

        ]
    }


# =========================================================
# BUYURTMA YARATISH
# =========================================================

def create_order(user_id):

    cart = get_cart(user_id)

    if not cart:

        return None

    order_id = str(
        int(time.time())
    )[-6:]

    total = sum(
        item["price"]
        for item in cart
    )

    orders[user_id] = {

        "id": order_id,

        "user_id": user_id,

        "restaurant_name":
            cart[0].get(
                "restaurant",
                ""
            ) if cart else "",

        "items": cart.copy(),

        "total": total,

        "status": "Qabul qilindi"
    }

    db_order(
        orders[user_id]
    )

    carts[user_id] = []

    return orders[user_id]


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):

    chat = message.get(
        "chat",
        {}
    )

    user = message.get(
        "from",
        {}
    )

    chat_id = chat.get("id")

    user_id = user.get("id")

    if not chat_id:

        return

    first_name = user.get(
        "first_name",
        "Mijoz"
    )

    users[user_id] = {

        "id": user_id,

        "name": first_name,

        "username":
            user.get(
                "username",
                ""
            )
    }

    db_user(
        user_id,
        first_name,
        user.get(
            "username",
            ""
        )
    )

    text = message.get(
        "text",
        ""
    ).strip()

    if text == "/start":

        send_message(

            chat_id,

            f"👋 Assalomu alaykum, {first_name}!\n\n"
            "🛵 Ali Kuryer botiga xush kelibsiz!\n\n"
            "Tez, xavfsiz va ishonchli yetkazib berish xizmati.",

            main_keyboard()
        )

        return

    if text in [
        "/order",
        "🍔 Buyurtma berish"
    ]:

        send_message(

            chat_id,

            "🍔 Buyurtma berish uchun restoranni tanlang:",

            restaurants_keyboard()
        )

        return

    if text in [
        "/restaurants",
        "🍽 Restoranlar"
    ]:

        send_message(

            chat_id,

            "🍽 Bizning restoranlar:",

            restaurants_keyboard()
        )

        return

    if text in [
        "/orders",
        "📦 Buyurtmalarim"
    ]:

        if user_id not in orders:

            send_message(

                chat_id,

                "📦 Sizda hozircha buyurtmalar yo‘q.",

                main_keyboard()
            )

        else:

            order = orders[user_id]

            send_message(

                chat_id,

                f"📦 Buyurtma №{order['id']}\n\n"
                f"💰 Summa: {order['total']:,} so'm\n"
                f"📌 Holati: {order['status']}",

                main_keyboard()
            )

        return

    if text in [
        "/track",
        "📍 Buyurtmani kuzatish"
    ]:

        if user_id not in orders:

            send_message(

                chat_id,

                "📍 Kuzatish uchun avval buyurtma bering.",

                main_keyboard()
            )

        else:

            order = orders[user_id]

            send_message(

                chat_id,

                f"📍 Buyurtma №{order['id']}\n\n"
                f"Holati: {order['status']}\n\n"
                "🛵 Kuryer tayinlangach, "
                "yetkazib berish holati yangilanadi.",

                main_keyboard()
            )

        return
