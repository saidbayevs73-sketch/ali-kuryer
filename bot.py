import os
import time
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

# =========================
# ALI KURYER BOT
# =========================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("XATO: BOT_TOKEN topilmadi.")
    exit()

API = f"https://api.telegram.org/bot{TOKEN}"


# =========================
# TELEGRAM API
# =========================

def telegram(method, data=None):
    try:
        if data is None:
            data = {}

        encoded = urllib.parse.urlencode(data).encode("utf-8")

        request = urllib.request.Request(
            f"{API}/{method}",
            data=encoded,
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as e:
        print("Telegram API xatosi:", e)
        return None


def send_message(chat_id, text):
    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# =========================
# RESTORANLAR
# =========================

RESTAURANTS = {
    "1": {
        "name": "Ali Burger",
        "foods": [
            ("🍔 Burger", "25000 so'm"),
            ("🍟 Kartoshka fri", "12000 so'm"),
            ("🥤 Cola", "8000 so'm")
        ]
    },
    "2": {
        "name": "Osh Markazi",
        "foods": [
            ("🍚 Osh", "30000 so'm"),
            ("🥗 Salat", "10000 so'm"),
            ("🥤 Choy", "5000 so'm")
        ]
    },
    "3": {
        "name": "Pizza House",
        "foods": [
            ("🍕 Margarita pizza", "55000 so'm"),
            ("🍕 Go'shtli pizza", "65000 so'm"),
            ("🥤 Cola", "8000 so'm")
        ]
    }
}


# =========================
# FOYDALANUVCHILAR
# =========================

users = {}
carts = {}


# =========================
# BUYRUQLAR
# =========================

def show_start(chat_id):
    text = (
        "Assalomu alaykum! 👋\n\n"
        "🛵 Ali Kuryer botiga xush kelibsiz!\n\n"
        "Tez, xavfsiz va ishonchli yetkazib berish xizmati.\n\n"
        "Buyruqlar:\n"
        "/order - 🍔 Buyurtma berish\n"
        "/restaurants - 🍽 Restoranlar\n"
        "/orders - 📦 Buyurtmalarim\n"
        "/track - 📍 Buyurtmani kuzatish\n"
        "/profile - 👤 Profilim\n"
        "/support - 💬 Yordam\n"
        "/courier - 🛵 Kuryer bo‘lish\n"
        "/partner - 🏪 Restoran hamkorligi"
    )

    send_message(chat_id, text)


def show_restaurants(chat_id):
    text = "🍽 RESTORANLAR\n\n"

    for number, restaurant in RESTAURANTS.items():
        text += f"{number}. {restaurant['name']}\n"

    text += "\nRestoran raqamini yuboring."

    send_message(chat_id, text)


def show_restaurant(chat_id, number):
    if number not in RESTAURANTS:
        return

    restaurant = RESTAURANTS[number]

    text = f"🍽 {restaurant['name']}\n\n"

    for food, price in restaurant["foods"]:
        text += f"{food} — {price}\n"

    text += (
        "\nBuyurtma berish uchun taom nomini yuboring.\n"
        "Masalan: Burger"
    )

    send_message(chat_id, text)


def handle_command(chat_id, text):

    if text == "/start":
        users[chat_id] = {
            "chat_id": chat_id,
            "name": ""
        }
        show_start(chat_id)

    elif text == "/order":
        show_restaurants(chat_id)

    elif text == "/restaurants":
        show_restaurants(chat_id)

    elif text == "/orders":
        send_message(
            chat_id,
            "📦 Sizda hozircha buyurtmalar mavjud emas."
        )

    elif text == "/track":
        send_message(
            chat_id,
            "📍 Hozircha faol buyurtmangiz yo‘q."
        )

    elif text == "/profile":
        send_message(
            chat_id,
            "👤 Profilingiz\n\n"
            f"Telegram ID: {chat_id}"
        )

    elif text == "/support":
        send_message(
            chat_id,
            "💬 Ali Kuryer yordam xizmati\n\n"
            "Savolingizni shu yerga yozing."
        )

    elif text == "/courier":
        send_message(
            chat_id,
            "🛵 KURYER BO‘LISH\n\n"
            "Ali Kuryer jamoasiga qo‘shilish uchun "
            "telefon raqamingizni yuboring."
        )

    elif text == "/partner":
        send_message(
            chat_id,
            "🏪 RESTORAN HAMKORLIGI\n\n"
            "Restoran nomi va telefon raqamingizni yuboring."
        )

    elif text in RESTAURANTS:
        show_restaurant(chat_id, text)

    else:
        send_message(
            chat_id,
            "Tushundim. 😊\n\n"
            "Menyu uchun /order buyrug‘ini yuboring."
        )


# =========================
# UPDATE QABUL QILISH
# =========================

def process_update(update):

    if "message" in update:

        message = update["message"]
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not chat_id:
            return

        text = message.get("text", "").strip()

        if text:
            handle_command(chat_id, text)


# =========================
# TELEGRAM POLLING
# =========================

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
                    process_update(update)

                except Exception as e:
                    print("Update xatosi:", e)

        except Exception as e:

            print("Bot xatosi:", e)

            time.sleep(5)


# =========================
# RENDER HEALTH SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"Ali Kuryer Bot OK"
        )

    def log_message(self, format, *args):
        pass


def health_server():

    port = int(
        os.getenv("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Health server ishga tushdi: {port}"
    )

    server.serve_forever()


# =========================
# START
# =========================

if __name__ == "__main__":

    Thread(
        target=health_server,
        daemon=True
    ).start()

    bot_loop()
