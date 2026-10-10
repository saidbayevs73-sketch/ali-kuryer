# ALI KURYER — administratorni tiklash va xavfsiz chiqarish

**Holat:** sinov hujjati. Jonli saytdan bazani o‘chirmaslik va hech qanday parolni GitHubga yozmaslik kerak.

## Hozirgi ikki server

| Render xizmati | Server vazifasi | Kirish usuli |
| --- | --- | --- |
| ali-kuryer | FastAPI, Android Admin va yangi veb-panel API | login admin, maxfiy DB password hash |
| ali-kuryer-1 | Eski buyurtma serveri va eski web-panellar | Render ADMIN_USER / ADMIN_PASSWORD |
| ali-kuryer-postgres | Mavjud PostgreSQL bazasi | qaysi APIga ulanganligi alohida tasdiqlanadi |

## Asosiy muammo

Agar FastAPI `DATABASE_URL` Render vaqtinchalik SQLite fayliga qarasa, deploy/restartdan so‘ng admin hisob qayta yaratilishi mumkin. Shu sabab parol o‘zgarganidek ko‘rinib, keyin ishlamay qoladi.

Yangi V2 tarmog‘ida production uchun quyidagilar kiritilgan:
- PostgreSQLsiz adminni qayta yaratish, parol o‘zgartirish va reset qilishga ruxsat yo‘q.
- `SECRET_KEY` kamida 32 bayt bo‘lmasa, server JWT token bermaydi.
- Admin loginiga 5 daqiqada 8 noto‘g‘ri urinishdan keyin vaqtinchalik limit qo‘yilgan. Bu jarayon hozir bitta server jarayonida ishlaydi; bir nechta server bo‘lsa markaziy limit talab etiladi.
- `GET /api/health` — faqat web liveness. `GET /api/ready` — baza va token sozlamasi tayyorligini tekshiradi, maxfiy qiymatlarni chiqarmaydi.
- `python scripts/check_admin_readiness.py` — Render ichida bajariladigan faqat o‘qish diagnostikasi; parol, telefon, DB URL va reset ID qiymatlarini chiqarmaydi.
- Yagona markaziy admin bilan eski sayt loginini tekshirish sinov kodi mavjud, ammo faollashtirilmagan.

## Ishga chiqarish tartibi

1. **Zaxira:** Render `ali-kuryer-1` xizmatida `/var/data` doimiy disk bor. SQLite buyurtmalar, suratlar va foydalanuvchilar bilan birga ishonchli backup oling va alohida muhitda restore sinab ko‘ring. Eski fayllarni o‘chirmang.
2. **Baza:** Renderning `ali-kuryer-postgres` bazasi mavjud. Ammo ma’lumotlar qayerda ekanini tekshirmasdan `DATABASE_URL`ni almashtirmang: eski foydalanuvchilar va buyurtmalar ko‘rinmay qolishi mumkin. Legacy SQLite dan PostgreSQLga migratsiya uchun oldindan mavjud `scripts/migrate_legacy_to_postgres.py` opt-in mexanizmi bor; avval dry-run va backup kerak.
3. **Read-only tekshiruv:** haqiqiy FastAPI servisining Render Shell terminalida `python scripts/check_admin_readiness.py` bajaring. Natijaning faqat boolean/holat qismi bilan ishlang.
4. **Kalitlar:** `SECRET_KEY` tasodifiy, maxfiy va yetarlicha uzun bo‘lsin; `ADMIN_PHONE` haqiqiy +998 raqamiga mos kelsin; `ALI_ADMIN_BOOTSTRAP_ENABLED=1` faqat tasdiqlangan adminni yaratish/tiklash maqsadida.
5. **Reset:** doimiy baza va admin aniqlangach, `ALI_ADMIN_RESET_REQUEST_ID` ga 20–128 belgili har safar **yangi** noyob ID, `ALI_ADMIN_RESET_PASSWORD` ga kamida 14 belgili kuchli parolni **Render private Environment** orqali o‘rnating. Katta-kichik harf, raqam va maxsus belgi talab etiladi. GitHubga yoki ommaviy chatga yozmang.
6. **Reset tasdig‘i:** Adminning one-time reset muvaffaqiyati Render logida tekshirilsin; `python scripts/check_admin_readiness.py` natijasida `reset_request_already_applied` true bo‘lishi kutiladi. Android admin va veb-adminda yangi parol bilan sinab ko‘ring.
7. **Sirlarni tozalash:** tiklash yakunlangach maxfiy Render `ALI_ADMIN_RESET_PASSWORD` va vaqtinchalik request ID ni olib tashlang. Ikkinchi reset uchun eski ID qayta ishlamaydi.
8. **Eski sayt bilan birlashtirish:** sinovda markaziy login, eski parol rad etilishi va eski sessiyalarning bekor qilinishi tasdiqlangandan keyingina legacy servisda `ALI_LEGACY_ADMIN_AUTH_MODE=central` rejimi yoqilishi mumkin. API vaqtincha ishlamasa, markaziy rejim avvalgi parolga fallback qilmaydi.
9. **Chiqarish:** CI + Android + staging + rol huquqlari + real buyurtma oqimi tekshirilsa va tiklash rejasi tayyor bo‘lsagina PR #23 asosiy branchga o‘tkaziladi.

## Xavfsiz diagnostika natijasini qanday talqin qilish kerak?

- `database_type=sqlite`: production admin parolini tiklash mumkin emas, doimiy PostgreSQLni tekshiring.
- `database_connected=false`: baza ulanishi ishlamayapti; SQL xato tafsilotlarini ommaga chiqarmang.
- `owner_admin_active=false`: ADMIN_PHONE ga bog‘langan faol admin topilmadi; noto‘g‘ri parolni taxmin qilmang.
- `recovery_id_valid=false`: request ID shakli noto‘g‘ri yoki hali belgilanmagan.
- `recovery_password_valid=false`: parol kuchlilik talabiga javob bermaydi yoki hali belgilanmagan.
- `reset_request_already_applied=true`: shu ID bir marta ishlatilgan, qayta foydalanib bo‘lmaydi.
- `safe_for_production_admin_password_rotation=true`: doimiy saqlash va admin hisobga oid texnik shartlar bajarilgan; alohida login va backup sinovlari baribir zarur.

## Hozircha bajarilmagan

- PostgreSQL ulanishi va jonli admin paroli hali tasdiqlanmagan.
- Ikkala Render serverida yagona admin hali faollashtirilmagan.
- Buyurtmalar/tovarlar to‘liq migratsiya va restore sinovidan o‘tmagan.
- Mijoz/kuryer/oshxona ekranlarining barcha ish jarayoni hali tekshirilmagan.

**Muhim:** Oddiy `admin/admin` parolni ishlatmang; login nomi `admin` bo‘lishi mumkin, ammo maxfiy parol xavfsiz bo‘lishi shart.
