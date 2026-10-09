# Ali Kuryer — mijoz sayti uchun tayyorlash
## Maqsad
Ommaviy sayt va mijoz ilovasi: oshxona/taom tanlash, savat, ism/telefon/manzil, xaritada nuqtani tasdiqlash, naqd buyurtma va yordam botiga murojaat.
Admin, kuryer va restoran hisoblari mijoz hisobidan alohida. Ommaviy HTML panellar standart holatda 404 qaytaradi; role-based API yopilmaydi. Alohida native xodim ilovalari bu PR tarkibida yaratilmagan.

## Hozirgi xizmatlar
- index.html katalog va checkout: https://ali-kuryer-1.onrender.com — eski ali_kuryer_v2.py API.
- site-assets/customer.js hisob, ariza va yordam konfiguratsiyasi: https://ali-kuryer.onrender.com — FastAPI.
- Har ikkala URL Render xizmatlari bilan solishtirilib tasdiqlanishi kerak.
- FastAPI main branch orders router faqat status endpointiga ega; uni eski checkout serveri o‘rniga qo‘ymang.
- PR #4 alohida sinov integratsiyasi; SQLite sxema migratsiyasi talab qiladi. Bu PR bazani o‘zgartirmaydi.

## Muhit
FastAPI uchun .env.customer.example dagi nomlardan foydalaning. .env fayli avtomatik yuklanishiga tayanmang: qiymatlarni Render Environment orqali kiriting.
- ENVIRONMENT=production
- DATABASE_URL=sqlite:////var/data/ali_kuryer.db — faqat shu xizmatning mos sxemali bazasi.
- SECRET_KEY — serverda xavfsiz generatsiya qilinadi; GitHub yoki chatga yozilmaydi.
- ENABLE_STAFF_WEB_PANELS=0 — mijoz serveri. Alohida xodim serverida template va auth tayyor bo‘lgandagina 1.
- ADMIN_PHONE va ADMIN_PASSWORD — haqiqiy administrator rekvizitlari; hozirgi bootstrap amalini tekshiring. Namuna qiymat kiritilmagan.
- SUPPORT_BOT_TOKEN — Renderga avval kiritilgan yangi tokenni saqlang, chatdagi eski tokenni ishlatmang.
- SUPPORT_WEBHOOK_SECRET — mustaqil server siri.
- SUPPORT_PUBLIC_URL — FastAPI xizmatining HTTPS manzili (webhook yo‘li kod tomonidan qo‘shiladi).
- SUPPORT_OPERATORS_CHAT_ID=-1003993048206 — foydalanuvchi taqdim etgan operator guruhi.
- SUPPORT_DB_PATH=/var/data/ali_kuryer_support.db — ticketlar doimiy diskda.
- ALI_HELP_BOT_URL — haqiqiy yordamchi bot username URLi; mavjud konfiguratsiyadagi URLni BotFather bilan tekshiring.
- GOOGLE_CLIENT_ID — OAuth sozlangandan keyin; sayt domenlarini Google Console’da ruxsat eting.
- AI_API_URL, AI_API_KEY, AI_MODEL — ixtiyoriy; ulanmasa jonli AI ishlayotgani deb ko‘rsatilmaydi.
- SMS_API_URL/SMS_API_TOKEN — ixtiyoriy, faqat provider oqimi implementatsiya qilinganda.
Legacy buyurtma serveri uchun mavjud DB_PATH, ADMIN_USER/ADMIN_PASSWORD, COOKIE_SECURE=1, BOT_TOKEN va PORT sozlamalari saqlanadi.

## Yordam
Mijoz chatidagi operator tugmasi Telegram botni ochadi. Bot kategoriyalari: buyurtma, to‘lov, kuryer, restoran, shikoyat va boshqa savol. Operator guruhda xabarga Reply bilan javob beradi; /take va /close mavjud.
Sayt ichida operator bilan ikki tomonlama jonli suhbat bu PRda yo‘q; buni alohida ticket API/session va operator interfeysi bilan ishlab chiqish kerak.

## Minimal qabul tekshiruvi
1. Jonli bazalarning izchil zaxirasini oling; tiklashni izolyatsiyalangan muhitda sinang.
2. PRni stagingga chiqaring, production DBga ulanmasin; qo‘llab-quvvatlash testlari uchun Telegram chaqiruvlarini mock qiling.
3. / va katalog yuklansin. /admin, /courier, /restaurant mijoz serverida 404 qaytarsin.
4. GPSdan so‘ng xarita ochilsin. Bekor qilish checkoutga ruxsat bermasin; “Shu joyga yetkazilsin” tasdiqlasin. Sahifa qayta yuklanganda eski nuqta avtomatik tasdiqlanmasin.
5. Ism, +998 telefon, ko‘cha, uy va bitta restoran savati bilan bir naqd buyurtma stagingda saqlansin. Noto‘g‘ri ma’lumot rad etilsin; narx serverda hisoblansin.
6. Mijoz akkauntiga xodim roli bilan kirish rad etilsin.
7. Yordam botiga sinov murojaati va operator javobi bilan ikki tomonlama relayni tekshiring (test guruhida).
8. Xizmat restartidan so‘ng baza va yordam ticketlari saqlansin.
9. Click/Payme/UZCARD/HUMO ulanmagan; merchant shartnoma, callback verifikatsiya va provider sinovlarisiz yoqmang.

## Chiqarish
Staging dalillari va backup/rollback tayyor bo‘lgandan keyin PRni main bilan birlashtiring. Bunda legacy buyurtma serverini FastAPI bilan almashtirmang. Frontend domeni GitHub Pages yoki Renderdan qaysi biri orqali xizmat olayotganini aniqlab, shu hostingdagi chiqarishni tekshiring.
