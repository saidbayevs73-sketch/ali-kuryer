# Ali Kuryer — Super Admin Control Center

## Qamrov
Bu funksiya FastAPI main.py serveriga qo‘shilgan. Eski ali-kuryer-1.onrender.com
backendiga yoki telefonlarga o‘rnatilgan eski APK fayllarga avtomatik ta'sir qilmaydi.

## Ochish
FastAPI server domenida /super-admin ochiladi. Kirish: admin va serverda
yaratilgan shaxsiy admin paroli. Parol yoki telefon raqami HTML faylda
saqlanmaydi. /api/auth/admin/login va /api/auth/admin/change-password
marshrutlari ishlatiladi.

## API
- GET /api/control-center/public: sayt va mobil ilovalar uchun ommaviy sozlamalar.
- GET /api/admin/control-center: role=admin tokeni bilan.
- POST /api/admin/control-center: ruxsat etilgan parametrlarni atomik saqlaydi.
- GET /api/admin/control-center/history: oxirgi 40 ta o‘zgarish.
- POST /api/auth/admin/change-password: joriy parol bilan yangi parol.

## Boshqariladigan sozlamalar
- Mijozlar: telefon/parol, username/parol, SMS OTP, Firebase telefon,
  Google va Telegram kirishlarini yoqish yoki o‘chirish.
- Kuryer va oshxona: FastAPI kirish usullarini yoqish yoki o‘chirish,
  e’lon matni va dizayn asosiy rangini saqlash.
- Mijoz sayti: aksent rang va e’lon matni live-controls.js orqali yangilanadi.
- Administrator: o‘z parolini almashtiradi; boshqa foydalanuvchilar
  parolini ko‘rish huquqi yo‘q.

## Xavfsizlik
- SMS API kalitlari, foydalanuvchi parollari va tizim kodi
  parametrlar bazasiga yozilmaydi.
- Kirishlar nafaqat tugma orqali, FastAPI serverida ham bloklanadi.
- Eski alohida ali-kuryer-1 backend kirishlari hali bunday bloklanmaydi.
- SMS ro‘yxatdan o‘tish usuli mavjud mijozlar uchun passwordless login
  emas; boshqa haqiqatan sozlangan provayder bo‘lmasa telefon/parol
  usulini o‘chirish rad etiladi.
- Vaqtinchalik Render SQLite bazasiga parametrlarni yozish cheklanadi.
- Har bir saqlangan o‘zgarish uchun audit yozuvi yaratiladi.

## Xavfsiz chiqarish tartibi
1. python -m pytest tests/test_super_admin_control_center.py va qolgan
   autentifikatsiya testlarini bajaring.
2. Production bazani zaxiralang va tiklashni tekshiring.
3. FastAPI Render servisi va doimiy DATABASE_URL mavjudligini tasdiqlang.
4. Faqat tekshiruvdan keyin pull requestni merge qiling.
5. /super-admin da kirib e’lon va ranglarni sinab ko‘ring.
6. Yangi kuryer va oshxona Android ilovalarini ommaviy konfiguratsiya
   APIga ulash kerak; eski APKlar sozlamalarni hali o‘qimaydi.
7. Ikkita backend yagona bazaga ko‘chmaguncha hamma loginlarni
   birdaniga o‘chirmang.

## Hali kiritilmagan
- APKni yangilamasdan kod va barcha ekranlarni masofadan qayta yozish.
- Buyurtmalar SMS xabarini boshqarish (faqat OTP SMS ishlatilmoqda).
- Eski kuryer va oshxona ilovalariga konfiguratsiyani ulash.
- To‘liq kontent boshqaruvi, marketing kampaniyalari,
  to‘lov tizimi va xodimlar parolini tiklash.
