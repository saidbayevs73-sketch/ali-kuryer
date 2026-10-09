package uz.alikuryer.customer

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.enableEdgeToEdge
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
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
        // Android 15 edge-to-edge: use window insets so content never overlaps clock/notch.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.light(android.graphics.Color.WHITE, android.graphics.Color.BLACK),
            navigationBarStyle = SystemBarStyle.light(android.graphics.Color.WHITE, android.graphics.Color.BLACK)
        )
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = AliRed, onPrimary = Color.White, background = AliCanvas,
                    surface = Color.White, onSurface = AliBlack
                )
            ) {
                var splash by remember { mutableStateOf(true) }
                LaunchedEffect(Unit) { delay(950); splash = false }
                Surface(
                    modifier = Modifier.fillMaxSize().safeDrawingPadding(),
                    color = AliCanvas
                ) {
                    if (splash) AliSplash() else AliCustomerApp()
                }
            }
        }
    }
}

@Composable
private fun AliSplash() {
    Surface(color = Color.White, modifier = Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally) {
            AliMark(size = 96)
            Spacer(Modifier.height(18.dp))
            Text("ALI KURYER", fontWeight = FontWeight.Black, fontSize = 32.sp,
                color = AliBlack, letterSpacing = 1.4.sp)
            Spacer(Modifier.height(7.dp))
            Text("MAZALI TAOMLAR. SIZGA YAQIN.", color = AliRed,
                fontSize = 11.sp, letterSpacing = 1.5.sp,
                fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(30.dp))
            CircularProgressIndicator(color = AliRed, strokeWidth = 3.dp,
                modifier = Modifier.size(25.dp))
        }
    }
}

@Composable
private fun AliCustomerApp() {
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
    var editAddress by remember { mutableStateOf(false) }
    var session by remember { mutableStateOf<Session?>(null) }
    var fullName by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("+998") }
    var password by remember { mutableStateOf("") }
    var registerMode by remember { mutableStateOf(false) }
    var chatText by remember { mutableStateOf("") }
    val chat = remember { mutableStateListOf<Pair<Boolean, String>>() }

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
            Surface(color = Color.White, shadowElevation = 1.dp) {
                Column(Modifier.fillMaxWidth()) {
                    Row(Modifier.fillMaxWidth().height(74.dp)
                        .padding(horizontal = 16.dp),
                        verticalAlignment = Alignment.CenterVertically) {
                        if (page == "menu" || page == "checkout" || page == "chat") {
                            IconButton(onClick = {
                                page = when (page) {
                                    "checkout" -> "cart"
                                    "chat" -> "home"
                                    else -> "home"
                                }
                            }) { Icon(Icons.Default.ArrowBack, "Orqaga", tint = AliBlack) }
                            Spacer(Modifier.width(4.dp))
                        }
                        AliWordmark(Modifier.weight(1f), subtitle = page == "home")
                        IconButton(onClick = { page = "profile" }) {
                            Icon(Icons.Default.AccountCircle, "Profil", tint = AliBlack,
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
                                Text("YETKAZISH MANZILI", color = AliMuted,
                                    fontWeight = FontWeight.Bold, fontSize = 10.sp)
                                Text(address.ifBlank { "Yetkazish manzilini kiriting" },
                                    fontSize = 14.sp, color = AliBlack,
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
            if (page != "chat") NavigationBar(
                containerColor = Color.White, tonalElevation = 7.dp) {
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
                            color = AliBlack, fontSize = 12.sp)
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
                            color = Color.White, border = BorderStroke(1.dp, AliBorder)) {
                            Row(Modifier.fillMaxWidth().height(54.dp)
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
                            color = Color.White, shape = RoundedCornerShape(19.dp),
                            border = BorderStroke(1.dp, AliBorder)) {
                            Row(Modifier.fillMaxWidth().padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(50.dp).clip(RoundedCornerShape(15.dp))
                                    .then(Modifier),
                                    contentAlignment = Alignment.Center) {
                                    Text("🤖", fontSize = 36.sp)
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
                                    color = Color.White, border = BorderStroke(1.dp, AliBorder)) {
                                    Row(Modifier.fillMaxWidth().padding(15.dp),
                                        verticalAlignment = Alignment.CenterVertically) {
                                        Text("🍱", fontSize = 31.sp)
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
                            Surface(color = AliBlack, shape = RoundedCornerShape(24.dp)) {
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
                                    Text("🍽️", fontSize = 47.sp)
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
                                            selectedContainerColor = AliBlack,
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
                            Surface(color = Color.White, shape = RoundedCornerShape(19.dp)) {
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

                "checkout" -> Column(Modifier.fillMaxSize().padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(13.dp)) {
                    AliSectionTitle("Rasmiylashtirish", "Ma’lumotlaringizni tekshiring")
                    if (session == null) {
                        AliEmptyState("🔐", "Hisobga kiring",
                            "Buyurtma berishdan oldin mijoz sifatida kiring.",
                            "Kirish") { page = "profile" }
                    } else {
                        OutlinedTextField(address, { address = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Yetkazish manzili") },
                            leadingIcon = { Icon(Icons.Default.LocationOn, null) },
                            minLines = 2, shape = RoundedCornerShape(16.dp))
                        OutlinedTextField(phone, { phone = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("Telefon raqamingiz") },
                            singleLine = true, shape = RoundedCornerShape(16.dp))
                        Surface(color = Color.White, shape = RoundedCornerShape(17.dp)) {
                            Column(Modifier.padding(17.dp)) {
                                Text("To‘lov usuli: naqd", fontWeight = FontWeight.Bold)
                                Spacer(Modifier.height(8.dp))
                                Text("Taomlar jami: ${priceText(subtotal)}",
                                    fontWeight = FontWeight.ExtraBold, fontSize = 19.sp)
                            }
                        }
                        Surface(color = Color(0xFFFFF3DF),
                            shape = RoundedCornerShape(15.dp)) {
                            Text("Buyurtma qabul qilish serveri hali ishga tushirilmagan. " +
                                "Bu test versiyada buyurtma jo‘natilmaydi va pul yechilmaydi.",
                                modifier = Modifier.padding(14.dp), color = AliBlack,
                                fontSize = 12.sp, lineHeight = 18.sp)
                        }
                        Button(onClick = {
                            message = if (address.trim().length < 5 ||
                                !Regex("^\\+998[0-9]{9}$").matches(phone))
                                "Manzil va telefon raqamini to‘liq kiriting"
                            else "Buyurtma serveri hali ulanmagan; buyurtma yuborilmadi."
                        }, modifier = Modifier.fillMaxWidth().height(54.dp),
                            shape = RoundedCornerShape(14.dp)) {
                            Text("Ma’lumotlarni tekshirish")
                        }
                    }
                }

                "orders" -> LazyColumn(contentPadding = PaddingValues(16.dp)) {
                    item {
                        AliSectionTitle("Buyurtmalarim", "Buyurtmalaringiz tarixi")
                        Spacer(Modifier.height(16.dp))
                        AliEmptyState("📦", "Buyurtma tarixi",
                            "Buyurtmalar API ulanmagani uchun hozircha haqiqiy " +
                                "buyurtma holatlarini ko‘rsata olmaymiz.",
                            "Oshxonalarni ko‘rish") { page = "home" }
                    }
                }

                "profile" -> LazyColumn(contentPadding = PaddingValues(18.dp),
                    verticalArrangement = Arrangement.spacedBy(13.dp)) {
                    item {
                        AliSectionTitle("Mening profilim", "Ali Kuryer mijoz hisobi")
                    }
                    item {
                        Surface(shape = RoundedCornerShape(21.dp), color = AliBlack) {
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
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                FilterChip(selected = !registerMode,
                                    onClick = { registerMode = false },
                                    label = { Text("Kirish") })
                                FilterChip(selected = registerMode,
                                    onClick = { registerMode = true },
                                    label = { Text("Ro‘yxatdan o‘tish") })
                            }
                        }
                        if (registerMode) item {
                            OutlinedTextField(fullName, { fullName = it },
                                label = { Text("Ism va familiya") },
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(14.dp))
                        }
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
                                    password.length < 8 || (registerMode && fullName.trim().length < 2)) {
                                    message = "Ism, telefon yoki parolni to‘g‘ri kiriting."
                                } else {
                                    scope.launch {
                                        busy = true
                                        try {
                                            if (registerMode) AliApi.register(
                                                fullName.trim(), phone, password)
                                            session = AliApi.login(phone, password)
                                            message = "Mijoz hisobiga muvaffaqiyatli kirdingiz"
                                            password = ""
                                        } catch (e: Exception) {
                                            message = e.message ?: "Tizimga kirish amalga oshmadi"
                                        } finally { busy = false }
                                    }
                                }
                            }, modifier = Modifier.fillMaxWidth().height(51.dp),
                                enabled = !busy, shape = RoundedCornerShape(15.dp)) {
                                Text(if (registerMode) "Ro‘yxatdan o‘tish" else "Kirish",
                                    fontWeight = FontWeight.Bold)
                            }
                        }
                    } else item {
                        OutlinedButton(onClick = { session = null },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(14.dp)) {
                            Text("Hisobdan chiqish", color = AliRed)
                        }
                    }
                    item {
                        HorizontalDivider(color = AliBorder)
                        Surface(onClick = { page = "chat" },
                            color = Color.White, shape = RoundedCornerShape(16.dp)) {
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
                        Surface(onClick = {
                            context.startActivity(Intent(Intent.ACTION_VIEW,
                                Uri.parse("https://t.me/AliKuryerYordamBot")))
                        }, color = Color.White, shape = RoundedCornerShape(16.dp)) {
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
                        Text("Ali Kuryer • mijoz ilovasi 1.1.0",
                            color = AliMuted, fontSize = 11.sp)
                    }
                }

                "chat" -> Column(Modifier.fillMaxSize().padding(16.dp)) {
                    AliSectionTitle("Muhammadali", "Ali Kuryer virtual yordamchisi")
                    Spacer(Modifier.height(10.dp))
                    LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        item {
                            Surface(color = Color.White,
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
                                Surface(color = if (item.first) AliRed else Color.White,
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
                                    try { chat.add(false to AliApi.chat(question)) }
                                    catch (_: Exception) {
                                        chat.add(false to "Yordamchi hozir javob bera olmadi. " +
                                            "Operatorga Telegram orqali yozishingiz mumkin.")
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
