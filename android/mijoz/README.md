# Ali Kuryer — Mijoz (Android)

Bu faqat **mijoz** uchun Android Studio loyihasi. Oshxona, kuryer va admin ilovalari bu papkaga kirmaydi.

- Ilova nomi: **Ali Kuryer**
- Package ID: `uz.alikuryer.customer`
- Kotlin + Jetpack Compose
- API: `https://ali-kuryer.onrender.com`

## Android Studio

1. GitHub reposini yuklab oling yoki clone qiling.
2. Android Studio → Open → **android/mijoz** papkasini tanlang.
3. Gradle sync qiling, emulator yoki Android telefonda Run bosing.
4. Internet ruxsati talab etiladi.

## Hozirgi imkoniyatlar

- Restoranlar va menyuni haqiqiy Ali Kuryer API dan olish.
- Qidiruv, taom tanlash, savatcha va manzil formasi.
- Mijoz hisobini yaratish va telefon/parol orqali kirish.
- Operator Telegram kanaliga murojaat.

**Muhim:** Hozir serverning `/api/orders` endpointi buyurtma qabul qilmaydi (faqat `/api/orders/status` ishlaydi). Android ilova haqiqiy buyurtma yuborilgan deb noto‘g‘ri ko‘rsatmaydi. Serverda buyurtma qabul qilish API tugatilgach integratsiya qilinadi.

Bu papkani root sayt/server kodini buzmasdan yuritish mumkin.
