# Ali Kuryer — SMS tasdiqlash (OTP)

## Foydalanuvchi oqimi

1. Mijoz `+998XXXXXXXXX` telefon raqamini kiritadi.
2. "SMS-kod olish" bosadi. Server 6 xonali tasodifiy kod yaratadi.
3. Kod Eskiz SMS xizmatida tasdiqlangan jo'natuvchi nomi orqali yuboriladi.
4. Mijoz kodni kiritadi. Android'da SMS User Consent (bir martalik
   Android tizim ruxsati) orqali avtomatik to'ldirish mumkin. Butun
   SMS qutisini o'qish uchun ruxsat so'ralmaydi.
5. Kod to'g'ri bo'lsa, yangi hisob ochiladi. Mavjud hisoblar Profil
   oynasida telefon raqamini qayta tasdiqlashi mumkin.
6. Haqiqiy buyurtmalarda tasdiqlangan telefon mijoz hisobiga tegishli
   bo'lishi shart.

## Himoya

- 6 raqam, `secrets.randbelow` bilan yaratish.
- Serverda faqat HMAC-SHA256 hash va nonce saqlanadi, oddiy kod emas.
- Kod **5 daqiqa** amal qiladi, **5 noto'g'ri urinish**dan so'ng rad etiladi.
- Bir raqamga qayta SMS yuborish orasida **60 soniya**, maksimal
  **5 ta SMS / 24 soat**.
- Kodni qayta ishlatish mumkin emas. User + tasdiqlangan telefon
  bir tranzaksiyada saqlanadi.
- SMS provider konfiguratsiyasiz `/api/auth/otp/request` **503** qaytaradi;
  real yuborilmagan kodni yuborildi deb ko'rsatmaydi.
- Yangi ro'yxatdan o'tish API'si SMSsiz ishlamaydi.
- Ishlab chiqarish muhitida doimiy PostgreSQL bazasi bo'lmasa SMS
  yuborish yoqilmaydi (SQLite yo'qolib qolish xavfini bartaraf etish uchun).
- Bu mexanizm SIM raqamiga kirishni tekshiradi, shaxsning haqiqiy kimligini
  yoki raqam virtual emasligini qat'iy kafolatlamaydi.

## Render: ulash talab etiladi

`ali-kuryer` servisida **Environment** bo'limidan maxfiy qiymatlarni kiriting:

- `DATABASE_URL` — **yagona** ali-kuryer-postgres ichki PostgreSQL URL.
  Ulanish migratsiyasini va amaldagi sayt integratsiyasini avval
  tekshirib, eski ma'lumotlarga zarar bermasdan bajaring.
- `SECRET_KEY` — yetarli uzunlikdagi, maxfiy o'zgarmas JWT/HMAC kaliti.
  Ishlayotgan sessiyalarni uzib qo'ymaslik uchun mavjudini almashirmang.
- `ALI_SMS_PROVIDER=eskiz`
- `ALI_SMS_SENDER` — Eskiz akkauntingizda tasdiqlangan jo'natuvchi.
- `ESKIZ_API_TOKEN` — Eskiz tokeni **yoki** `ESKIZ_EMAIL` va
  `ESKIZ_PASSWORD` juftligi. GitHub va suhbatga maxfiy kalitlarni
  joylashtirmang.

O'zbekistonda SMS matni va jo'natuvchini provayder bilan kelishish
zarur bo'lishi mumkin. SMS uchun alohida provayder shartnomasi va
trafik to'lovlari bor. Loyihada tasdiqlanmagan provayder yoki pul
xaridini avtomatik amalga oshirmang.

## Sinov

`python -m pytest -q tests/test_sms_otp.py` testlari haqiqiy SMS
yubormaydi: test transporti orqali kodni tekshiradi. Ishlab chiqarishda
bir dona haqiqiy test-raqam bilan SMS yetkazilishini oxirida tekshiring.

`Android Ali Kuryer 4 APK` ish oqimi `mijoz` flavor uchun APK hosil
qiladi. Ilova yangi kodni kiritish va SMS User Consent bilan to'ldirish
funksiyalarini taklif qiladi. SMS yetkazilishi faqat provayder
sozlangandan keyin ishlaydi.
