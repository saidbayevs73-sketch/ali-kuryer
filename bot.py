import os
import time
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

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
            request = urllib.request.Request(url, data=encoded)
        else:
            request = urllib.request.Request(url)

        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as e:
        print("Telegram API xatosi:", e)
        return None


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)

    return telegram("sendMessage", data)


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
                {"text": "🍔 Buyurtma berish"},
                {"text": "🍽 Restoranlar"}
            ],
            [
                {"text": "📦 Buyurtmalarim"},
                {"text": "📍 Buyurtmani kuzatish"}
            ],
            [
                {"text": "👤 Profilim"},
                {"text": "💬 Yordam"}
            ],
            [
                {"text": "🛵 Kuryer bo‘lish"},
                {"text": "🏪 Restoran hamkorligi"}
            ]
        ],
        "resize_keyboard": True
    }


def restaurants_keyboard():
    buttons = []

    for rid, restaurant in RESTAURANTS.items():
        buttons.append([
            {
                "text": restaurant["name"],
                "callback_data": f"restaurant:{rid}"
            }
        ])

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
        buttons.append([
            {
                "text": f"{item['name']} — {item['price']:,} so'm",
                "callback_data": f"item:{restaurant_id}:{item_id}"
            }
        ])

    buttons.append([
        {
            "text": "🛒 Savat",
            "callback_data": "cart"
        }
    ])

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

    order_id = str(int(time.time()))[-6:]

    total = sum(item["price"] for item in cart)

    orders[user_id] = {
        "id": order_id,
        "items": cart.copy(),
        "total": total,
        "status": "Qabul qilindi"
    }

    carts[user_id] = []

    return orders[user_id]


# =========================================================
# MESSAGE HANDLER
# =========================================================

def handle_message(message):
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")

    if not chat_id:
        return

    first_name = user.get("first_name", "Mijoz")

    users[user_id] = {
        "id": user_id,
        "name": first_name,
        "username": user.get("username", "")
    }

    text = message.get("text", "").strip()

    if text == "/start":
        send_message(
            chat_id,
            f"👋 Assalomu alaykum, {first_name}!\n\n"
            "🛵 Ali Kuryer botiga xush kelibsiz!\n\n"
            "Tez, xavfsiz va ishonchli yetkazib berish xizmati.",
            main_keyboard()
        )
        return

    if text in ["/order", "🍔 Buyurtma berish"]:
        send_message(
            chat_id,
            "🍔 Buyurtma berish uchun restoranni tanlang:",
            restaurants_keyboard()
        )
        return

    if text in ["/restaurants", "🍽 Restoranlar"]:
        send_message(
            chat_id,
            "🍽 Bizning restoranlar:",
            restaurants_keyboard()
        )
        return

    if text in ["/orders", "📦 Buyurtmalarim"]:
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

    if text in ["/track", "📍 Buyurtmani kuzatish"]:
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
                "🛵 Kuryer tayinlangach, yetkazib berish holati yangilanadi.",
                main_keyboard()
            )
        return

    if text in ["/profile", "👤 Profilim"]:
        username = users[user_id].get("username", "")

        if username:
            username_text = f"@{username}"
        else:
            username_text = "Ko‘rsatilmagan"

        send_message(
            chat_id,
            "👤 PROFILIM\n\n"
            f"Ism: {first_name}\n"
            f"Username: {username_text}\n"
            f"Telegram ID: {user_id}",
            main_keyboard()
        )
        return

    if text in ["/support", "💬 Yordam"]:
        send_message(
            chat_id,
            "💬 YORDAM\n\n"
            "Savol yoki muammo bo‘lsa, administrator bilan bog‘laning.\n\n"
            "📞 Ali Kuryer qo‘llab-quvvatlash xizmati\n"
            "🕐 Har kuni 09:00–23:00",
            main_keyboard()
        )
        return

    if text in ["/courier", "🛵 Kuryer bo‘lish"]:
        send_message(
            chat_id,
            "🛵 KURYER BO‘LISH\n\n"
            "Ali Kuryer jamoasiga qo‘shiling!\n\n"
            "Kerakli ma’lumotlar:\n"
            "• Ism-familiya\n"
            "• Telefon raqam\n"
            "• Transport turi\n"
            "• Ishlash hududi\n\n"
            "Ariza uchun administrator bilan bog‘laning.",
            main_keyboard()
        )
        return

    if text in ["/partner", "🏪 Restoran hamkorligi"]:
        send_message(
            chat_id,
            "🏪 RESTORAN HAMKORLIGI\n\n"
            "Restoraningizni Ali Kuryer platformasiga ulang.\n\n"
            "Biz sizga:\n"
            "• Restoran sahifasi\n"
            "• Menyu boshqaruvi\n"
            "• Buyurtmalar\n"
            "• Kuryer yetkazib berish\n"
            "• Hisobotlar\n\n"
            "taqdim qilamiz.\n\n"
            "Hamkorlik uchun administrator bilan bog‘laning.",
            main_keyboard()
        )
        return

    send_message(
        chat_id,
        "👇 Kerakli bo‘limni tanlang:",
        main_keyboard()
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = callback.get("from", {}).get("id")

    if not chat_id:
        return

    answer_callback(callback_id)

    if data == "restaurants":
        send_message(
            chat_id,
            "🍽 Restoranni tanlang:",
            restaurants_keyboard()
        )
        return

    if data.startswith("restaurant:"):
        restaurant_id = data.split(":")[1]

        if restaurant_id not in RESTAURANTS:
            return

        restaurant = RESTAURANTS[restaurant_id]

        send_message(
            chat_id,
            f"🍽 {restaurant['name']}\n\n"
            "Menyudan taom tanlang:",
            restaurant_menu_keyboard(restaurant_id)
        )
        return

    if data.startswith("item:"):
        parts = data.split(":")
        restaurant_id = parts[1]
        item_id = parts[2]

        restaurant = RESTAURANTS.get(restaurant_id)

        if not restaurant:
            return

        item = restaurant["items"].get(item_id)

        if not item:
            return

        send_message(
            chat_id,
            f"🍽 {item['name']}\n\n"
            f"💰 Narxi: {item['price']:,} so'm\n\n"
            f"📝 {item['description']}",
            item_keyboard(restaurant_id, item_id)
        )
        return

    if data.startswith("add:"):
        parts = data.split(":")
        restaurant_id = parts[1]
        item_id = parts[2]

        restaurant = RESTAURANTS.get(restaurant_id)

        if not restaurant:
            return

        item = restaurant["items"].get(item_id)

        if not item:
            return

        cart = get_cart(user_id)

        cart.append({
            "restaurant": restaurant["name"],
            "name": item["name"],
            "price": item["price"]
        })

        send_message(
            chat_id,
            f"✅ {item['name']} savatga qo‘shildi!\n\n"
            + cart_text(user_id),
            cart_keyboard(user_id)
        )
        return

    if data == "cart":
        send_message(
            chat_id,
            cart_text(user_id),
            cart_keyboard(user_id)
        )
        return

    if data == "clear_cart":
        carts[user_id] = []

        send_message(
            chat_id,
            "🗑 Savat tozalandi.",
            main_keyboard()
        )
        return

    if data == "checkout":
        order = create_order(user_id)

        if not order:
            send_message(
                chat_id,
                "🛒 Savat bo‘sh.",
                main_keyboard()
            )
            return

        send_message(
            chat_id,
            f"✅ BUYURTMA QABUL QILINDI!\n\n"
            f"📦 Buyurtma №{order['id']}\n"
            f"💰 Jami: {order['total']:,} so'm\n"
            f"📌 Holati: {order['status']}\n\n"
            "🛵 Kuryer tayinlangach, sizga xabar beramiz.",
            main_keyboard()
        )
        return


# =========================================================
# UPDATE'LARNI OLISH
# =========================================================

def bot_loop():
    print("Ali Kuryer bot ishga tushdi...")

    offset = 0

    while True:
        try:
            result = telegram(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 30
                }
            )

            if not result or not result.get("ok"):
                time.sleep(3)
                continue

            updates = result.get("result", [])

            for update in updates:
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
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Ali Kuryer Bot OK")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Health server ishga tushdi: {port}")

    server.serve_forever()


# =========================================================
# BOSHLASH
# =========================================================

if __name__ == "__main__":

    health_thread = Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    bot_loop()
