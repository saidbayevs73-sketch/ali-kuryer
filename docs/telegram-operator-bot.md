# Ali Kuryer — Telegram operator yordami

Mavjud FastAPI saytga alohida operator Telegram boti qo‘shiladi.
U avvalgi buyurtma botining BOT_TOKEN qiymatiga tegmaydi.

## Bot nimalar qiladi?

1. Mijoz toifani tanlaydi: buyurtma, to‘lov, kuryer, restoran, shikoyat, boshqa.
2. Savol-javob bo‘limidagi oddiy savollarga tayyor javob beradi (AI emas).
3. Yangi murojaatga raqam beradi va operatorlar Telegram guruhiga yuboradi.
4. Operator kelgan murojaat yoki mijoz xabariga Reply qilib javob yozadi.
5. Javob bot orqali mijozning shaxsiy Telegram chatiga boradi.
6. Guruhda Reply qilib /close yuborilsa murojaat yopiladi; /take uni operatorga biriktiradi.
7. Kerak bo‘lsa, har bir toifa uchun alohida operatorlar guruhi belgilanadi.
8. Ma’lumotlar SQLite bazasida saqlanadi.

## Telegramda sozlash

1. https://t.me/BotFather ni oching va /newbot yuboring.
2. Bot nomini Ali Kuryer Yordam deb qo‘yishingiz mumkin; username mavjud bo‘lmasa boshqasini tanlang, oxiri bot bilan tugasin.
3. BotFather bergan tokenni xavfsiz saqlang. Chat yoki GitHub kodiga joylamang.
4. Telegramda yopiq Ali Kuryer Operatorlar guruhini yarating va yangi botni qo‘shing.
5. Guruh ichida /chatid (yoki /chatid@SizningBotUsername) yuboring. Bot guruh ID sini beradi.

## Render Environment

Oldingi Ali Kuryer web service ichida quyidagilarni qo‘shing:

| Kalit | Qiymat |
| --- | --- |
| SUPPORT_BOT_TOKEN | Yangi botning BotFather tokeni |
| SUPPORT_OPERATORS_CHAT_ID | Operator guruhining manfiy Telegram ID si |
| SUPPORT_PUBLIC_URL | Backend joylashgan haqiqiy HTTPS Render URL |
| SUPPORT_WEBHOOK_SECRET | Tasodifiy yaratilgan kamida 32 belgili sirli qator; faqat A-Z, a-z, 0-9, _ va - ishlating |
| SUPPORT_DB_PATH | /var/data/ali_kuryer_support.db (doimiy disk ulangan bo‘lsa) |

Bo‘limlar uchun ixtiyoriy alohida guruhlar:
SUPPORT_ORDERS_CHAT_ID, SUPPORT_PAYMENT_CHAT_ID,
SUPPORT_COURIER_CHAT_ID, SUPPORT_RESTAURANT_CHAT_ID,
SUPPORT_COMPLAINT_CHAT_ID, SUPPORT_GENERAL_CHAT_ID.

SUPPORT_PUBLIC_URL — sayt ochiladigan HTTPS backend manzili, GitHub Pages statik manzili emas.
Mavjud render.yaml fayli /var/data ga disk ulanishini nazarda tutadi;
haqiqiy Render xizmatida disk ulanganini tekshiring. Disksiz SQLite qayta deployda saqlanmasligi mumkin.

## Ishga tushirish

1. Taklif qilingan kod o‘zgarishlarini GitHubdagi asosiy main tarmog‘iga qo‘shing.
2. Render web service yangi kodni deploy qilsin.
3. Environment kalitlari joylanganidan keyin servis restart qilinsin.
4. Ishga tushishda dastur Telegram setWebhook sozlamasini avtomatik o‘rnatadi.
5. Botga /start yuborib sinab ko‘ring.

Muhim: yangi SUPPORT_BOT_TOKEN ni alohida yarating.
Bitta tokenni bir vaqtda Telegram polling va webhook bilan ishlatmang.

## Operator uchun sinov

1. Mijoz botga /start yozadi.
2. 📦 Buyurtma bo‘yicha tugmasini bosadi.
3. Savolini yozadi. Guruhga № raqamli murojaat va mijoz xabari tushadi.
4. Operator guruhdagi bot xabariga Reply qilib javob yozadi.
5. Javob mijozga boradi.
6. Operator kelgan bot xabariga Reply -> /close yuborib murojaatni yopadi.

Test kodi: python -m unittest discover -s tests -p test_support_bot.py -v

## Chegaralar

Hozirgi versiya tayyor FAQ javoblarini beradi, lekin AI yordamida erkin matnni tushunmaydi.
Buyurtmani bazadan avtomatik qidirish, to‘lov, pul qaytarish va SMS funksiyalari hali ulanmagan.
