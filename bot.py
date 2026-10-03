import os
import json
import time
import urllib.request
import urllib.parse

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("XATO: BOT_TOKEN topilmadi.")
    print("Tokenni serverda BOT_TOKEN sifatida o'rnating.")
    exit()

API = f"https://api.telegram.org/bot{TOKEN}"

users = {}
carts = {}

RESTAURANTS = {
    "1": {
        "name": "Ali Burger",
        "foods": {
            "1": {
                "name": "Cheeseburger",
                "price": 25000,
                "description": "Go'sht, pishloq, salat va maxsus sous.",
                "photo": ""
            },
            "2": {
                "name": "Burger Combo",
                "price": 35000,
                "description": "Burger + kartoshka fri + ichimlik.",
                "photo": ""
            }
        }
    },
    "2": {
        "name": "Ali Pizza",
        "foods": {
            "1": {
                "name": "Margarita Pizza",
                "price": 45000,
                "description": "Pomidor, pishloq va maxsus sous.",
                "photo": ""
            },
            "2": {
                "name": "Go'shtli Pizza",
                "price": 55000,
                "description": "Go'sht, pishloq, pomidor va sous.",
                "photo": ""
            }
        }
    }
}


def telegram(method, data=None):
    if data is None:
        data = {}

    encoded = urllib.parse.urlencode(data).encode()

    try:
        request = urllib.request.Request(
            f"{API}/{method}",
            data=encoded
        )

        response = urllib.request.urlopen(request, timeout=30)
        return json.loads(response.read().decode())

    except Exception as e:
        print("Telegram xatosi:", e)
        return None


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)

    return telegram("sendMessage", data)


def main_menu():
    return {
        "keyboard": [
            [{"text": "🍔 Buyurtma berish"}],
            [{"text": "🍽 Restoranlar"}, {"text": "📦 Buyurtmalarim"}],
            [{"text": "📍 Buyurtmani kuzatish"}],
            [{"text": "👤 Profilim"}, {"text": "💬 Yordam"}],
            [{"text": "🛵 Kuryer bo‘lish"}],
            [{"text": "🏪 Restoran hamkorligi"}]
        ],
        "resize_keyboard": True
    }


def restaurants_menu():
    buttons = []

    for restaurant_id, restaurant in RESTAURANTS.items():
        buttons.append([
            {
                "text": f"🍽 {restaurant['name']}",
                "callback_data": f"restaurant_{restaurant_id}"
            }
        ])

    return {
        "inline_keyboard": buttons
    }


def foods_menu(restaurant_id):
    restaurant = RESTAURANTS[restaurant_id]

    buttons = []

    for food_id, food in restaurant["foods"].items():
        buttons.append([
            {
                "text": f"{food['name']} — {food['price']:,} so'm",
                "callback_data": f"food_{restaurant_id}_{food_id}"
            }
        ])

    buttons.append([
        {
            "text": "⬅️ Restoranlar",
            "callback_data": "restaurants"
        }
    ])

    return {
        "inline_keyboard": buttons
    }


def get_cart(user_id):
    return carts.get(str(user_id), [])


def cart_text(user_id):
    cart = get_cart(user_id)

    if not cart:
        return "🛒 Savatchangiz hozircha bo‘sh."

    total = 0
    text = "🛒 SAVATCHA\n\n"

    for item in cart:
        text += f"🍔 {item['name']} x {item['quantity']}\n"
        text += f"💰 {item['price']:,} so'm\n\n"

        total += item["price"] * item["quantity"]

    text += f"💵 Jami: {total:,} so'm"

    return text


def handle_message(message):
    chat = message.get("chat", {})
    user = message.get("from", {})

    chat_id = chat.get("id")
    user_id = user.get("id")

    text = message.get("text", "")

    if not chat_id:
        return

    users[str(user_id)] = {
        "id": user_id,
        "first_name": user.get("first_name", ""),
        "username": user.get("username", "")
    }

    if text.startswith("/start"):
        send_message(
            chat_id,
            "🛵 Ali Kuryer botiga xush kelibsiz!\n\n"
            "Tez, xavfsiz va ishonchli yetkazib berish xizmati.",
            main_menu()
        )
        return

    if text == "🍔 Buyurtma berish" or text == "🍽 Restoranlar":
        send_message(
            chat_id,
            "🍽 Restoranni tanlang:",
            restaurants_menu()
        )
        return

    if text == "📦 Buyurtmalarim":
        send_message(
            chat_id,
            "📦 Sizning buyurtmalaringiz hozircha yo‘q."
        )
        return

    if text == "📍 Buyurtmani kuzatish":
        send_message(
            chat_id,
            "📍 Hozir faol buyurtmangiz yo‘q."
        )
        return

    if text == "👤 Profilim":
        u = users.get(str(user_id), {})

        send_message(
            chat_id,
            "👤 PROFIL\n\n"
            f"Ism: {u.get('first_name', '-')}\n"
            f"Username: @{u.get('username', '-')}\n\n"
            "🛵 Ali Kuryer"
        )
        return

    if text == "💬 Yordam":
        send_message(
            chat_id,
            "💬 Yordam\n\n"
            "Savollaringiz bo‘lsa administrator bilan bog‘laning."
        )
        return

    if text == "🛵 Kuryer bo‘lish":
        send_message(
            chat_id,
            "🛵 KURYER BO‘LISH\n\n"
            "Ali Kuryer jamoasiga kuryer sifatida qo‘shiling.\n\n"
            "Ariza topshirish uchun administrator bilan bog‘laning."
        )
        return

    if text == "🏪 Restoran hamkorligi":
        send_message(
            chat_id,
            "🏪 RESTORAN HAMKORLIGI\n\n"
            "Restoraningizni Ali Kuryer platformasiga qo‘shish uchun "
            "administrator bilan bog‘laning."
        )
        return


def handle_callback(callback):
    callback_id = callback.get("id")
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    telegram("answerCallbackQuery", {
        "callback_query_id": callback_id
    })

    if data == "restaurants":
        telegram("editMessageText", {
            "chat_id": chat_id,
            "message_id": message.get("message_id"),
            "text": "🍽 Restoranni tanlang:",
            "reply_markup": json.dumps(restaurants_menu())
        })
        return

    if data.startswith("restaurant_"):
        restaurant_id = data.split("_")[1]

        restaurant = RESTAURANTS.get(restaurant_id)

        if not restaurant:
            return

        telegram("editMessageText", {
            "chat_id": chat_id,
            "message_id": message.get("message_id"),
            "text": f"🍽 {restaurant['name']}\n\nTaomni tanlang:",
            "reply_markup": json.dumps(
                foods_menu(restaurant_id)
            )
        })
        return

    if data.startswith("food_"):
        parts = data.split("_")

        restaurant_id = parts[1]
        food_id = parts[2]

        restaurant = RESTAURANTS.get(restaurant_id)

        if not restaurant:
            return

        food = restaurant["foods"].get(food_id)

        if not food:
            return

        user_id = message.get("from", {}).get("id", chat_id)

        if str(user_id) not in carts:
            carts[str(user_id)] = []

        found = False

        for item in carts[str(user_id)]:
            if item["name"] == food["name"]:
                item["quantity"] += 1
                found = True
                break

        if not found:
            carts[str(user_id)].append({
                "name": food["name"],
                "price": food["price"],
                "quantity": 1
            })

        send_message(
            chat_id,
            f"✅ {food['name']} savatchaga qo‘shildi!\n\n"
            f"{cart_text(user_id)}",
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "🍔 Yana taom tanlash",
                            "callback_data": f"restaurant_{restaurant_id}"
                        }
                    ],
                    [
                        {
                            "text": "🛒 Savatchani ko‘rish",
                            "callback_data": "cart"
                        }
                    ]
                ]
            }
        )
        return

    if data == "cart":
        user_id = chat_id

        send_message(
            chat_id,
            cart_text(user_id),
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "🚚 Buyurtma berish",
                            "callback_data": "checkout"
                        }
                    ]
                ]
            }
        )
        return

    if data == "checkout":
        send_message(
            chat_id,
            "🚚 Buyurtmani rasmiylashtirish\n\n"
            "📍 Yetkazib berish manzilingizni yuboring.\n\n"
            "Keyingi bosqichda xarita orqali manzil olishni "
            "qo‘shamiz."
        )
        return


def main():
    print("Ali Kuryer bot ishga tushdi...")

    offset = 0

    while True:
        result = telegram("getUpdates", {
            "offset": offset,
            "timeout": 30
        })

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
                print("Xato:", e)


if __name__ == "__main__":
    main()
