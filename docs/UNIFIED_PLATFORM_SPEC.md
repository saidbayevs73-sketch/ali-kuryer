# Ali Kuryer — yagona platforma talablari

## Asosiy arxitektura
- To‘rtta alohida interfeys: mijoz, kuryer, oshxona va Super Admin.
- Bitta backend API, bitta PostgreSQL ma’lumotlar bazasi va yagona Firebase Authentication loyihasi.
- Telegram bot ham shu API orqali buyurtmalarni yaratadi va kuzatadi; bot tokeni faqat server secretida saqlanadi.
- Mavjud mijoz dizayni va `main` branch o‘zgartirilmaydi; ish `auth-role-security` branchida davom etadi.

## Rollar va kirish
- Mijoz: Google hisobi bilan kiradi.
- Kuryer va oshxona xodimi: faqat Super Admin yaratgan Firebase Email/Password hisobidan kiradi; ochiq ro‘yxatdan o‘tish yo‘q.
- Super Admin: `ADMIN_EMAILS` ro‘yxatidagi Google hisobi va server tomondagi ruxsat bilan boshqaradi.
- Har bir API so‘rovida Firebase ID token tekshiriladi; rol, faol holat va resursga egalik serverda tekshiriladi.
- Xodimga vaqtinchalik parolni xavfsiz yetkazish va birinchi kirishda almashtirish oqimi keyingi bosqichda qo‘shiladi.

## Buyurtma oqimi
1. Mijoz sayt, mijoz ilovasi yoki Telegram botdan buyurtma beradi.
2. Buyurtma umumiy bazaga yoziladi va oshxona kabinetida paydo bo‘ladi.
3. Oshxona qabul qiladi, tayyorlaydi va tayyor deb belgilaydi.
4. Kuryer yaqin buyurtmalar ro‘yxatidan o‘zi tanlab qabul qiladi. Avtomatik eng yaqin kuryerga biriktirish yo‘q.
5. Kuryer qabul qilganidan buyurtma tugaguncha mijoz xaritada uning jonli joylashuvini ko‘radi.
6. Shu faol buyurtma davomida mijoz va biriktirilgan kuryer o‘zaro jonli chat va faqat audio internet qo‘ng‘iroqdan foydalanadi.
7. Buyurtma yetkazildi yoki bekor qilindi holatiga o‘tganda server chat, audio qo‘ng‘iroq va jonli joylashuv ruxsatini darhol yopadi.

## Maxfiylik
- Buyurtma sharhlari ommaviy katalogda ko‘rsatilmaydi.
- Taom sharhini uni yozgan mijoz, Super Admin va tegishli oshxona ko‘radi.
- Kuryer bahosi va shikoyati mijoz hamda Super Admin uchun; kuryer boshqa mijozlarning ma’lumotlarini ko‘rmaydi.
- Mijoz-kuryer aloqa kanali faqat faol va aynan shu kuryer biriktirilgan buyurtmaga tegishli.
- Barcha admin amallari audit jurnaliga yoziladi.

## Oshxona
- Oshxona profili: nom, aloqa, to‘liq manzil, GPS koordinata, logo.
- Taom: nom, narx, tarkib, mavjudlik, rasm.
- Rasm telefon kamerasi orqali yangi olinishi yoki galereyadan tanlanishi mumkin. Kamera rasmi uchun ilova capture metama’lumotini yozadi; galereya rasmi alohida belgilab qo‘yiladi.
- Oshxona faqat o‘z menyusi va o‘z buyurtmalarini boshqaradi.

## Kuryer
- Ish boshlashda online holat va GPS ruxsati.
- Yaqin hududdagi ochiq buyurtmalarni ko‘rish va o‘zi tanlash.
- Ish boshlash tekshiruvida ilova ichidagi jonli kamera bilan shaxs va skuter tasviri olinadi; galereyadan fayl qabul qilinmaydi.
- Tekshiruvni Super Admin tasdiqlaydi; tekshiruv maqsadi, ko‘rish huquqi va saqlash muddati ochiq ko‘rsatiladi.
- Joylashuv faqat kuryer online va faol buyurtma shartlariga muvofiq olinadi.

## Murojaat va Telegram
- Mijoz, kuryer va oshxona sayt/ilovadan admin uchun murojaat yubora oladi.
- Admin murojaatni ko‘radi, tegishli bo‘limga biriktiradi va holatini boshqaradi.
- Telegram bot orqali buyurtma va operatorga murojaat; saytning qo‘llab-quvvatlash bo‘limida bot va yo‘riqnoma havolalari.
- Telegram botning mavjud tokeni hech qachon frontendga joylanmaydi.

## Super Admin
- Xodim hisoblari va rollarini yaratish, bloklash va faollashtirish.
- Oshxona va kuryer arizalarini ko‘rib chiqish.
- Buyurtmalar, shikoyatlar, baholar, menyular, sozlamalar va tizim holatini kuzatish.
- Sayt/ilova sozlamalarini boshqarish. Koddagi kamchiliklarni tuzatish esa versiya, test va tasdiqlangan deploy orqali bajariladi; paneldan xom kodni to‘g‘ridan-to‘g‘ri tahrirlash xavfsizlik sababli yoqilmaydi.

## Ishga tushirish tartibi
1. Firebase xodim autentifikatsiyasi va admin ruxsatini tekshirish.
2. PostgreSQL migratsiyasini backupdan keyin qo‘llash.
3. Admin/staff API va rollarni yakunlash.
4. Oshxona profili va menyu API/UI.
5. Buyurtma, kuryer tanlashi va real-time status.
6. Jonli GPS, order-scoped chat va faqat audio qo‘ng‘iroq.
7. Murojaatlar, maxfiy baholar va Telegram webhook.
8. Jonli kamera tekshiruvi, monitoring, test va bosqichli deploy.

## Hozirgi cheklov
Ushbu hujjat va migratsiya — platforma asosining birinchi bosqichi. Ular mavjud production ma’lumotlar bazasiga avtomatik qo‘llanmagan. Migratsiya qo‘llanmaguncha yangi jadvallar mavjud emas; frontend yoki API funksiyalari tayyor deb e’lon qilinmaydi.
