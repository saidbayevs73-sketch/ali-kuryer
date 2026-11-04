# Ali Kuryer — dastlabki texnik audit

Sana: 2026-11-05
Audit turi: faqat o'qish (read-only) statik kod ko'rigi
Asosiy branch: main (o'zgartirilmagan)
Audit branch: ai-orchestrator/setup

## Muhim himoya qoidasi
Ushbu audit davomida Android/Web UI, dizayn, ranglar, shriftlar, rasmlar, animatsiyalar va ekranlar o'zgartirilmadi. Hech qanday mavjud ilova kodi tahrirlanmadi. Ushbu fayl faqat audit hisobotidir.

## Repository tarkibi
- Android mijoz ilovasi: Kotlin/Jetpack Compose + WebView orqali veb ilovani yuklash.
- Admin Android ilovasi: WebView ichidagi demo admin HTML.
- Website: HTML/CSS/JS, Firebase Web Auth moduli.
- Backend: Node.js/Express + PostgreSQL.
- GitHub Actions: Android mijoz va admin debug APK build workflow.

## Aniqlangan holatlar

### 1. Gemini API hali backendda ishlatilmayapti — yuqori ustuvorlik
Render Environment'da GEMINI_API_KEY o'zgaruvchisi mavjud bo'lishi mumkin, ammo ko'rilgan backend/src/server.js ichida GEMINI_API_KEY o'qilmaydi va Gemini API chaqiruvi yo'q. Demak, faqat Environment'ga kalit kiritish Gemini'ni avtomatik ulab qo'ymaydi. Integratsiya uchun alohida backend modul/endpoint, server-side kalitdan foydalanish, kirish nazorati, rate limit va xarajat cheklovlari kerak.

### 2. Buyurtma yetkazib berish narxi mijoz so'rovidan olinadi — yuqori ustuvorlik
backend/src/server.js POST /api/v1/orders ichida deliveryFee mijoz yuborgan qiymatdan olinib, jami summaga qo'shiladi. Server yetkazib berish narxini ishonchli zona/qoidalar asosida o'zi hisoblamaydi. Bu narxni noto'g'ri yuborish yoki manipulyatsiya qilish xavfini tug'diradi. Tuzatishdan oldin delivery zone va narxlash qoidalarini aniqlash kerak.

### 3. Buyurtma holatini ko'rish endpointi ommaviy — o'rta/yuqori ustuvorlik
GET /api/v1/orders/:code faqat public_code orqali buyurtma holati, jami summa va vaqtlarni qaytaradi; mijoz autentifikatsiyasi yo'q. Buyurtma kodi maxfiy va taxmin qilib bo'lmaydigan bo'lishi kerak, so'rovlar soni cheklanishi va qaytariladigan ma'lumotlar minimal bo'lishi kerak. Hozirgi kod AK- + vaqt raqamlarining oxirgi 8 belgisi asosida kod yaratadi; bu yetarlicha tasodifiy emas va to'qnashuv ehtimoli bor.

### 4. CORS sozlamasi default holatda barcha originlarga ruxsat berishi mumkin — o'rta ustuvorlik
ALLOWED_ORIGINS bo'sh bo'lsa, cors origin true bilan ishga tushadi. Production muhitida aniq ruxsat berilgan domenlar ro'yxati Environment'da ko'rsatilishi va bo'sh qiymat xavfsiz default bilan boshqarilishi kerak.

### 5. Admin API ataylab o'chirilgan — hozircha to'g'ri himoya
GET /api/v1/admin/orders 501 qaytaradi va admin autentifikatsiyasi talab qilinishini bildiradi. backend/README.md ham admin RBAC tayyor bo'lmaguncha admin endpointlar yoqilmasligini aytadi. Buni autentifikatsiya va role-based access control tayyor bo'lmaguncha yoqmaslik kerak.

### 6. Admin Android interfeysi demo holatda
admin/src/main/assets/admin.html ichida login maydonlari o'chirilgan va demo ko'rinishi haqida ogohlantirish bor. Dashboard ko'rsatkichlari haqiqiy server ma'lumotlari emas. Admin ilovasini ishlab chiqarish muhitida ishlatishdan oldin server autentifikatsiyasi, rollar va API ulanishi talab qilinadi.

### 7. Mijoz ilovasi prototip cheklovlari hujjatlashtirilgan
README.md haqiqiy SMS OTP, server integratsiyasi, GPS, kuryer dispetcherligi, push xabarnomalar va to'lov provayderlari hali ulanmaganini bildiradi. backend/README.md ham SMS OTP, customer sessions, admin RBAC, courier assignment va live GPS ishlab chiqarishga chiqarishdan oldingi ishlar ekanini qayd etadi.

### 8. Firebase Web Auth domen sozlamasi tekshirilishi kerak
website/firebase-web-auth.js Google redirect login ishlatadi va unauthorized-domain holatida ali-kuryer-web.onrender.com domenini Firebase Authorized domains ro'yxatiga qo'shishni ko'rsatadi. Firebase Console'dagi haqiqiy ruxsat etilgan domenlar, Google provider holati va Android SHA fingerprintlari alohida tekshirilishi kerak. Bu auditda Firebase Console yoki Render runtime sozlamalari ko'rilmagan.

### 9. Frontend mahsulot ma'lumotlari
website/app.js boshida namunaviy mahsulotlar frontend ichida statik ro'yxat sifatida berilgan. Haqiqiy katalog backend /api/v1/catalog bilan to'liq bog'langanmi, buni runtime sinovi bilan tekshirish kerak.

## Hozircha bajarilmagan tekshiruvlar
- GitHub Actions buildni ishga tushirish yoki APK yuklab olib qurilmada sinash.
- Render deploy logs va real Environment qiymatlarini tekshirish.
- Firebase Console provider/domain/SHA sozlamalarini tekshirish.
- Android runtime login, GPS, til almashtirish va buyurtma oqimini qurilmada sinash.
- Claude/Gemini API orqali jonli integratsiya testi.

## Tavsiya etilgan keyingi tartib
1. Mavjud dizayn uchun screenshot/reference baseline va fayl hashlarini saqlash.
2. Gemini integratsiyasini alohida backend modulida, hech qanday frontend/UI faylga tegmasdan loyihalash.
3. Backend xavfsizlik muammolarini alohida kichik o'zgarishlar bilan tuzatish.
4. Har bir o'zgarishni alohida commit va pull requestda ko'rib chiqish.
5. GitHub Actions build va sinovlar o'tmaguncha main branchga birlashtirmaslik.
6. UI o'zgarishlari talab qilinmasa, UI fayllariga umuman tegmaslik.

## Yakun
Repositoryda mijoz Android ilovasi, web frontend, admin demo, Express backend va APK build workflow mavjud. Hozirgi hujjatlarga ko'ra loyiha ayrim joylarda prototip/foundation bosqichida. Gemini API kaliti Environment'ga qo'shilgan bo'lsa ham, backend kodi uni hozircha ishlatmaydi. Ishlab chiqarishga chiqarishdan oldin backend autentifikatsiyasi, rollar, GPS, buyurtma xavfsizligi va haqiqiy katalog oqimini yakunlash kerak.

Bu hisobot statik kod ko'rigiga asoslangan; runtime ishlashiga yoki deploy muvaffaqiyatiga kafolat bermaydi.
