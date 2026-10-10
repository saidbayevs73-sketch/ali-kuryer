package uz.alikuryer.customer

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import coil.compose.AsyncImage
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

private fun JSONArray.objList(): List<JSONObject> =
    (0 until length()).mapNotNull { optJSONObject(it) }

private fun JSONObject.int(key: String) = optInt(key, 0)
private fun JSONObject.str(key: String) = optString(key, "").takeUnless { it == "null" }.orEmpty()

@Composable
internal fun AliStaffApp() {
    val role = BuildConfig.APP_ROLE
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var token by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    var tab by remember { mutableStateOf("home") }
    var orders by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var offers by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var restaurants by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var restaurantId by remember { mutableIntStateOf(0) }
    var menu by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var statistics by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var selectedOrder by remember { mutableIntStateOf(0) }
    var selectedCustomer by remember { mutableIntStateOf(0) }
    var chatMessages by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var threads by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var aiHistory by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var chatDraft by remember { mutableStateOf("") }
    var online by remember { mutableStateOf(false) }
    var gpsLat by remember { mutableStateOf<Double?>(null) }
    var gpsLng by remember { mutableStateOf<Double?>(null) }
    var newName by remember { mutableStateOf("") }
    var newPrice by remember { mutableStateOf("") }
    var newCategory by remember { mutableStateOf("") }
    var newDescription by remember { mutableStateOf("") }
    var staffName by remember { mutableStateOf("") }
    var staffPhone by remember { mutableStateOf("") }
    var staffPassword by remember { mutableStateOf("") }
    var staffRole by remember { mutableStateOf("courier") }
    var staffRestaurantId by remember { mutableStateOf("") }
    var pictureTarget by remember { mutableIntStateOf(0) }

    fun refresh() {
        if (token.isBlank()) return
        val saved = token
        scope.launch {
            try {
                when (tab) {
                    "home", "orders" -> {
                        orders = StaffApi.getOrders(saved).objList()
                        if (role == "courier") offers = StaffApi.offers(saved).objList()
                        if (role == "restaurant" || role == "admin") {
                            restaurants = StaffApi.restaurants(saved).objList()
                            if (restaurantId == 0 && restaurants.isNotEmpty())
                                restaurantId = restaurants.first().int("id")
                        }
                    }
                    "menu" -> if (restaurantId > 0) {
                        menu = StaffApi.manageMenu(saved, restaurantId).objList()
                        statistics = StaffApi.stats(saved, restaurantId).objList()
                    }
                    "chat" -> {
                        if (selectedOrder > 0)
                            chatMessages = StaffApi.messages(saved, selectedOrder).objList()
                        else if (role == "admin" && selectedCustomer > 0)
                            chatMessages = StaffApi.supportMessages(saved, selectedCustomer).objList()
                        if (role == "admin") threads = StaffApi.supportThreads(saved).objList()
                    }
                    "ai" -> if (role == "admin")
                        aiHistory = StaffApi.aiHistory(saved).objList()
                    "team" -> if (role == "admin")
                        restaurants = StaffApi.restaurants(saved).objList()
                }
                error = ""
            } catch (e: Exception) {
                error = e.message ?: "Server bilan aloqa o‘rnatilmadi"
            }
        }
    }

    LaunchedEffect(token, tab, restaurantId, selectedOrder, selectedCustomer) {
        if (token.isBlank()) return@LaunchedEffect
        while (true) {
            val t = token
            try {
                when (tab) {
                    "home", "orders" -> {
                        orders = StaffApi.getOrders(t).objList()
                        if (role == "courier") offers = StaffApi.offers(t).objList()
                        if (role in listOf("restaurant", "admin")) {
                            restaurants = StaffApi.restaurants(t).objList()
                            if (restaurantId == 0 && restaurants.isNotEmpty())
                                restaurantId = restaurants.first().int("id")
                        }
                    }
                    "menu" -> if (restaurantId != 0) {
                        menu = StaffApi.manageMenu(t, restaurantId).objList()
                        statistics = StaffApi.stats(t, restaurantId).objList()
                    }
                    "chat" -> {
                        chatMessages = if (selectedOrder > 0)
                            StaffApi.messages(t, selectedOrder).objList()
                        else if (role == "admin" && selectedCustomer > 0)
                            StaffApi.supportMessages(t, selectedCustomer).objList()
                        else emptyList()
                        if (role == "admin") threads = StaffApi.supportThreads(t).objList()
                    }
                    "ai" -> if (role == "admin") aiHistory = StaffApi.aiHistory(t).objList()
                    "team" -> if (role == "admin")
                        restaurants = StaffApi.restaurants(t).objList()
                }
            } catch (e: Exception) {
                error = e.message ?: "Serverga ulanib bo‘lmadi"
            }
            delay(10000)
        }
    }

    fun currentGps(andThen: (Double, Double) -> Unit) {
        val fine = ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        val coarse = ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        if (!fine && !coarse) { error = "Joylashuvga ruxsat bering"; return }
        try {
            val manager = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
            val provider = when {
                fine && manager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
                manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
                else -> { error = "Telefoningizda GPS'ni yoqing"; return }
            }
            if (Build.VERSION.SDK_INT >= 30) {
                manager.getCurrentLocation(provider, null, ctx.mainExecutor) { p ->
                    if (p != null) {
                        gpsLat = p.latitude; gpsLng = p.longitude
                        andThen(p.latitude, p.longitude)
                    } else error = "GPS topilmadi, qayta urinib ko‘ring"
                }
            } else {
                val p = manager.getLastKnownLocation(provider)
                if (p != null) { gpsLat = p.latitude; gpsLng = p.longitude; andThen(p.latitude, p.longitude) }
                else error = "GPS topilmadi"
            }
        } catch (_: SecurityException) { error = "GPS ruxsatini tekshiring" }
    }

    val gpsLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted.values.any { it } && token.isNotBlank()) {
            currentGps { lat, lng ->
                scope.launch {
                    try {
                        if (role == "courier") {
                            StaffApi.updatePosition(token, lat, lng, true)
                            online = true
                            error = "GPS yuborildi. Joylashuv faqat ish paytida ulashiladi."
                        } else if (role == "restaurant" && restaurantId > 0) {
                            StaffApi.setRestaurantGeo(token, restaurantId, lat, lng)
                            error = "Oshxona GPS manzili saqlandi."
                        }
                    } catch (e: Exception) { error = e.message ?: "GPS yuborilmadi" }
                }
            }
        } else error = "GPS ruxsati berilmadi"
    }
    val photoPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri != null && pictureTarget > 0 && token.isNotBlank() && restaurantId > 0) {
            scope.launch {
                try {
                    val mime = ctx.contentResolver.getType(uri).orEmpty()
                    if (mime !in listOf("image/jpeg", "image/png", "image/webp"))
                        throw IllegalArgumentException("JPG, PNG yoki WebP rasm tanlang")
                    val stream = ctx.contentResolver.openInputStream(uri)
                        ?: throw IllegalStateException("Fayl ochilmadi")
                    val bytes = stream.use { it.readNBytes(2_000_001) }
                    StaffApi.uploadPhoto(token, restaurantId, pictureTarget, bytes, mime)
                    error = "Taom rasmi saqlandi"
                    menu = StaffApi.manageMenu(token, restaurantId).objList()
                } catch (e: Exception) { error = e.message ?: "Rasm yuklanmadi" }
            }
        }
    }

    if (token.isBlank()) {
        StaffLogin(
            role = role, phone = phone, password = password,
            busy = busy, error = error,
            onPhone = { phone = it }, onPassword = { password = it },
            onLogin = {
                scope.launch {
                    busy = true; error = ""
                    try {
                        token = StaffApi.login(phone.trim(), password, role)
                        password = ""; tab = "home"
                    } catch (e: Exception) { error = e.message ?: "Kirishda xatolik" }
                    finally { busy = false }
                }
            }
        )
        return
    }

    val tabs = when (role) {
        "courier" -> listOf("home" to "Buyurtmalar", "orders" to "Mening", "chat" to "Chat")
        "restaurant" -> listOf("home" to "Buyurtmalar", "menu" to "Menyu", "chat" to "Chat")
        else -> listOf("home" to "Buyurtmalar", "chat" to "Chat", "ai" to "AI", "team" to "Xodimlar")
    }
    Scaffold(
        topBar = {
            Surface(color = AliSurface, shadowElevation = 1.dp) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        AliMark(size = 43)
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) {
                            Text("ALI KURYER", fontWeight = FontWeight.Black, fontSize = 21.sp)
                            Text(roleLabel(role).uppercase(), color = AliRed, fontSize = 11.sp,
                                fontWeight = FontWeight.Bold)
                        }
                        IconButton(onClick = {
                            token = ""; online = false; selectedOrder = 0; selectedCustomer = 0
                            orders = emptyList(); menu = emptyList(); tab = "home"
                        }) { Icon(Icons.Default.Logout, "Chiqish", tint = AliRed) }
                    }
                    if (error.isNotBlank()) {
                        Text(error, color = if (error.startsWith("GPS yuborildi") ||
                            error.contains("saqlandi")) AliMuted else AliRed,
                            fontSize = 12.sp, modifier = Modifier.padding(top = 6.dp))
                    }
                }
            }
        },
        bottomBar = {
            NavigationBar(containerColor = AliSurface) {
                tabs.forEach { (key, label) ->
                    NavigationBarItem(selected = tab == key, onClick = {
                        tab = key
                        if (key != "chat") { selectedOrder = 0; selectedCustomer = 0 }
                    }, icon = {
                        Icon(when (key) {
                            "menu" -> Icons.Default.RestaurantMenu
                            "chat" -> Icons.Default.ChatBubbleOutline
                            "ai" -> Icons.Default.SmartToy
                            "team" -> Icons.Default.Groups
                            "orders" -> Icons.Default.DeliveryDining
                            else -> Icons.Default.Dashboard
                        }, null)
                    }, label = { Text(label, fontSize = 11.sp) })
                }
            }
        },
        containerColor = AliCanvas
    ) { insets ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(insets),
            contentPadding = PaddingValues(15.dp),
            verticalArrangement = Arrangement.spacedBy(13.dp)
        ) {
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        when (tab) {
                            "menu" -> "Taomlar boshqaruvi"
                            "chat" -> "Xabarlar va suhbatlar"
                            "ai" -> "Muhammadali AI nazorati"
                            "team" -> "Xodimlar va hamkorlar"
                            else -> if (role == "courier") "Kuryer buyurtmalari"
                            else "Buyurtmalar"
                        },
                        fontSize = 23.sp, fontWeight = FontWeight.ExtraBold,
                        modifier = Modifier.weight(1f)
                    )
                    TextButton(onClick = { refresh() }) { Text("Yangilash", color = AliRed) }
                }
            }
            if (tab == "home" || tab == "orders") {
                if (role == "courier" && tab == "home") {
                    item {
                        StaffCard {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.MyLocation, null, tint = AliRed)
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(if (online) "Ish rejimi: ONLAYN"
                                         else "Ish rejimi: OFLAYN", fontWeight = FontWeight.Bold)
                                    Text("Joylashuv faqat ishga chiqqaningizda yuboriladi",
                                        fontSize = 11.sp, color = AliMuted)
                                }
                            }
                            Spacer(Modifier.height(10.dp))
                            Button(onClick = {
                                if (!online) gpsLauncher.launch(arrayOf(
                                    Manifest.permission.ACCESS_FINE_LOCATION,
                                    Manifest.permission.ACCESS_COARSE_LOCATION))
                                else scope.launch {
                                    try {
                                        StaffApi.updatePosition(token, gpsLat ?: 0.0, gpsLng ?: 0.0, false)
                                        online = false
                                        error = "Siz oflaynsiz"
                                    } catch (e: Exception) { error = e.message.orEmpty() }
                                }
                            }, colors = ButtonDefaults.buttonColors(containerColor = AliRed)) {
                                Text(if (online) "Ishni tugatish" else "Ishni boshlash va GPS ulash")
                            }
                            if (online) Text("📍 Joylashuvni yangilash uchun ish rejimini qayta bosing. " +
                                "Bu versiyada fon rejimida GPS uzatilmaydi.",
                                fontSize = 11.sp, color = AliMuted)
                        }
                    }
                    item { AliSectionTitle("Eng yaqin buyurtmalar", "Oshxonaga masofa bo‘yicha") }
                    if (offers.isEmpty()) item { Text("Yaqin buyurtma yo‘q. GPS va ish rejimini tekshiring.", color = AliMuted) }
                    items(offers, key = { "offer"+it.optJSONObject("order")?.int("id") }) { offer ->
                        val order = offer.optJSONObject("order") ?: JSONObject()
                        StaffOrderCard(order, "Masofa: ${offer.optDouble("distance_km")} km") {
                            StaffAction("Qabul qilish", enabled = online) {
                                scope.launch { try {
                                    StaffApi.accept(token, order.int("id")); refresh()
                                } catch (e: Exception) { error = e.message.orEmpty() } }
                            }
                        }
                    }
                }
                if (role == "admin") item {
                    StaffCard {
                        Text("Jami buyurtmalar: ${orders.size}", fontWeight = FontWeight.ExtraBold)
                        Text("Buyurtma holati va operator chatlarini shu ilovadan boshqaring.",
                            fontSize = 12.sp, color = AliMuted)
                    }
                }
                if (role == "restaurant" && restaurantId == 0) item {
                    Text("Hisobingizga biriktirilgan oshxona topilmadi.", color = AliRed)
                }
                item { AliSectionTitle(if (role == "courier" && tab == "home")
                    "Menga biriktirilgan" else "Buyurtmalar", "${orders.size} ta qayd") }
                if (orders.isEmpty()) item { Text("Hozircha buyurtmalar mavjud emas.", color = AliMuted) }
                items(orders, key = { "order"+it.int("id") }) { order ->
                    StaffOrderCard(order) {
                        val status = order.str("status")
                        val next = when {
                            role == "restaurant" && status == "pending" -> "preparing" to "Tayyorlanmoqda"
                            role == "restaurant" && status == "preparing" -> "ready" to "Tayyor"
                            role == "courier" && status == "assigned" -> "delivering" to "Yo‘lga chiqdim"
                            role == "courier" && status == "delivering" -> "delivered" to "Yetkazildi"
                            else -> null
                        }
                        if (next != null) StaffAction(next.second) {
                            scope.launch {
                                try { StaffApi.setStatus(token, order.int("id"), next.first); refresh() }
                                catch (e: Exception) { error = e.message.orEmpty() }
                            }
                        }
                        StaffAction("Chat", secondary = true) {
                            selectedOrder = order.int("id"); selectedCustomer = 0; tab = "chat"
                        }
                        val courier = order.optJSONObject("courier")
                        if (courier != null) {
                            val number = courier.str("phone")
                            if (number.isNotBlank()) StaffAction("Kuryerga qo‘ng‘iroq", secondary = true) {
                                ctx.startActivity(Intent(Intent.ACTION_DIAL,
                                    Uri.parse("tel:${Uri.encode(number)}")))
                            }
                        }
                        if (role == "courier") {
                            StaffAction("Manzilga yo‘l", secondary = true) {
                                val address = order.str("address")
                                ctx.startActivity(Intent(Intent.ACTION_VIEW,
                                    Uri.parse("geo:0,0?q=${Uri.encode(address)}")))
                            }
                        }
                    }
                }
            }
            if (tab == "menu" && role == "restaurant") {
                item {
                    StaffCard {
                        Text("Oshxona", fontWeight = FontWeight.Bold)
                        restaurants.forEach { rest ->
                            FilterChip(
                                selected = restaurantId == rest.int("id"),
                                onClick = { restaurantId = rest.int("id"); menu = emptyList() },
                                label = { Text(rest.str("name")) },
                                modifier = Modifier.padding(end = 4.dp)
                            )
                        }
                        Spacer(Modifier.height(6.dp))
                        StaffAction("Oshxona GPS manzilini belgilash") {
                            gpsLauncher.launch(arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION))
                        }
                    }
                }
                item {
                    StaffCard {
                        Text("Yangi taom", fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                        StaffField("Taom nomi", newName) { newName = it }
                        StaffField("Narxi (so‘m)", newPrice, keyboard = KeyboardType.Decimal) { newPrice = it }
                        StaffField("Kategoriya", newCategory) { newCategory = it }
                        StaffField("Taom tavsifi", newDescription) { newDescription = it }
                        StaffAction("Taomni qo‘shish", enabled = restaurantId > 0 &&
                            newName.trim().length >= 2 && newPrice.toDoubleOrNull()?.let { it > 0 } == true) {
                            scope.launch {
                                try {
                                    val id = StaffApi.addFood(token, restaurantId, newName,
                                        newPrice.toDouble(), newCategory, newDescription)
                                    newName = ""; newPrice = ""; newCategory = ""; newDescription = ""
                                    menu = StaffApi.manageMenu(token, restaurantId).objList()
                                    error = "Taom №$id saqlandi. Fotosuratini quyidagi menyudan qo‘shing."
                                } catch (e: Exception) { error = e.message.orEmpty() }
                            }
                        }
                    }
                }
                item { AliSectionTitle("Taomlar", "Fotosurat, narx va mavjudlik") }
                if (menu.isEmpty()) item { Text("Menyu hali bo‘sh yoki oshxona tanlanmagan.", color = AliMuted) }
                items(menu, key = { "menu"+it.int("id") }) { food ->
                    StaffCard {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            val image = food.str("image_url")
                            if (image.isNotBlank()) AsyncImage(
                                model = image, contentDescription = food.str("name"),
                                modifier = Modifier.size(74.dp))
                            Column(Modifier.weight(1f).padding(start = 8.dp)) {
                                Text(food.str("name"), fontWeight = FontWeight.Bold)
                                Text(priceText(food.optDouble("price").toLong()), color = AliRed)
                                Text(if (food.optBoolean("is_available")) "Sotuvda" else "Yashirilgan",
                                    fontSize = 11.sp, color = AliMuted)
                            }
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                            StaffAction("Foto", secondary = true) {
                                pictureTarget = food.int("id")
                                photoPicker.launch("image/*")
                            }
                            StaffAction(if (food.optBoolean("is_available")) "Yashirish" else "Sotuvga") {
                                scope.launch {
                                    try {
                                        StaffApi.updateFood(token, restaurantId, food.int("id"),
                                            food.optDouble("price"), !food.optBoolean("is_available"))
                                        menu = StaffApi.manageMenu(token, restaurantId).objList()
                                    } catch (e: Exception) { error = e.message.orEmpty() }
                                }
                            }
                        }
                    }
                }
                item { AliSectionTitle("Savdo statistikasi", "Faqat yetkazilgan buyurtmalar") }
                if (statistics.isEmpty()) item { Text("Statistika ma’lumotlari hozircha yo‘q.", color = AliMuted) }
                items(statistics, key = { "stat"+it.int("menu_item_id") }) { entry ->
                    StaffCard {
                        Row {
                            Text(entry.str("name"), modifier = Modifier.weight(1f), fontWeight = FontWeight.Bold)
                            Text("${entry.int("sold_count")} ta", color = AliRed)
                        }
                    }
                }
            }
            if (tab == "chat") {
                if (role == "admin") {
                    item { AliSectionTitle("Operator chati", "Mijozlarning xabarlari") }
                    items(threads, key = { "thread"+it.int("customer_id") }) { thread ->
                        StaffCard {
                            StaffAction("Mijoz №${thread.int("customer_id")}", secondary = true) {
                                selectedCustomer = thread.int("customer_id"); selectedOrder = 0
                            }
                        }
                    }
                }
                item {
                    val title = when {
                        selectedOrder > 0 -> "Buyurtma №$selectedOrder"
                        selectedCustomer > 0 -> "Mijoz №$selectedCustomer"
                        else -> "Buyurtmani tanlang"
                    }
                    StaffCard {
                        Text(title, fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                        Text("Suhbatlar xizmat sifati uchun vakolatli admin tomonidan ko‘rilishi mumkin.",
                            fontSize = 11.sp, color = AliMuted)
                        if (selectedOrder == 0 && selectedCustomer == 0)
                            Text("Buyurtmalar bo‘limidagi «Chat» tugmasini bosing.",
                                color = AliRed, fontSize = 13.sp)
                    }
                }
                items(chatMessages, key = { "msg"+it.int("id") }) { entry ->
                    StaffCard {
                        Text(entry.str("sender_name"), fontSize = 11.sp, color = AliRed,
                            fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(4.dp))
                        Text(entry.str("body"))
                    }
                }
                if (selectedOrder > 0 || selectedCustomer > 0) item {
                    StaffCard {
                        StaffField("Xabar yozing", chatDraft) { chatDraft = it.take(1000) }
                        StaffAction("Xabarni yuborish", enabled = chatDraft.trim().isNotEmpty()) {
                            val sent = chatDraft.trim()
                            scope.launch {
                                try {
                                    if (selectedOrder > 0) {
                                        StaffApi.sendMessage(token, selectedOrder, sent)
                                        chatMessages = StaffApi.messages(token, selectedOrder).objList()
                                    } else {
                                        StaffApi.sendSupport(token, selectedCustomer, sent)
                                        chatMessages = StaffApi.supportMessages(token, selectedCustomer).objList()
                                    }
                                    chatDraft = ""
                                } catch (e: Exception) { error = e.message.orEmpty() }
                            }
                        }
                    }
                }
            }
            if (tab == "ai" && role == "admin") {
                item {
                    Text("Faqat mijoz saqlashga rozilik bergan AI suhbatlari (30 kun).",
                        color = AliMuted, fontSize = 12.sp)
                }
                if (aiHistory.isEmpty()) item { Text("Rozilik bilan saqlangan AI suhbatlari hozircha yo‘q.", color = AliMuted) }
                items(aiHistory, key = { "ai"+it.int("id") }) { entry ->
                    StaffCard {
                        Text("Mijoz №${entry.int("customer_id")}", color = AliRed, fontWeight = FontWeight.Bold)
                        Text("Savol: ${entry.str("question")}", fontSize = 13.sp)
                        Spacer(Modifier.height(5.dp))
                        Text("Javob: ${entry.str("answer")}", fontSize = 12.sp, color = AliMuted)
                    }
                }
            }
            if (tab == "team" && role == "admin") {
                item {
                    StaffCard {
                        Text("Xodim uchun yangi hisob", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold)
                        StaffField("Ism", staffName) { staffName = it }
                        StaffField("Telefon (+998...)", staffPhone, keyboard = KeyboardType.Phone) { staffPhone = it }
                        OutlinedTextField(staffPassword, { staffPassword = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Yangi maxfiy parol (12+ belgi)") },
                            visualTransformation = PasswordVisualTransformation())
                        Row {
                            listOf("courier" to "Kuryer", "restaurant" to "Oshxona").forEach { (id, label) ->
                                FilterChip(selected = staffRole == id, onClick = { staffRole = id },
                                    label = { Text(label) }, modifier = Modifier.padding(end = 8.dp))
                            }
                        }
                        if (staffRole == "restaurant") StaffField(
                            "Oshxona ID", staffRestaurantId, keyboard = KeyboardType.Number
                        ) { staffRestaurantId = it }
                        StaffAction("Hisob yaratish", enabled = staffName.isNotBlank() &&
                            staffPassword.length >= 12 && staffPhone.startsWith("+998")) {
                            scope.launch {
                                try {
                                    StaffApi.addStaff(token, staffName, staffPhone, staffPassword,
                                        staffRole, if (staffRole == "restaurant")
                                            staffRestaurantId.toIntOrNull() else null)
                                    staffName = ""; staffPhone = ""; staffPassword = ""
                                    error = "Yangi xodim hisobi yaratildi."
                                } catch (e: Exception) { error = e.message.orEmpty() }
                            }
                        }
                    }
                }
                item { AliSectionTitle("Oshxonalar", "Hamkorlik nazorati") }
                items(restaurants, key = { "rest"+it.int("id") }) { rest ->
                    StaffCard {
                        Text(rest.str("name"), fontWeight = FontWeight.Bold)
                        Text(rest.str("address"), color = AliMuted, fontSize = 12.sp)
                        Text(if (rest.optBoolean("is_approved")) "Tasdiqlangan" else "Tasdiq kutilmoqda",
                            color = AliRed, fontSize = 12.sp)
                        StaffAction(if (rest.optBoolean("is_approved")) "Tasdiqni bekor qilish"
                        else "Tasdiqlash") {
                            scope.launch {
                                try {
                                    StaffApi.approval(token, rest.int("id"), !rest.optBoolean("is_approved"))
                                    restaurants = StaffApi.restaurants(token).objList()
                                } catch (e: Exception) { error = e.message.orEmpty() }
                            }
                        }
                    }
                }
            }
            item {
                Spacer(Modifier.height(14.dp))
                Text("Ali Kuryer • ${roleLabel(role)} • 1.4.0",
                    color = AliMuted, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun StaffLogin(role: String, phone: String, password: String,
                       busy: Boolean, error: String, onPhone: (String) -> Unit,
                       onPassword: (String) -> Unit, onLogin: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(25.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        AliMark(size = 117)
        Spacer(Modifier.height(18.dp))
        Text("ALI KURYER", fontWeight = FontWeight.Black, fontSize = 28.sp)
        Text("${roleLabel(role).uppercase()} ILOVASI",
            color = AliRed, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        Spacer(Modifier.height(25.dp))
        StaffCard {
            Text("Hisobga kirish", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold)
            Text("Faqat tasdiqlangan ${roleLabel(role).lowercase()} hisobi uchun.",
                fontSize = 12.sp, color = AliMuted)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(phone, onPhone, modifier = Modifier.fillMaxWidth(),
                label = { Text("Telefon +998XXXXXXXXX") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                singleLine = true)
            OutlinedTextField(password, onPassword, modifier = Modifier.fillMaxWidth(),
                label = { Text("Parol") },
                visualTransformation = PasswordVisualTransformation(), singleLine = true)
            if (error.isNotBlank()) Text(error, color = AliRed, fontSize = 12.sp)
            Button(onClick = onLogin, enabled = !busy && phone.isNotBlank() && password.isNotBlank(),
                modifier = Modifier.fillMaxWidth().height(54.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AliRed),
                shape = RoundedCornerShape(13.dp)) {
                Text(if (busy) "Tekshirilmoqda..." else "Kirish",
                    fontWeight = FontWeight.ExtraBold)
            }
        }
        Spacer(Modifier.height(18.dp))
        Text("Xavfsiz kirish • Har bir rol uchun alohida ruxsat",
            color = AliMuted, fontSize = 12.sp)
    }
}

@Composable
private fun StaffCard(content: @Composable ColumnScope.() -> Unit) {
    Surface(color = AliSurface, shape = RoundedCornerShape(18.dp),
        border = BorderStroke(1.dp, AliBorder)) {
        Column(modifier = Modifier.fillMaxWidth().padding(15.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp), content = content)
    }
}

@Composable
private fun StaffField(label: String, value: String,
                       keyboard: KeyboardType = KeyboardType.Text, onChange: (String) -> Unit) {
    OutlinedTextField(value, onChange, modifier = Modifier.fillMaxWidth(),
        label = { Text(label) }, keyboardOptions = KeyboardOptions(keyboardType = keyboard))
}

@Composable
private fun StaffAction(text: String, secondary: Boolean = false,
                        enabled: Boolean = true, onClick: () -> Unit) {
    if (secondary) OutlinedButton(onClick = onClick, enabled = enabled,
        shape = RoundedCornerShape(12.dp)) { Text(text, color = AliRed) }
    else Button(onClick = onClick, enabled = enabled,
        colors = ButtonDefaults.buttonColors(containerColor = AliRed),
        shape = RoundedCornerShape(12.dp)) { Text(text) }
}

@Composable
private fun StaffOrderCard(order: JSONObject, subtitle: String = "",
                           actions: @Composable ColumnScope.() -> Unit) {
    StaffCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Buyurtma №${order.int("id")}", fontWeight = FontWeight.ExtraBold,
                modifier = Modifier.weight(1f))
            Text(order.str("status"), color = AliRed, fontSize = 12.sp)
        }
        if (subtitle.isNotBlank()) Text(subtitle, fontSize = 12.sp, color = AliRed)
        Text(order.str("address"), fontSize = 13.sp, color = AliMuted)
        Text(priceText(order.optDouble("total", 0.0).toLong()),
            fontWeight = FontWeight.Bold)
        val products = order.optJSONArray("items")
        products?.objList()?.forEach { item ->
            Text("${item.str("name")} × ${item.int("quantity")}",
                color = AliMuted, fontSize = 12.sp)
        }
        actions()
    }
}
