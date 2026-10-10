# Ali Kuryer Mijoz 1.6.3 — bir xil sayt va mobil ilova

## Yangiliklar
- Mijoz Android ilovasi hozirgi responsiv veb-saytni WebView orqali ochadi. Alohida Android UI va sayt ko‘rinishi ajralib ketmaydi. Admin, kuryer va oshxona uchun native ilovalar o‘z holicha qoladi.
- Telegram orqali kirish/tasdiqlash birinchi variant; **Telegram mavjud bo‘lmasa** pastda ism, telefon, parol va maxfiylik shartlariga rozilik orqali **SMS-kodsiz** ro‘yxatdan o‘tish formasi bor.
- SMS-kod olish/tasdiqlash elementlari mijozning veb interfeysidan olib tashlangan.
- Muhammadali chatida surat yuklash tugmasi, foto-tahlil so‘rovi va foto preview olib tashlandi; faqat yozma savol.
- Server `ALI_ASSISTANT_PHOTO_ENABLED` yoqilmagan holatda foto-chat so‘rovini rad etadi; eski testlar ixtiyoriy ruxsat bilan alohida saqlangan.

## Xavfsiz unverified telefon qaydi
- `POST /api/auth/contact/register`: SMS talab qilmaydi, lekin telefon egasi tasdiqlandi **demaydi**.
- Raqam `unverified_customer_contacts` da, foydalanuvchi `users.phone=NULL` bilan saqlanadi. Shuning uchun bu raqam haqiqiy tasdiqlangan mijozning hisobini egallash yoki ro‘yxatdan o‘tishini bloklash uchun ishlatilmaydi.
- `POST /api/auth/contact/login`: raqam + maxfiy parol bilan kirish; shunchaki raqamni bilish yetarli emas.
- `GET /api/auth/me` unverified raqamni kontakt sifatida ko‘rsatadi va `phone_verified=false` beradi.
- Xizmat `ALI_CONTACT_SIGNUP_ENABLED=1` **va** doimiy PostgreSQL mavjud bo‘lganda productionga chiqariladi. `SECRET_KEY` yetarlicha kuchli bo‘lishi talab qilinadi.
- SMS-OTPning eski backend endpointlari mavjud hisoblar bilan moslik uchun qolgan; mijoz ilovasi endi ularni taklif qilmaydi.
- Bitta telefon raqamini bir necha kishi aloqa uchun yozishi mumkin, shu sabab raqam tekshirilgan identifikator sifatida talqin qilinmaydi.

## Muhim foydalanish cheklovlari
- Telegram OIDC haqiqiy tasdiqlash faqat Telegram tomonidan berilgan ishonchli token va tasdiqlangan raqam bo‘lsa ishlaydi. Telegram ishlamasa, fallback hisob **telefon tasdiqlangan** hisoblanmaydi.
- Android WebView faqat birinchi tomon saytini va Telegram OAuthni o‘z ichida ochadi. Boshqa oddiy HTTPS, tel va mailto havolalari tashqi ilovaga beriladi; xavfli URL sxemalari rad etiladi.
- Saytning ko‘rinishi bilan tenglashish internet talab qiladi va onlayn katalog ishlashi xizmat holatiga bog‘liq.
- SMSsiz registratsiya telefon egasini tasdiqlamaydi: bunday aloqa ma’lumoti asosida parolni qayta tiklash yoki yuqori huquq berish mumkin emas.

## Chiqarmasdan oldin
1. Mavjud SQLite va PostgreSQLdan backup oling, jadval qo‘shilishi hamda restore sinovi qiling.
2. Asosiy FastAPI servisini doimiy PostgreSQLga xavfsiz ulang, mavjud hisob va buyurtmalarni saqlang.
3. `ALI_CONTACT_SIGNUP_ENABLED=1` ni faqat tayyor production bazada yoqing.
4. Ikkala kirish: Telegram ishlayotgan holat va Telegram ishlamayotgan fallbackni Android hamda brauzerda sinang.
5. Joylashuv, buyurtma, mijoz profilidagi raqam, operator chat va mavjud loginlarga regressiya testlarini bajaring.
6. Android 1.6.3 APKni emulyator va real telefonda tekshiring; keyin production saytda kodni chiqarish.

**Hozirgi holat:** GitHub draft PR #23 ichidagi sinov kodlari. Jonli sayt / Render muhitidagi foydalanuvchi hisoblariga tegilmadi.
