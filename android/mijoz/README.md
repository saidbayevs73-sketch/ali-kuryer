# Ali Kuryer — Android mijoz ilovasi (qizil dizayn)

**Android Studio loyiha papkasi:** `android/mijoz`
**Mijoz paketi:** `uz.alikuryer.customer`
**Texnologiya:** Kotlin + Jetpack Compose

## Yangi kirish tartibi

1. Mijoz ilovasida **Google orqali kirish** yoki **Telegram orqali kirish** ni tanlaydi.
2. Google: haqiqiy Google ID token serverdagi `POST /api/auth/google` bilan tekshiriladi.
3. Telegram: serverdagi OIDC + PKCE orqali brauzerda tasdiqlanadi va ilovaga xavfsiz bir martalik ticket qaytariladi.
4. Hisob ochilgach **ism, familiya va +998 telefon raqami** kiritiladi; `PUT /api/customer/account/profile` da saqlanadi.
5. **SMS tasdiqlash kodi, SMS login va parol bilan kirish mijoz interfeysidan olib tashlangan.**
6. Telefon faqat yetkazib berish uchun aloqa ma'lumoti. Uning egasi tasdiqlangan deb ko'rsatilmaydi.
7. Tasdiqlanmagan aloqa raqami bilan naqd buyurtmaga cheklov qo'llanadi; doimiy PostgreSQL va `ALI_COMMERCE_CUTOVER_ENABLED=1` shartlari saqlanadi.

## Ishga tushirish

1. Android Studio > Open > `android/mijoz` katalogini tanlang.
2. Google Cloud Console da **Web application OAuth Client ID** yarating. Server Render `GOOGLE_CLIENT_ID` va Android `GOOGLE_WEB_CLIENT_ID` **aynan bir xil Web Client ID** bo'lishi kerak. Androiddagi ilova paketi va SHA-1 imzosini Google Cloud loyihasiga qo'shing (Android OAuth client).
3. **Mahalliy** `~/.gradle/gradle.properties` ga shuni kiriting (o'zingizning qiymatingiz bilan):
   `GOOGLE_WEB_CLIENT_ID=YOUR_WEB_OAUTH_CLIENT_ID.apps.googleusercontent.com`
4. Render serverda `GOOGLE_CLIENT_ID` ni sozlang va Google API hisobning ID tokenini tekshirayotganiga ishonch hosil qiling.
5. Telegram server uchun `TELEGRAM_LOGIN_CLIENT_ID`, `TELEGRAM_LOGIN_CLIENT_SECRET` va `TELEGRAM_LOGIN_ENABLED=1` ni sozlang. Telegram OIDC callback serverda oldindan ro'yxatdan o'tgan bo'lishi kerak.
6. Gradle Sync, so'ng `mijozDebug` build variantini tanlab Run bosing.
7. Google va Telegram avtorizatsiyasi, yangi hisob formasi, qayta kirish, kiritilgan telefondan buyurtma berish va cheklovlarni **real Android qurilmasida sinang**.

**Muhim:** bu branch hali ishlab chiqarishga chiqarilmagan. Google/Telegram provider kalitlari va tasdiqlash jarayonlari sozlanmaguncha login tugmalari haqiqiy ishlaydi deb hisoblamang. Hech qanday provider maxfiy kalitini Android dasturiga yoki GitHubga qo'ymang. OTP backend endpointlari tarixiy moslik uchun saqlangan, faqat mijoz ilovasida ko'rsatilmaydi. Androidda telefon kiritilishi SIM egasini tekshirmaydi.

## Mustaqil ilovalar

Loyihadagi product flavorlar: `mijoz`, `kuryer`, `oshxona`, `admin`. Mijoz ilovasida boshqa panellarga kirish tugmalari ko'rsatilmaydi. Admin huquqlari serverda tekshiriladi.
