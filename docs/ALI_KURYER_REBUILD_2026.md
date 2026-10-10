# Ali Kuryer — 2026-10-11 tekshiruv va qayta qurish rejasi

## Asosiy qoida
Ishlayotgan saytni, bazani yoki buyurtmalarni **zaxirasiz o‘chirmang**. Bu tarmoq sinov uchun. Asosiy production sayti hozircha o‘zgarmaydi.

## Aniqlangan arxitektura
| Xizmat | Dastur | Tekshirish kerak |
| --- | --- | --- |
| ali-kuryer | FastAPI / main.py, Render free | Admin va buyurtmalar doimiy PostgreSQL bazada saqlanadimi? |
| ali-kuryer-1 | Legacy / ali_kuryer.py, 1 GB doimiy disk | Eski buyurtmalarni saqlash va alohida admin kirishi |
| ali-kuryer-postgres | Render PostgreSQL mavjud | Qaysi xizmat ulangan, sxema va restore sinovi |
| Android | Alohida admin, kuryer, oshxona, mijoz flavorlari | Haqiqiy API, sessiya va kirish sinovi |
| Sayt | index.html va site-assets | Katalog, buyurtma, tracking, yordamchi |

## Eng muhim topilma
Birinchi API /api/auth/admin/login, login admin va DB password hashidan foydalanadi. Ikkinchi eski sayt /admin/login ADMIN_USER va ADMIN_PASSWORD Render sozlamalariga bog‘liq. Shuning uchun bitta parolni almashtirish ikkinchisiga ta’sir qilmaydi. Admin/admin zaif va qabul qilinmasligi kerak.

## Ushbu feature branch
1. Yangi mobilga mos Super Admin web konsol: app/templates/admin-console-v2.html.
2. /owner-console yashirin kirish nuqtasi: ENABLE_ADMIN_CONSOLE=1 bo‘lgandagina ishlaydi.
3. Password hash orqali login va parolni o‘zgartirish, tokenni faqat xotirada saqlash.
4. Yangi admin hisobini zaif parol bilan ochishni bloklash.
5. Eski bootstrap sirini bilmasdan egasi so‘rovi bilan bir martalik reset qilish.
6. ALI_LEGACY_ADMIN_AUTH_MODE=central bo‘lganda eski web-admindagi login yangi API orqali tasdiqlanadi. Sozlama faqat asosiy APIning bazasi saqlanishi tekshirilgandan va staging sinovidan keyin yoqilsin; aks holda eski login alohida qoladi.
7. Testlar: 404 default, no-store, zaif parol rad etilishi, resetning takroran ishlamasligi va markaziy admin roli tekshiruvi.
8. Android versiyasi 1.6.2 (yangi parol talablarini foydalanuvchining o‘zida tekshirish).

## Productionga chiqarishdan oldingi shartlar
- Legacy /var/data bazasini, rasm va ticketlarni, FastAPI/PG bazani zaxiralash va tiklashni alohida sinash.
- Bitta doimiy PostgreSQL asosiy identifikatorlar serveri tanlanishi va restartdan keyin admin/buyurtmalar saqlanishini tekshirish.
- Legacy adminni markaziy APIga xavfsiz ulash; alohida parolni keyin olib tashlash.
- Login admin saqlanadi; kamida 14 belgili kuchli maxfiy parol, rate-limit, parolni tiklash, audit, eski JWTlarni rad qilish.
- Mijoz, oshxona, kuryer rollari uchun alohida huquq tekshiruvlari.
- Buyurtma: katalog, serverdagi narx, joylashuv, to‘lov usuli, tasdiq, status, kuryerga taqsimlash.
- Click/Payme va boshqa to‘lovlar faqat shartnoma va webhook sinovidan so‘ng.
- Android APK sinovlari: login, xatolik, lokatsiya, buyurtma, versiya yangilanishi.
- DNS, HTTPS, real e’lon, operator/SMS/Telegram/Goggle sozlash va monitoring.
- Alohida staging server va baza, barcha testlar, rollback rejasi.

## Kengaytiriladigan modullar
Kontent/rang/e’lon boshqaruvi, oshxona/kuryer tasdiqlash, buyurtma nazorati, GPS, operator va Muhammadali yordamchisi, bonuslar (har 10 000 so‘m xaridga 1 ball), mijoz profillari, hisobot va audit.

## Muhim cheklovlar
- Ikkala server admin paroli hozircha birlashtirilmagan.
- Render PostgreSQL mavjud, lekin qaysi service unga ulanganini tasdiqlab bo‘lmadi; tashqi SQL tekshiruvi IP cheklovi sabab ishlamadi.
- Yangi konsol hali productionda yoqilmagan; haqiqiy mijoz buyurtmalariga tegilmagan.
- Hech bir loyiha va baza o‘chirilmagan.


## 2026-10-11 yangilangan sinov komponentlari
- Super Admin uchun tashqi JS/CSS ajratildi; Content Security Policy `unsafe-inline`siz ishlaydi.
- Mijoz buyurtmalari, oshxonalar, hamkorlik arizalari va operator suhbatlari uchun API orqali nazorat oynasi bor. Aloqa xatosi nol soni bilan chalkashmaydi.
- Oshxonani tasdiqlash, kuryer va oshxona xodimlarini (faqat admin) yaratish uchun APIga ulangan formalar qo‘shildi.
- Eski web admin uchun opt-in markaziy login har bir imtiyozli murojaatda FastAPI admin tokenining hali yaroqliligini tekshiradi. Parol almashsa eski token va cookie bekor bo‘ladi (faqat central mode yoqilganda).
- Production Render SQLite vaqtinchalik baza bo‘lsa admin parolini o‘zgartirish va bir martalik reset 503 qaytaradi — yolg‘on muvaffaqiyat berilmaydi.
- Server testlari va JavaScript syntax testlari GitHub Actions orqali bajariladi; Android 15 emulyatorida APK ishga tushishi avval tasdiqlangan.

**Diqqat:** Legacy xizmatning central mode yoqilishi, Render environment orqali yangi kuchli parolni sozlash, Postgresga xavfsiz migratsiya, to‘lov integratsiyasi va to‘liq staging tekshiruvi hali bajarilmagan. Bularsiz production deploy qilinmasin.
