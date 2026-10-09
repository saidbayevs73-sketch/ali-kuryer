# Ali Kuryer — sinov tarmog‘idagi yangilanish

**Holat:** feature/customer-ui-and-complaints-20261009 (sinov), asosiy `main` va jonli Render deployi o‘zgartirilmagan.

## Mijoz ilovasi
- Mijoz bosh sahifasida kuryer, oshxona va admin kirish havolalari yo‘q.
- Oshxonalar, menyu, savatcha, buyurtma shakli.
- GPS va OpenStreetMap/Leaflet xaritasi orqali yetkazish nuqtasini tanlash.
- Faqat naqd to‘lov ishlaydi. Click, Payme, UZCARD/HUMO bank to‘lovlari **hali ulanmagan**; “tez kunda” deb belgilangan.
- Yangi buyurtma uchun server joriy menyu narxlaridan umumiy summani qayta hisoblaydi.
- Buyurtma va shikoyatlarni maxfiy token bilan kuzatish, admin javobini o‘qish.

## Oshxona
- Xodim telefon + parol bilan kiradi; server roli va restoran egaligini tekshiradi.
- Taom qo‘shish, buyurtmani qabul qilish: pending → preparing → ready.
- Bir oshxona boshqasining buyurtmasini ko‘ra olmaydi.

## Kuryer
- Telefon + parol; smena boshida JPEG/PNG/WebP selfie va GPS yuboradi.
- Suratlar ommaviy `/static` papkasida emas, faqat admin uchun himoyalangan faylda saqlanadi.
- Admin smenani tasdiqlaydi, shundan keyin tayyor buyurtmalarni olish mumkin.
- Kuryerga biriktirilgan buyurtmalar, taomlar, oladigan oshxona va mijoz manzili ko‘rsatiladi.
- Buyurtma holati: ready → picked_up → on_the_way → delivered.
- GPS faqat kuryer ruxsati bilan, faol buyurtma davomida yuboriladi. Veb ilova fonga o‘tganda GPS kuzatuvi to‘xtatiladi. Android/iOS fon GPS uchun alohida native ilova va ruxsatlar kerak.

## Admin
- Birinchi administrator `ADMIN_PHONE` va `ADMIN_PASSWORD` muhit sozlamalaridan yaratiladi; parol kamida 12 UTF-8 bayt.
- Faqat admin shikoyatlarni ko‘radi va javob yuboradi.
- Admin oshxona va kuryer akkauntlarini ochadi, kuryer smenalari va maxfiy rasmlarini tasdiqlaydi, faol buyurtmalarni kuzatadi.
- Rasm va mijoz shaxsiy ma’lumotlari begona tashrifchilarga API orqali ko‘rsatilmaydi.

## Videoaloqa
- Admin tasodifiy xona kodiga ega Jitsi videoqo‘ng‘irog‘ini yaratishi mumkin.
- Xonalar faqat admin, oshxona va kuryer hisoblari uchun ro‘yxatda ko‘rinadi.
- **Ogohlantirish:** Jitsi — tashqi xizmat; havolani olgan kishi ham qo‘shila olishi mumkin. Maxfiy uchrashuvlar uchun PIN/JWT bilan boshqariladigan provayder talab etiladi.

## Serverga joylashdan oldin
1. Jonli ma’lumotlar bazasining zaxirasini oling.
2. `ali_kuryer_v2.py` bilan yangi FastAPI `main.py` **turli ma’lumotlar bazasi sxemalariga ega**. Bir DB ga nazoratsiz almashtirmang. Avval migratsiya va sinov kerak.
3. `DATABASE_URL`, uzun `SECRET_KEY`, `ADMIN_PHONE`, `ADMIN_PASSWORD` ni Render muhiti orqali sozlang. Hech qachon maxfiy qiymatlarni GitHub kodiga kiritmang.
4. `PRIVATE_UPLOAD_DIR` doimiy va ommaga ochilmagan diskni ko‘rsatishi kerak: Render’da `/var/data/ali-kuryer-private`.
5. `python -m pytest -q tests/test_startup.py tests/test_customer_workflow.py tests/test_staff_workflow.py` va `node --check app/static/app.js` sinovlari o‘tganini tekshiring.
6. Sinov muhiti bilan API, buyurtma, shikoyat, video, surat va GPS ishini telefonda qo‘lda tekshiring. Shundan keyingina tasdiq bilan `main`ga merge va deploy qiling.

**To‘lovlar:** haqiqiy Click/Payme/bank karta to‘lovlarini avtomatik yoqish mumkin emas. Rasmiy merchant shartnomasi, API kalitlari, callback imzosi va to‘lov holatini serverda tekshirish talab qilinadi. Kalitlarni suhbatga yubormang.

**Bu hujjat va kod jonli saytga nashr qilinganini bildirmaydi.**
