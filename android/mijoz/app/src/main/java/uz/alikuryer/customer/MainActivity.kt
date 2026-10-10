package uz.alikuryer.customer

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import java.util.Locale
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val preferences = remember { getSharedPreferences("ali_kuryer_appearance", Context.MODE_PRIVATE) }
            var appearanceMode by remember {
                mutableStateOf(preferences.getString("mode", "system")
                    ?.takeIf { it in setOf("light", "dark", "system") } ?: "system")
            }
            val isDark = when (appearanceMode) {
                "light" -> false
                "dark" -> true
                else -> isSystemInDarkTheme()
            }
            val canvas = if (isDark) Color(0xFF101114) else Color(0xFFF5F5F5)
            val surfaceColor = if (isDark) Color(0xFF1B1D21) else Color.White
            val textColor = if (isDark) Color(0xFFF4F4F6) else Color(0xFF111111)
            SideEffect {
                val barColor = if (isDark) android.graphics.Color.rgb(16, 17, 20)
                               else android.graphics.Color.WHITE
                val style = if (isDark) SystemBarStyle.dark(barColor)
                            else SystemBarStyle.light(barColor, android.graphics.Color.BLACK)
                this@MainActivity.enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
            }
            CompositionLocalProvider(LocalAliDark provides isDark) {
                MaterialTheme(
                    colorScheme = if (isDark) darkColorScheme(
                        primary = AliRed, onPrimary = Color.White,
                        background = canvas, onBackground = textColor,
                        surface = surfaceColor, onSurface = textColor,
                        surfaceVariant = Color(0xFF282B30),
                        onSurfaceVariant = Color(0xFFBABCC6),
                        outline = Color(0xFF555963),
                        outlineVariant = Color(0xFF353841)
                    ) else lightColorScheme(
                        primary = AliRed, onPrimary = Color.White,
                        background = canvas, onBackground = textColor,
                        surface = surfaceColor, onSurface = textColor,
                        surfaceVariant = Color(0xFFF0F1F4),
                        onSurfaceVariant = Color(0xFF696B73),
                        outline = Color(0xFFBBBFC8),
                        outlineVariant = Color(0xFFEAEAF0)
                    )
                ) {
                    var splash by remember { mutableStateOf(true) }
                    LaunchedEffect(Unit) { delay(950); splash = false }
                    Surface(modifier = Modifier.fillMaxSize().safeDrawingPadding(),
                            color = AliCanvas) {
                        if (splash) AliSplash()
                        else if (BuildConfig.APP_ROLE == "customer")
                            AliCustomerApp(
                                appearanceMode = appearanceMode,
                                onAppearanceChange = { next ->
                                    if (next in setOf("light", "dark", "system")) {
                                        appearanceMode = next
                                        preferences.edit().putString("mode", next).apply()
                                    }
                                }
                            )
                        else AliStaffApp()
                    }
                }
            }
        }
    }
}

@Composable
private fun AliSplash() {
    Surface(color = AliSurface, modifier = Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally) {
            AliMark(size = 190)
            Spacer(Modifier.height(18.dp))
            Text("ALI KURYER", fontWeight = FontWeight.Black, fontSize = 28.sp,
                color = AliBlack, letterSpacing = 1.4.sp)
            Spacer(Modifier.height(7.dp))
            Text(if (BuildConfig.APP_ROLE == "customer") "MAZALI TAOMLAR. SIZGA YAQIN." else when (BuildConfig.APP_ROLE) { "courier" -> "KURYER BOSHQARUVI" ; "restaurant" -> "OSHXONA BOSHQARUVI" ; else -> "ADMIN BOSHQARUVI" }, color = AliRed,
                fontSize = 11.sp, letterSpacing = 1.5.sp,
                fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(30.dp))
            CircularProgressIndicator(color = AliRed, strokeWidth = 3.dp,
                modifier = Modifier.size(25.dp))
        }
    }
}

@Composable
private fun AliCustomerApp(appearanceMode: String, onAppearanceChange: (String) -> Unit) {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    var page by remember { mutableStateOf("home") }
    var restaurants by remember { mutableStateOf<List<Restaurant>>(emptyList()) }
    var foods by remember { mutableStateOf<List<Food>>(emptyList()) }
    var searchFoods by remember { mutableStateOf<List<FoodHit>>(emptyList()) }
    var searchLoaded by remember { mutableStateOf(false) }
    var selected by remember { mutableStateOf<Restaurant?>(null) }
    var pendingRestaurant by remember { mutableStateOf<Restaurant?>(null) }
    var cart by remember { mutableStateOf<Map<Int, Int>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var search by remember { mutableStateOf("") }
    var menuFilter by remember { mutableStateOf("Barchasi") }
    var address by remember { mutableStateOf("") }
    var addressTemp by remember { mutableStateOf("") }
    var customerLatitude by remember { mutableStateOf<Double?>(null) }
    var customerLongitude by remember { mutableStateOf<Double?>(null) }

    var editAddress by remember { mutableStateOf(false) }
    var session by remember { mutableStateOf<Session?>(null) }
    var fullName by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("+998") }
    var password by remember { mutableStateOf("") }
    var registerMode by remember { mutableStateOf(false) }
    var firebaseLoginMode by remember { mutableStateOf(false) }
    var phoneVerified by remember { mutableStateOf<Boolean?>(null) }

    var chatText by remember { mutableStateOf("") }
    var retainAiHistory by remember { mutableStateOf(false) }
    val chat = remember { mutableStateListOf<Pair<Boolean, String>>() }
    var privacyAccepted by remember { mutableStateOf(false) }
    var myOrders by remember { mutableStateOf<List<AliOrder>>(emptyList()) }
    var activeOrderId by remember { mutableIntStateOf(0) }
    var activeOrder by remember { mutableStateOf<AliOrder?>(null) }
    var supportMessages by remember { mutableStateOf<List<AliChatMessage>>(emptyList()) }
    var orderMessages by remember { mutableStateOf<List<AliChatMessage>>(emptyList()) }
    var conversationText by remember { mutableStateOf("") }

    LaunchedEffect(session?.token) {
        phoneVerified = null
        val currentToken = session?.token ?: return@LaunchedEffect
        try { phoneVerified = AliApi.isPhoneVerified(currentToken) }
        catch (_: Exception) { phoneVerified = null }
    }

    fun openSupport() {
        if (session == null) {
            message = "Operator chatidan foydalanish uchun Profil orqali kiring."
            page = "profile"
        } else {
            conversationText = ""
            page = "support"
        }
    }

    fun loadOrder() {
        if (activeOrderId == 0 || session == null) return
        scope.launch {
            try {
                activeOrder = AliApi.orderDetails(session!!.token, activeOrderId)
            } catch (e: Exception) {
                message = e.message ?: "Buyurtma ma’lumotlari olinmadi"
            }
        }
    }

    LaunchedEffect(page, session?.token, activeOrderId) {
        val token = session?.token ?: return@LaunchedEffect
        while (true) {
            try {
                when (page) {
                    "orders" -> myOrders = AliApi.myOrders(token)
                    "order_status" -> if (activeOrderId > 0) {
                        activeOrder = AliApi.orderDetails(token, activeOrderId)
                    }
                    "support" -> supportMessages = AliApi.supportMessages(token)
                    "order_chat" -> if (activeOrderId > 0) {
                        orderMessages = AliApi.orderMessages(token, activeOrderId)
                    }
                }
            } catch (e: Exception) {
                if (page in listOf("orders", "order_status", "support", "order_chat")) {
                    message = "Server bilan bog‘lanishda xato: " + (e.message ?: "")
                }
            }
            delay(7000)
        }
    }


    fun readGpsLocation() {
        val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val hasFine = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        if (!hasFine && !hasCoarse) {
            message = "GPS uchun telefondan ruxsat bering."
            return
        }
        try {
            val provider = when {
                hasFine && manager.isProviderEnabled(LocationManager.GPS_PROVIDER) ->
                    LocationManager.GPS_PROVIDER
                manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) ->
                    LocationManager.NETWORK_PROVIDER
                else -> {
                    message = "Telefon sozlamalaridan joylashuvni yoqing."
                    return
                }
            }
            if (Build.VERSION.SDK_INT >= 30) {
                manager.getCurrentLocation(provider, null, context.mainExecutor) { location ->
                    if (location == null) {
                        message = "GPS nuqtasi olinmadi. Manzilni qo‘lda kiriting."
                    } else {
                        customerLatitude = location.latitude
                        customerLongitude = location.longitude
                        message = "GPS nuqtasi belgilandi. Endi to‘liq ko‘cha va uy raqamini kiriting."
                    }
                }
            } else {
                val location = manager.getLastKnownLocation(provider)
                if (location == null) {
                    message = "GPS nuqtasi topilmadi. Manzilni qo‘lda kiriting."
                } else {
                    customerLatitude = location.latitude
                    customerLongitude = location.longitude
                    message = "GPS nuqtasi belgilandi."
                }
            }
        } catch (_: SecurityException) {
            message = "GPS ruxsatini tekshiring."
        } catch (_: IllegalArgumentException) {
            message = "GPS xizmati hozircha ishlamadi."
        }
    }

    val gpsPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        if (granted.values.any { it }) {
            readGpsLocation()
        } else {
            message = "Joylashuv ruxsati berilmadi. Manzilni qo‘lda kiriting."
        }
    }

    fun loadRestaurants() {
        scope.launch {
            busy = true
            try {
                restaurants = AliApi.restaurants()
                message = ""
            } catch (e: Exception) {
                message = "Oshxonalarni yuklab bo‘lmadi: " + (e.message ?: "Internetni tekshiring")
            } finally { busy = false }
        }
    }

    fun openMenu(restaurant: Restaurant, resetCart: Boolean = false) {
        if (resetCart || selected?.id != restaurant.id) cart = emptyMap()
        selected = restaurant
        foods = emptyList()
        menuFilter = "Barchasi"
        page = "menu"
        scope.launch {
            busy = true
            try {
                foods = AliApi.menu(restaurant.id)
                message = ""
            } catch (e: Exception) {
                message = "Menyu ochilmadi: " + (e.message ?: "Internetni tekshiring")
            } finally { busy = false }
        }
    }

    fun selectRestaurant(restaurant: Restaurant) {
        if (selected?.id != null && selected?.id != restaurant.id && cart.values.sum() > 0) {
            pendingRestaurant = restaurant
        } else {
            openMenu(restaurant)
        }
    }

    fun openSearch(query: String = "") {
        search = query
        page = "search"
        if (!searchLoaded) {
            searchLoaded = true
            scope.launch {
                busy = true
                val result = mutableListOf<FoodHit>()
                var failures = 0
                for (restaurant in restaurants) {
                    try {
                        AliApi.menu(restaurant.id).forEach { result.add(FoodHit(restaurant, it)) }
                    } catch (_: Exception) { failures++ }
                }
                searchFoods = result
                if (failures > 0 && result.isEmpty() && restaurants.isNotEmpty()) {
                    message = "Taom qidiruvi vaqtincha ishlamadi. Oshxonadan menyuni ko‘ring."
                    searchLoaded = false
                }
                busy = false
            }
        }
    }

    LaunchedEffect(Unit) { loadRestaurants() }

    val cartCount = cart.values.sum()
    val subtotal = foods.sumOf { it.price * (cart[it.id] ?: 0) }
    val matchingRestaurants = restaurants.filter {
        it.name.contains(search, true) || it.address.contains(search, true)
    }
    val matchingFoods = searchFoods.filter {
        it.food.name.contains(search, true) || it.food.category.contains(search, true) ||
            it.restaurant.name.contains(search, true)
    }
    val menuCategories = listOf("Barchasi") +
        foods.map { it.category.trim() }.filter { it.isNotEmpty() }.distinct().take(8)
    val visibleMenu = foods.filter { menuFilter == "Barchasi" || it.category == menuFilter }

    if (pendingRestaurant != null) {
        AlertDialog(
            onDismissRequest = { pendingRestaurant = null },
            title = { Text("Savatni almashtiramizmi?") },
            text = { Text("Bitta buyurtma faqat bitta oshxonadan bo‘lishi mumkin. Oldingi savat tozalanadi.") },
            confirmButton = {
                TextButton(onClick = {
                    val next = pendingRestaurant
                    pendingRestaurant = null
                    if (next != null) openMenu(next, resetCart = true)
                }) { Text("Almashtirish", color = AliRed) }
            },
            dismissButton = { TextButton(onClick = { pendingRestaurant = null }) { Text("Bekor qilish") } }
        )
    }

    if (editAddress) {
        AlertDialog(
            onDismissRequest = { editAddress = false },
            title = { Text("Yetkazish manzili") },
            text = {
                Column {
                    Text("Mijozga yetib borish uchun aniq manzil kiriting.",
                        fontSize = 13.sp, color = AliMuted)
                    Spacer(Modifier.height(12.dp))
                    OutlinedTextField(addressTemp, { addressTemp = it },
                        label = { Text("Shahar, ko‘cha, uy raqami") },
                        modifier = Modifier.fillMaxWidth(), minLines = 2)
                    Spacer(Modifier.height(10.dp))
                    OutlinedButton(
                        onClick = {
                            gpsPermissionLauncher.launch(arrayOf(
                                Manifest.permission.ACCESS_FINE_LOCATION,
                                Manifest.permission.ACCESS_COARSE_LOCATION
                            ))
                        },
                        shape = RoundedCornerShape(13.dp)
                    ) {
                        Icon(Icons.Default.MyLocation, null, tint = AliRed)
                        Spacer(Modifier.width(7.dp))
                        Text("GPS nuqtamni aniqlash")
                    }
                    if (customerLatitude != null && customerLongitude != null) {
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "📍 GPS: " + String.format(
                                Locale.US, "%.5f, %.5f",
                                customerLatitude!!, customerLongitude!!
                            ),
                            fontSize = 12.sp, color = AliMuted
                        )
                    }
                    Text("GPS faqat ruxsatingiz bilan olinadi va buyurtma manziliga " +
                        "biriktiriladi.", fontSize = 10.sp, color = AliMuted)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    if (addressTemp.trim().length < 5) {
                        message = "To‘liq manzil kiriting"
                    } else {
                        address = addressTemp.trim()
                        editAddress = false
                    }
                }) { Text("Saqlash", color = AliRed) }
            },
            dismissButton = {
                TextButton(onClick = { editAddress = false }) { Text("Bekor qilish") }
            }
        )
    }

    Scaffold(
        containerColor = AliCanvas,
        topBar = {
            Surface(color = Color(0xFF050505), shadowElevation = 1.dp) {
                Column(Modifier.fillMaxWidth()) {
                    Row(Modifier.fillMaxWidth().height(74.dp)
                        .padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        if (page in listOf("menu", "checkout", "chat", "support", "order_status", "order_chat")) {
                            IconButton(onClick = {
                                page = when (page) {
                                    "checkout" -> "cart"
                                    "chat" -> "home"
                                    "support" -> "profile"
                                    "order_chat" -> "order_status"
                                    "order_status" -> "orders"
                                    else -> "home"
                                }
                            }) { Icon(Icons.Default.ArrowBack, "Orqaga", tint = Color.White) }
                            Spacer(Modifier.width(4.dp))
                        }
                        AliWordmark(Modifier.weight(1f), subtitle = page == "home", darkHeader = true)
                        IconButton(onClick = { page = "profile" }) {
                            Icon(Icons.Default.AccountCircle, "Profil", tint = Color.White,
                                modifier = Modifier.size(29.dp))
                        }
                    }
                    if (page == "home") {
                        Row(Modifier.fillMaxWidth().clickable {
                            addressTemp = address
                            editAddress = true
                        }.padding(start = 18.dp, end = 18.dp, bottom = 13.dp),
                            verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.LocationOn, null, tint = AliRed,
                                modifier = Modifier.size(20.dp))
                            Spacer(Modifier.width(7.dp))
                            Column(Modifier.weight(1f)) {
                                Text("YETKAZISH MANZILI", color = Color.LightGray,
                                    fontWeight = FontWeight.Bold, fontSize = 10.sp)
                                Text(address.ifBlank { "Yetkazish manzilini kiriting" },
                                    fontSize = 14.sp, color = Color.White,
                                    fontWeight = FontWeight.Bold, maxLines = 1,
                                    overflow = TextOverflow.Ellipsis)
                            }
                            Icon(Icons.Default.KeyboardArrowDown, null, tint = AliRed)
                        }
                    }
                }
            }
        },
        bottomBar = {
            if (page !in listOf("chat", "support", "order_chat")) NavigationBar(
                containerColor = AliSurface, tonalElevation = 7.dp) {
                data class Nav(val key: String, val title: String, val icon: @Composable () -> Unit)
                val tabs = listOf(
                    Nav("home", "Asosiy") { Icon(Icons.Default.Home, null) },
                    Nav("search", "Qidiruv") { Icon(Icons.Default.Search, null) },
                    Nav("orders", "Buyurtmalar") { Icon(Icons.Default.ReceiptLong, null) },
                    Nav("cart", "Savat") {
                        BadgedBox(badge = { if (cartCount > 0) Badge { Text(cartCount.toString()) } }) {
                            Icon(Icons.Default.ShoppingBag, null)
                        }
                    },
                    Nav("profile", "Profil") { Icon(Icons.Default.Person, null) }
                )
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = page == tab.key ||
                            (tab.key == "home" && page == "menu") ||
                            (tab.key == "cart" && page == "checkout"),
                        onClick = {
                            if (tab.key == "search") openSearch()
                            else page = tab.key
                        },
                        icon = tab.icon,
                        label = { Text(tab.title, fontSize = 10.sp) },
                        alwaysShowLabel = true,
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = AliRed, selectedTextColor = AliBlack,
                            indicatorColor = Color(0xFFFFE7EA),
                            unselectedIconColor = AliMuted, unselectedTextColor = AliMuted
                        )
                    )
                }
            }
        }
    ) { inner ->
        Column(Modifier.fillMaxSize().padding(inner)) {
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth(),
                color = AliRed, trackColor = Color(0xFFFFE4E8))
            if (message.isNotBlank()) {
                Surface(color = Color(0xFFFFF3DF)) {
                    Row(Modifier.fillMaxWidth().padding(9.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        Text(message, modifier = Modifier.weight(1f),
                            color = Color(0xFF17171B), fontSize = 12.sp)
                        IconButton(onClick = { message = "" }, Modifier.size(27.dp)) {
                            Icon(Icons.Default.Close, "Yopish", modifier = Modifier.size(17.dp))
                        }
                    }
                }
            }
            when (page) {
                "home" -> LazyColumn(
                    contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 28.dp),
                    verticalArrangement = Arrangement.spacedBy(20.dp)
                ) {
                    item {
                        Surface(onClick = { openSearch() }, shape = RoundedCornerShape(17.dp),
                            color = AliSurface, border = BorderStroke(1.dp, AliBorder)) {
                            Row(Modifier.fillMaxWidth().height(62.dp)
                                .padding(horizontal = 16.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.Search, null, tint = AliRed)
                                Spacer(Modifier.width(11.dp))
                                Text("Taom yoki oshxona qidirish", color = AliMuted,
                                    fontSize = 14.sp, modifier = Modifier.weight(1f))
                                Icon(Icons.Default.Tune, null, tint = AliMuted)
                            }
                        }
                    }
                    item { AliPromoHero(onExplore = {
                        if (restaurants.isNotEmpty()) {
                            selectRestaurant(restaurants.first())
                        } else { message = "Hozircha oshxonalar mavjud emas" }
                    }) }
                    item { AliServiceHighlights() }
                    item {
                        AliSectionTitle("Nima buyurtma qilamiz?", "Sevimli taomingizni tanlang")
                        Spacer(Modifier.height(13.dp))
                        LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            items(quickCategories) { category ->
                                AliCategoryTile(category) { openSearch(category.query) }
                            }
                        }
                    }
                    item {
                        Surface(onClick = { page = "chat" },
                            color = AliSurface, shape = RoundedCornerShape(19.dp),
                            border = BorderStroke(1.dp, AliBorder)) {
                            Row(Modifier.fillMaxWidth().padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(50.dp).clip(RoundedCornerShape(15.dp))
                                    .then(Modifier),
                                    contentAlignment = Alignment.Center) {
                                    Icon(Icons.Default.AutoAwesome, null, tint = AliRed, modifier = Modifier.size(33.dp))
                                }
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) {
                                    Text("Muhammadali yordamchi",
                                        fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                    Text("Taom tanlashda yordam beradi",
                                        fontSize = 12.sp, color = AliMuted)
                                }
                                Icon(Icons.Default.ArrowForwardIos, null,
                                    tint = AliRed, modifier = Modifier.size(17.dp))
                            }
                        }
                    }
                    item {
                        Surface(
                            onClick = { openSupport() },
                            shape = RoundedCornerShape(18.dp),
                            color = AliSurface,
                            border = BorderStroke(1.dp, AliBorder)
                        ) {
                            Row(Modifier.fillMaxWidth().padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.HeadsetMic, null, tint = AliRed)
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text("Operator bilan onlayn chat",
                                        fontWeight = FontWeight.Bold, color = AliBlack)
                                    Text("Buyurtma yoki xizmat haqida savol bering",
                                        fontSize = 12.sp, color = AliMuted)
                                }
                                Icon(Icons.Default.ChevronRight, null, tint = AliRed)
                            }
                        }
                    }
                    item {
                        AliSectionTitle(
                            "Oshxonalar",
                            "Yaqin hamkor oshxonalar",
                            trailing = "Yangilash",
                            onTrailing = { loadRestaurants() }
                        )
                    }
                    if (restaurants.isEmpty()) {
                        item {
                            AliEmptyState("🍽️", "Hozircha oshxonalar yo‘q",
                                "Tasdiqlangan oshxonalar paydo bo‘lgach shu yerda ko‘rsatiladi.",
                                "Yangilash") { loadRestaurants() }
                        }
                    } else {
                        items(restaurants, key = { it.id }) { restaurant ->
                            AliRestaurantTile(restaurant) { selectRestaurant(restaurant) }
                        }
                    }
                    item { Spacer(Modifier.height(2.dp)) }
                }

                "search" -> Column(Modifier.fillMaxSize().padding(16.dp)) {
                    AliSectionTitle("Qidiruv", "Oshxona yoki taom nomini kiriting")
                    Spacer(Modifier.height(14.dp))
                    OutlinedTextField(value = search, onValueChange = { search = it },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                        placeholder = { Text("Masalan: pizza, burger, osh") },
                        leadingIcon = { Icon(Icons.Default.Search, null) },
                        trailingIcon = {
                            if (search.isNotBlank()) IconButton(onClick = { search = "" }) {
                                Icon(Icons.Default.Close, "Tozalash")
                            }
                        },
                        shape = RoundedCornerShape(16.dp))
                    Spacer(Modifier.height(12.dp))
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(11.dp)) {
                        if (matchingRestaurants.isNotEmpty()) {
                            item {
                                Text("Oshxonalar", fontWeight = FontWeight.ExtraBold,
                                    fontSize = 17.sp, color = AliBlack)
                            }
                            items(matchingRestaurants, key = { "r-${it.id}" }) { r ->
                                AliRestaurantTile(r) { selectRestaurant(r) }
                            }
                        }
                        if (search.isNotBlank() && matchingFoods.isNotEmpty()) {
                            item {
                                Spacer(Modifier.height(6.dp))
                                Text("Taomlar", fontWeight = FontWeight.ExtraBold,
                                    fontSize = 17.sp, color = AliBlack)
                            }
                            items(matchingFoods, key = { "f-${it.restaurant.id}-${it.food.id}" }) { hit ->
                                Surface(onClick = { selectRestaurant(hit.restaurant) },
                                    shape = RoundedCornerShape(17.dp),
                                    color = AliSurface, border = BorderStroke(1.dp, AliBorder)) {
                                    Row(Modifier.fillMaxWidth().padding(15.dp),
                                        verticalAlignment = Alignment.CenterVertically) {
                                        Box(Modifier.size(85.dp)
                                            .clip(RoundedCornerShape(13.dp))
                                            .background(AliCanvas),
                                            contentAlignment = Alignment.Center) {
                                            Icon(Icons.Default.Restaurant, null, tint = AliMuted)
                                            coil.compose.AsyncImage(
                                                model = hit.food.imageUrl
                                                    ?: "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=400&q=85",
                                                contentDescription = if (hit.food.imageUrl == null)
                                                    "Namunaviy taom fotosurati" else hit.food.name,
                                                modifier = Modifier.fillMaxSize(),
                                                contentScale = androidx.compose.ui.layout.ContentScale.Crop
                                            )
                                        }
                                        Spacer(Modifier.width(12.dp))
                                        Column(Modifier.weight(1f)) {
                                            Text(hit.food.name, fontWeight = FontWeight.Bold)
                                            Text(hit.restaurant.name, fontSize = 12.sp, color = AliMuted)
                                            Text(priceText(hit.food.price),
                                                color = AliRed, fontWeight = FontWeight.Bold)
                                        }
                                        Icon(Icons.Default.ArrowForwardIos, null, tint = AliRed,
                                            modifier = Modifier.size(16.dp))
                                    }
                                }
                            }
                        }
                        if (matchingRestaurants.isEmpty() &&
                            (search.isBlank() || matchingFoods.isEmpty())) {
                            item {
                                AliEmptyState("🔎", "Natija topilmadi",
                                    if (busy) "Qidiruv davom etmoqda..."
                                    else "Boshqa nom bilan qidirib ko‘ring.")
                            }
                        }
                    }
                }

                "menu" -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    item {
                        Box(Modifier.fillMaxWidth()) {
                            Surface(color = Color(0xFF17171B), shape = RoundedCornerShape(24.dp)) {
                                Row(Modifier.fillMaxWidth().padding(20.dp),
                                    verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) {
                                        Text("OSHXONA MENYUSI", color = Color(0xFFFF9EA8),
                                            fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        Spacer(Modifier.height(7.dp))
                                        Text(selected?.name.orEmpty(), color = Color.White,
                                            fontSize = 24.sp, fontWeight = FontWeight.ExtraBold)
                                        Spacer(Modifier.height(7.dp))
                                        Text(selected?.address.orEmpty(), color = Color.LightGray,
                                            fontSize = 12.sp, maxLines = 2)
                                    }
                                    Icon(Icons.Default.RestaurantMenu, null, tint = Color.White,
                                         modifier = Modifier.size(44.dp))
                                }
                            }
                        }
                    }
                    item {
                        AliSectionTitle("Taomlarni tanlang", "${foods.size} ta mavjud taom")
                        if (menuCategories.size > 1) {
                            Spacer(Modifier.height(10.dp))
                            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                items(menuCategories) { category ->
                                    FilterChip(selected = menuFilter == category,
                                        onClick = { menuFilter = category },
                                        label = { Text(category) },
                                        colors = FilterChipDefaults.filterChipColors(
                                            selectedContainerColor = Color(0xFF17171B),
                                            selectedLabelColor = Color.White))
                                }
                            }
                        }
                    }
                    if (visibleMenu.isEmpty()) {
                        item {
                            AliEmptyState("🥘", "Menyu bo‘sh",
                                "Oshxona taom qo‘shgach shu yerda paydo bo‘ladi.")
                        }
                    } else {
                        items(visibleMenu, key = { it.id }) { food ->
                            AliFoodTile(food, cart[food.id] ?: 0,
                                onPlus = {
                                    cart = cart + (food.id to ((cart[food.id] ?: 0) + 1))
                                },
                                onMinus = {
                                    val left = (cart[food.id] ?: 0) - 1
                                    cart = if (left <= 0) cart - food.id
                                    else cart + (food.id to left)
                                })
                        }
                    }
                    if (cartCount > 0) {
                        item {
                            Button(onClick = { page = "cart" },
                                modifier = Modifier.fillMaxWidth().height(54.dp),
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = AliRed)) {
                                Icon(Icons.Default.ShoppingBag, null)
                                Spacer(Modifier.width(8.dp))
                                Text("Savat: ${cartCount} ta  •  ${priceText(subtotal)}",
                                    fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                "cart" -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(13.dp)
                ) {
                    item { AliSectionTitle("Savatcham", selected?.name) }
                    if (cartCount == 0) {
                        item {
                            AliEmptyState("🛒", "Savatcha bo‘sh",
                                "Taom qo‘shish uchun oshxonani tanlang.",
                                "Oshxonalarni ko‘rish") { page = "home" }
                        }
                    } else {
                        items(foods.filter { (cart[it.id] ?: 0) > 0 }, key = { it.id }) { food ->
                            AliFoodTile(food, cart[food.id] ?: 0,
                                onPlus = {
                                    cart = cart + (food.id to ((cart[food.id] ?: 0) + 1))
                                },
                                onMinus = {
                                    val left = (cart[food.id] ?: 0) - 1
                                    cart = if (left <= 0) cart - food.id
                                    else cart + (food.id to left)
                                })
                        }
                        item {
                            Surface(color = AliSurface, shape = RoundedCornerShape(19.dp)) {
                                Column(Modifier.fillMaxWidth().padding(17.dp)) {
                                    Text("Buyurtma hisoboti", fontWeight = FontWeight.Bold,
                                        fontSize = 17.sp)
                                    Spacer(Modifier.height(12.dp))
                                    Row {
                                        Text("Taomlar narxi", Modifier.weight(1f), color = AliMuted)
                                        Text(priceText(subtotal), fontWeight = FontWeight.Bold)
                                    }
                                    Spacer(Modifier.height(9.dp))
                                    Text("Yetkazish narxi buyurtma tizimi ishga tushgach hisoblanadi.",
                                        color = AliMuted, fontSize = 11.sp)
                                    Spacer(Modifier.height(12.dp))
                                    HorizontalDivider(color = AliBorder)
                                    Spacer(Modifier.height(12.dp))
                                    Text("Taomlar jami: ${priceText(subtotal)}",
                                        color = AliBlack, fontWeight = FontWeight.ExtraBold,
                                        fontSize = 20.sp)
                                }
                            }
                        }
                        item {
                            Button(onClick = { page = "checkout" },
                                modifier = Modifier.fillMaxWidth().height(54.dp),
                                shape = RoundedCornerShape(16.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = AliRed)) {
                                Text("Rasmiylashtirish  →", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                "checkout" -> LazyColumn(
                    contentPadding = PaddingValues(18.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    item { AliSectionTitle("Buyurtmani rasmiylashtirish",
                        "Taomlar, manzil va telefonni tekshiring") }
                    if (session == null) {
                        item {
                            AliEmptyState("🔐", "Tizimga kiring",
                                "Buyurtma berish uchun mijoz hisobi kerak.",
                                "Kirish") { page = "profile" }
                        }
                    } else {
                        item {
                            OutlinedTextField(address, { address = it },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text("Yetkazish manzili") },
                                leadingIcon = { Icon(Icons.Default.LocationOn, null) },
                                minLines = 2, shape = RoundedCornerShape(16.dp))
                        }
                        item {
                            OutlinedTextField(phone, { phone = it },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text("Telefon raqami") }, singleLine = true,
                                shape = RoundedCornerShape(16.dp))
                        }
                        item {
                            Surface(color = AliSurface, shape = RoundedCornerShape(17.dp)) {
                                Column(Modifier.fillMaxWidth().padding(17.dp)) {
                                    Text("To‘lov: naqd", fontWeight = FontWeight.Bold)
                                    Spacer(Modifier.height(9.dp))
                                    Text("Taomlar jami: ${priceText(subtotal)}",
                                        fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
                                    Spacer(Modifier.height(6.dp))
                                    Text("Yetkazish narxi serverda hozircha hisoblanmaydi.",
                                        fontSize = 11.sp, color = AliMuted)
                                }
                            }
                        }
                        item {
                            Row(verticalAlignment = Alignment.Top) {
                                Checkbox(checked = privacyAccepted,
                                    onCheckedChange = { privacyAccepted = it })
                                Spacer(Modifier.width(6.dp))
                                Text("Manzilim va telefonimni buyurtmani yetkazish uchun " +
                                    "qayta ishlashga roziman. Buyurtma va operator yozishmalari " +
                                    "xizmat sifatini nazorat qilish maqsadida vakolatli " +
                                    "administrator tomonidan ko‘rilishi mumkin.",
                                    modifier = Modifier.padding(top = 11.dp),
                                    fontSize = 12.sp, lineHeight = 18.sp)
                            }
                        }
                        item {
                            Button(
                                onClick = {
                                    when {
                                        cartCount < 1 || selected == null ->
                                            message = "Savat bo‘sh."
                                        address.trim().length < 5 ||
                                        !Regex("^\\+998[0-9]{9}$").matches(phone) ->
                                            message = "Manzil va telefon raqamini kiriting."
                                        !privacyAccepted ->
                                            message = "Buyurtma uchun ma’lumotlarga rozilik kerak."
                                        else -> scope.launch {
                                            busy = true
                                            try {
                                                val result = AliApi.createOrder(
                                                    session!!.token, selected!!.id,
                                                    address, phone, cart, privacyAccepted,
                                                    customerLatitude, customerLongitude
                                                )
                                                activeOrder = result
                                                activeOrderId = result.id
                                                cart = emptyMap()
                                                page = "order_status"
                                                message = "Buyurtma №${result.id} qabul qilindi."
                                            } catch (e: Exception) {
                                                message = "Buyurtma yuborilmadi: " +
                                                    (e.message ?: "Server xatosi")
                                            } finally { busy = false }
                                        }
                                    }
                                },
                                enabled = !busy,
                                modifier = Modifier.fillMaxWidth().height(55.dp),
                                shape = RoundedCornerShape(15.dp)
                            ) {
                                Icon(Icons.Default.CheckCircle, null)
                                Spacer(Modifier.width(9.dp))
                                Text("Buyurtma berish", fontWeight = FontWeight.ExtraBold)
                            }
                        }
                    }
                }

                "orders" -> AliOrdersScreen(
                    orders = myOrders,
                    loggedIn = session != null,
                    onLogin = { page = "profile" },
                    onOpen = {
                        activeOrderId = it.id
                        activeOrder = it
                        page = "order_status"
                    },
                    onRefresh = {
                        if (session != null) scope.launch {
                            try { myOrders = AliApi.myOrders(session!!.token) }
                            catch (e: Exception) {
                                message = e.message ?: "Buyurtmalar yangilanmadi"
                            }
                        }
                    }
                )

                "order_status" -> AliOrderTracker(
                    order = activeOrder,
                    onRefresh = { loadOrder() },
                    onSupport = { openSupport() },
                    onOrderChat = {
                        conversationText = ""
                        page = "order_chat"
                    }
                )

                "support" -> AliConversationScreen(
                    title = "Operator bilan onlayn chat",
                    note = "Xabarlar server orqali yetkaziladi • 7 soniyada yangilanadi",
                    messages = supportMessages,
                    text = conversationText,
                    onText = { conversationText = it.take(1000) },
                    onRefresh = {
                        if (session != null) scope.launch {
                            try { supportMessages = AliApi.supportMessages(session!!.token) }
                            catch (e: Exception) { message = e.message ?: "Chat ishlamadi" }
                        }
                    },
                    onSend = {
                        val body = conversationText.trim()
                        if (body.isNotEmpty() && session != null) {
                            conversationText = ""
                            scope.launch {
                                try {
                                    AliApi.sendSupportMessage(session!!.token, body)
                                    supportMessages = AliApi.supportMessages(session!!.token)
                                } catch (e: Exception) {
                                    conversationText = body
                                    message = e.message ?: "Xabar yetkazilmadi"
                                }
                            }
                        }
                    }
                )

                "order_chat" -> AliConversationScreen(
                    title = "Buyurtma №${activeOrderId} chati",
                    note = "Kuryer, oshxona va operator bilan yozishmalar",
                    messages = orderMessages,
                    text = conversationText,
                    onText = { conversationText = it.take(1000) },
                    onRefresh = {
                        if (session != null && activeOrderId > 0) scope.launch {
                            try {
                                orderMessages = AliApi.orderMessages(session!!.token, activeOrderId)
                            } catch (e: Exception) { message = e.message ?: "Chat ishlamadi" }
                        }
                    },
                    onSend = {
                        val body = conversationText.trim()
                        if (body.isNotEmpty() && session != null && activeOrderId > 0) {
                            conversationText = ""
                            scope.launch {
                                try {
                                    AliApi.sendOrderMessage(session!!.token, activeOrderId, body)
                                    orderMessages = AliApi.orderMessages(session!!.token, activeOrderId)
                                } catch (e: Exception) {
                                    conversationText = body
                                    message = e.message ?: "Xabar yetkazilmadi"
                                }
                            }
                        }
                    }
                )

                "profile" -> LazyColumn(contentPadding = PaddingValues(18.dp),
                    verticalArrangement = Arrangement.spacedBy(13.dp)) {
                    item {
                        AliSectionTitle("Mening profilim", "Ali Kuryer mijoz hisobi")
                    }
                    item {
                        AliAppearanceSelector(appearanceMode, onAppearanceChange)
                    }
                    item {
                        Surface(shape = RoundedCornerShape(21.dp), color = Color(0xFF17171B)) {
                            Row(Modifier.fillMaxWidth().padding(18.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.AccountCircle, null, tint = Color.White,
                                    modifier = Modifier.size(53.dp))
                                Spacer(Modifier.width(11.dp))
                                Column {
                                    Text(if (session == null) "Xush kelibsiz!"
                                         else (fullName.ifBlank { "Ali Kuryer mijozi" }),
                                        color = Color.White, fontSize = 19.sp,
                                        fontWeight = FontWeight.ExtraBold)
                                    Text(if (session == null) "Hisobga kiring yoki ro‘yxatdan o‘ting"
                                         else phone,
                                        color = Color.White.copy(alpha = .7f), fontSize = 12.sp)
                                }
                            }
                        }
                    }
                    if (session == null) {
                        item {
                            Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                FilterChip(
                                    selected = !registerMode && !firebaseLoginMode,
                                    onClick = { registerMode = false; firebaseLoginMode = false },
                                    label = { Text("Parol bilan") }
                                )
                                FilterChip(
                                    selected = firebaseLoginMode,
                                    onClick = { registerMode = false; firebaseLoginMode = true },
                                    label = { Text("SMS bilan") }
                                )
                                FilterChip(
                                    selected = registerMode,
                                    onClick = { registerMode = true; firebaseLoginMode = false },
                                    label = { Text("Ro‘yxatdan o‘tish") }
                                )
                            }
                        }
                        if (registerMode) item {
                            OutlinedTextField(
                                fullName, { fullName = it },
                                label = { Text("Ism va familiya") },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(14.dp)
                            )
                        }
                        if (registerMode || firebaseLoginMode) {
                            item {
                                AliFirebasePhonePanel(
                                    phone = phone,
                                    onPhoneChange = { phone = it },
                                    onTokenVerified = { firebaseToken ->
                                        scope.launch {
                                            busy = true
                                            try {
                                                session = AliApi.firebasePhoneLogin(
                                                    firebaseToken, fullName.trim()
                                                )
                                                phoneVerified = true
                                                password = ""
                                                message = "Telefon Firebase orqali tasdiqlandi"
                                            } catch (e: Exception) {
                                                message = e.message ?: "SMS tekshiruvini server qabul qilmadi"
                                            } finally {
                                                busy = false
                                            }
                                        }
                                    }
                                )
                                if (busy) LinearProgressIndicator(
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }
                        } else {
                            item {
                                OutlinedTextField(phone, { phone = it },
                                    label = { Text("Telefon: +998XXXXXXXXX") },
                                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                                    shape = RoundedCornerShape(14.dp))
                            }
                            item {
                                OutlinedTextField(password, { password = it },
                                    label = { Text("Parol (kamida 8 belgi)") },
                                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                                    visualTransformation = PasswordVisualTransformation(),
                                    shape = RoundedCornerShape(14.dp))
                            }
                            item {
                                Button(onClick = {
                                    if (!Regex("^\\+998[0-9]{9}$").matches(phone) ||
                                        password.length < 8) {
                                        message = "Telefon yoki parol noto‘g‘ri."
                                    } else {
                                        scope.launch {
                                            busy = true
                                            try {
                                                session = AliApi.login(phone, password)
                                                phoneVerified = AliApi.isPhoneVerified(session!!.token)
                                                message = "Mijoz hisobiga muvaffaqiyatli kirdingiz"
                                                password = ""
                                            } catch (e: Exception) {
                                                message = e.message ?: "Tizimga kirish amalga oshmadi"
                                            } finally {
                                                busy = false
                                            }
                                        }
                                    }
                                }, modifier = Modifier.fillMaxWidth().height(51.dp),
                                    enabled = !busy, shape = RoundedCornerShape(15.dp)) {
                                    Text("Kirish", fontWeight = FontWeight.Bold)
                                }
                            }
                        }
                    } else {
                        item {
                            Surface(color = AliSurface, shape = RoundedCornerShape(17.dp)) {
                                Column(
                                    Modifier.fillMaxWidth().padding(15.dp),
                                    verticalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Text("Telefon raqami xavfsizligi", fontWeight = FontWeight.Bold)
                                    Text(when (phoneVerified) {
                                        true -> "✅ Telefon SMS orqali tasdiqlangan"
                                        false -> "⚠️ Telefoningizni SMS orqali tasdiqlang"
                                        null -> "Telefon raqami tekshirilmoqda..."
                                    }, fontSize = 12.sp, color = AliMuted)
                                }
                            }
                        }
                        if (phoneVerified == false) item {
                            AliFirebasePhonePanel(
                                phone = phone, onPhoneChange = { phone = it },
                                onTokenVerified = { firebaseToken ->
                                    scope.launch {
                                        busy = true
                                        try {
                                            val newSession = AliApi.firebasePhoneLogin(
                                                firebaseToken, fullName.trim()
                                            )
                                            session = newSession
                                            phoneVerified = true
                                            message = "Telefoningiz SMS orqali tasdiqlandi"
                                        } catch (e: Exception) {
                                            message = e.message ?: "Raqam tasdiqlanmadi"
                                        } finally {
                                            busy = false
                                        }
                                    }
                                }
                            )
                        }
                        item {
                            OutlinedButton(onClick = {
                                session = null
                                phoneVerified = null
                                firebaseLoginMode = false
                            }, modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(14.dp)) {
                                Text("Hisobdan chiqish", color = AliRed)
                            }
                        }
                    }
                    item {
                        HorizontalDivider(color = AliBorder)
                        Surface(onClick = { page = "chat" },
                            color = AliSurface, shape = RoundedCornerShape(16.dp)) {
                            Row(Modifier.fillMaxWidth().padding(15.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.SmartToy, null, tint = AliRed)
                                Spacer(Modifier.width(12.dp))
                                Text("Muhammadali yordamchi", Modifier.weight(1f),
                                    fontWeight = FontWeight.Bold)
                                Icon(Icons.Default.ChevronRight, null, tint = AliMuted)
                            }
                        }
                        Spacer(Modifier.height(7.dp))
                        Surface(onClick = { openSupport() },
                            color = AliSurface, shape = RoundedCornerShape(16.dp)) {
                            Row(Modifier.fillMaxWidth().padding(15.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.SupportAgent, null, tint = AliRed)
                                Spacer(Modifier.width(12.dp))
                                Text("Operator bilan bog‘lanish", Modifier.weight(1f),
                                    fontWeight = FontWeight.Bold)
                                Icon(Icons.Default.OpenInNew, null, tint = AliMuted)
                            }
                        }
                        Spacer(Modifier.height(12.dp))
                        Text("Ali Kuryer • mijoz ilovasi 1.3.0",
                            color = AliMuted, fontSize = 11.sp)
                    }
                }

                "chat" -> Column(Modifier.fillMaxSize().padding(16.dp)) {
                    AliSectionTitle("Muhammadali", "Ali Kuryer virtual yordamchisi")
                    Spacer(Modifier.height(10.dp))
                    LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        item {
                            Surface(color = AliSurface,
                                shape = RoundedCornerShape(16.dp)) {
                                Text("Assalomu alaykum! Men Muhammadali. " +
                                    "Taom tanlashda yordam beraman. Nima haqida so‘ramoqchisiz?",
                                    modifier = Modifier.padding(15.dp), fontSize = 13.sp)
                            }
                        }
                        items(chat.size) { index ->
                            val item = chat[index]
                            Row(Modifier.fillMaxWidth(),
                                horizontalArrangement = if (item.first)
                                    Arrangement.End else Arrangement.Start) {
                                Surface(color = if (item.first) AliRed else AliSurface,
                                    shape = RoundedCornerShape(17.dp),
                                    modifier = Modifier.fillMaxWidth(.87f)) {
                                    Text(item.second, modifier = Modifier.padding(13.dp),
                                        color = if (item.first) Color.White else AliBlack,
                                        fontSize = 13.sp, lineHeight = 19.sp)
                                }
                            }
                        }
                    }
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(checked = retainAiHistory && session != null,
                            enabled = session != null,
                            onCheckedChange = { retainAiHistory = it })
                        Text(
                            if (session == null) "AI suhbatini saqlash uchun profilga kiring"
                            else "AI suhbatini 30 kungacha saqlashga roziman; admin ko‘rishi mumkin",
                            fontSize = 11.sp, color = AliMuted,
                            modifier = Modifier.weight(1f)
                        )
                    }
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        OutlinedTextField(chatText, { chatText = it.take(600) },
                            modifier = Modifier.weight(1f), maxLines = 3,
                            placeholder = { Text("Savolingizni yozing...") },
                            shape = RoundedCornerShape(17.dp))
                        Spacer(Modifier.width(8.dp))
                        FilledIconButton(onClick = {
                            val question = chatText.trim()
                            if (question.length > 1) {
                                chat.add(true to question)
                                chatText = ""
                                scope.launch {
                                    try { chat.add(false to AliApi.chat(question, session?.token,
                                        session != null && retainAiHistory)) }
                                    catch (e: Exception) {
                                        val detail = (e as? IllegalStateException)?.message
                                        chat.add(false to (
                                            (detail?.takeIf { it.isNotBlank() }
                                                ?: "Internet yoki AI xizmati bilan aloqa uzildi.") +
                                            " Operator bilan ilovadagi onlayn chat orqali bog‘lanishingiz mumkin."
                                        ))
                                    }
                                }
                            }
                        }, modifier = Modifier.size(52.dp), enabled = chatText.trim().length > 1,
                            colors = IconButtonDefaults.filledIconButtonColors(
                                containerColor = AliRed)) {
                            Icon(Icons.Default.Send, "Yuborish", tint = Color.White)
                        }
                    }
                }
            }
        }
    }
}
