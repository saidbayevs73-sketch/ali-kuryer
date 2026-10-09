package uz.alikuryer.customer

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import java.util.Locale

private val BrandRed = Color(0xFFD72531)
private val Background = Color(0xFFF8F8FA)
private fun money(value: Long): String =
    "%,d so‘m".format(Locale.US, value).replace(",", " ")

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = BrandRed, background = Background)) {
                CustomerApp()
            }
        }
    }
}

@Composable
private fun CustomerApp() {
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var page by remember { mutableStateOf("home") }
    var restaurants by remember { mutableStateOf<List<Restaurant>>(emptyList()) }
    var foods by remember { mutableStateOf<List<Food>>(emptyList()) }
    var selected by remember { mutableStateOf<Restaurant?>(null) }
    var cart by remember { mutableStateOf<Map<Int, Int>>(emptyMap()) }
    var busy by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf("") }
    var search by remember { mutableStateOf("") }
    var deliveryAddress by remember { mutableStateOf("") }
    var session by remember { mutableStateOf<Session?>(null) }
    var fullName by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("+998") }
    var password by remember { mutableStateOf("") }
    var registerMode by remember { mutableStateOf(false) }

    fun reloadRestaurants() {
        scope.launch {
            busy = true
            try {
                restaurants = AliApi.restaurants()
                notice = if (restaurants.isEmpty()) "Hozircha tasdiqlangan restoranlar yo‘q" else ""
            } catch (e: Exception) {
                notice = "Restoranlar yuklanmadi: " + (e.message ?: "Internetni tekshiring")
            } finally { busy = false }
        }
    }

    fun openRestaurant(restaurant: Restaurant) {
        if (selected?.id != restaurant.id) cart = emptyMap()
        selected = restaurant
        foods = emptyList()
        page = "menu"
        scope.launch {
            busy = true
            try {
                foods = AliApi.menu(restaurant.id)
                notice = ""
            } catch (e: Exception) {
                notice = "Menyu yuklanmadi: " + (e.message ?: "Internetni tekshiring")
            } finally { busy = false }
        }
    }

    LaunchedEffect(Unit) { reloadRestaurants() }
    val total = foods.sumOf { it.price * (cart[it.id] ?: 0) }
    val cartCount = cart.values.sum()
    val visibleRestaurants = restaurants.filter {
        it.name.contains(search, ignoreCase = true) ||
            it.address.contains(search, ignoreCase = true)
    }

    Scaffold(
        containerColor = Background,
        topBar = {
            Surface(color = BrandRed, shadowElevation = 3.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().height(68.dp).padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (page == "menu" || page == "checkout") {
                        IconButton(onClick = { page = if (page == "checkout") "cart" else "home" }) {
                            Icon(Icons.Default.ArrowBack, "Orqaga", tint = Color.White)
                        }
                    } else {
                        Icon(Icons.Default.DeliveryDining, null,
                            modifier = Modifier.size(40.dp), tint = Color.White)
                        Spacer(Modifier.width(10.dp))
                    }
                    Column(Modifier.weight(1f)) {
                        Text("ALI KURYER", color = Color.White,
                            fontSize = 20.sp, fontWeight = FontWeight.Black)
                        Text("Mazali taomlar, qulay buyurtma",
                            color = Color.White.copy(alpha = 0.85f), fontSize = 11.sp)
                    }
                    IconButton(onClick = { page = "cart" }) {
                        BadgedBox(badge = {
                            if (cartCount > 0) Badge { Text(cartCount.toString()) }
                        }) {
                            Icon(Icons.Default.ShoppingCart, "Savatcha", tint = Color.White)
                        }
                    }
                }
            }
        },
        bottomBar = {
            NavigationBar(containerColor = Color.White) {
                NavigationBarItem(
                    selected = page == "home" || page == "menu",
                    onClick = { page = "home" },
                    icon = { Icon(Icons.Default.Home, "Bosh sahifa") },
                    label = { Text("Bosh sahifa", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = page == "cart" || page == "checkout",
                    onClick = { page = "cart" },
                    icon = { Icon(Icons.Default.ShoppingCart, "Savatcha") },
                    label = { Text("Savatcha", fontSize = 10.sp) }
                )
                NavigationBarItem(
                    selected = page == "profile",
                    onClick = { page = "profile" },
                    icon = { Icon(Icons.Default.Person, "Profil") },
                    label = { Text("Profil", fontSize = 10.sp) }
                )
            }
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            if (notice.isNotBlank()) {
                Surface(color = Color(0xFFFFF0D5)) {
                    Row(Modifier.fillMaxWidth().padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(notice, Modifier.weight(1f), fontSize = 12.sp)
                        IconButton(onClick = { notice = "" }, modifier = Modifier.size(26.dp)) {
                            Icon(Icons.Default.Close, "Yopish")
                        }
                    }
                }
            }
            when (page) {
                "home" -> LazyColumn(contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    item {
                        Surface(color = Color.White, shape = RoundedCornerShape(20.dp)) {
                            Column(Modifier.padding(17.dp)) {
                                Text("🍔 Och qoldingizmi?", fontWeight = FontWeight.Black, fontSize = 23.sp)
                                Text("Yaqin restoranlardan taom tanlang", fontSize = 13.sp)
                                Spacer(Modifier.height(15.dp))
                                OutlinedTextField(
                                    value = search, onValueChange = { search = it },
                                    placeholder = { Text("Restoran qidirish") },
                                    leadingIcon = { Icon(Icons.Default.Search, null) },
                                    modifier = Modifier.fillMaxWidth(),
                                    singleLine = true
                                )
                            }
                        }
                    }
                    item {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Restoranlar", fontWeight = FontWeight.Bold,
                                fontSize = 19.sp, modifier = Modifier.weight(1f))
                            Text(visibleRestaurants.size.toString() + " ta", fontSize = 13.sp)
                            IconButton(onClick = { reloadRestaurants() }) {
                                Icon(Icons.Default.Refresh, "Yangilash")
                            }
                        }
                    }
                    if (visibleRestaurants.isEmpty()) {
                        item {
                            Text("Hozircha restoran topilmadi. Yangilash tugmasini bosing.",
                                modifier = Modifier.padding(14.dp))
                        }
                    }
                    items(visibleRestaurants, key = { it.id }) { restaurant ->
                        Card(onClick = { openRestaurant(restaurant) },
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            shape = RoundedCornerShape(18.dp)) {
                            Row(Modifier.fillMaxWidth().padding(18.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Text("🍽️", fontSize = 35.sp)
                                Spacer(Modifier.width(14.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(restaurant.name, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                                    Text(restaurant.address.ifBlank { "Menyuni ko‘rish" },
                                        fontSize = 12.sp, maxLines = 2,
                                        overflow = TextOverflow.Ellipsis)
                                }
                                Icon(Icons.Default.ChevronRight, null, tint = BrandRed)
                            }
                        }
                    }
                    item {
                        OutlinedButton(onClick = {
                            context.startActivity(Intent(Intent.ACTION_VIEW,
                                Uri.parse("https://t.me/AliKuryerYordamBot")))
                        }, modifier = Modifier.fillMaxWidth()) {
                            Icon(Icons.Default.SupportAgent, null)
                            Spacer(Modifier.width(8.dp))
                            Text("Ali yordamchiga yozish")
                        }
                    }
                }
                "menu" -> LazyColumn(contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    item {
                        Text(selected?.name ?: "Menyu", fontWeight = FontWeight.Black,
                            fontSize = 22.sp)
                        Text("O‘zingizga yoqqan taomlarni tanlang", fontSize = 13.sp)
                    }
                    if (foods.isEmpty()) {
                        item { Text("Menyu bo‘sh yoki yuklanmoqda.") }
                    }
                    items(foods, key = { it.id }) { food ->
                        Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
                            Row(Modifier.fillMaxWidth().padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Text("🥘", fontSize = 34.sp)
                                Spacer(Modifier.width(12.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(food.name, fontWeight = FontWeight.Bold)
                                    Text(money(food.price), color = BrandRed, fontSize = 13.sp)
                                }
                                IconButton(onClick = {
                                    cart = cart + (food.id to ((cart[food.id] ?: 0) + 1))
                                }) {
                                    Icon(Icons.Default.AddCircle, "Qo‘shish", tint = BrandRed)
                                }
                            }
                        }
                    }
                    if (cartCount > 0) {
                        item {
                            Button(onClick = { page = "cart" }, Modifier.fillMaxWidth()) {
                                Text("Savatcha: " + cartCount + " ta — " + money(total))
                            }
                        }
                    }
                }
                "cart" -> LazyColumn(contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    item {
                        Text("Savatcha", fontSize = 23.sp, fontWeight = FontWeight.Black)
                        Text(selected?.name.orEmpty(), fontSize = 13.sp)
                    }
                    if (cartCount == 0) {
                        item { Text("Savatchangiz bo‘sh. Restorandan taom tanlang.") }
                    }
                    items(foods.filter { (cart[it.id] ?: 0) > 0 }, key = { it.id }) { food ->
                        Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
                            Row(Modifier.fillMaxWidth().padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(food.name, fontWeight = FontWeight.Bold)
                                    Text(money(food.price * (cart[food.id] ?: 0)))
                                }
                                IconButton(onClick = {
                                    val next = (cart[food.id] ?: 1) - 1
                                    cart = if (next == 0) cart - food.id else cart + (food.id to next)
                                }) { Icon(Icons.Default.RemoveCircleOutline, "Kamaytirish") }
                                Text((cart[food.id] ?: 0).toString())
                                IconButton(onClick = {
                                    cart = cart + (food.id to ((cart[food.id] ?: 0) + 1))
                                }) { Icon(Icons.Default.AddCircleOutline, "Ko‘paytirish") }
                            }
                        }
                    }
                    if (cartCount > 0) {
                        item {
                            HorizontalDivider()
                            Text("Jami: " + money(total), fontWeight = FontWeight.Bold,
                                fontSize = 20.sp)
                            Spacer(Modifier.height(8.dp))
                            Button(onClick = { page = "checkout" },
                                modifier = Modifier.fillMaxWidth()) {
                                Text("Davom etish")
                            }
                        }
                    }
                }
                "checkout" -> Column(
                    Modifier.fillMaxSize().padding(17.dp),
                    verticalArrangement = Arrangement.spacedBy(13.dp)
                ) {
                    Text("Buyurtmani rasmiylashtirish", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                    if (session == null) {
                        Text("Buyurtmadan oldin Profil orqali mijoz sifatida tizimga kiring.")
                        Button(onClick = { page = "profile" }) { Text("Profilga o‘tish") }
                    } else {
                        Text("Jami: " + money(total))
                        OutlinedTextField(
                            value = deliveryAddress, onValueChange = { deliveryAddress = it },
                            label = { Text("Aniq yetkazish manzili") },
                            modifier = Modifier.fillMaxWidth(), minLines = 2
                        )
                        Text("To‘lov usuli: naqd", fontSize = 13.sp)
                        Text("Diqqat: serverda buyurtmalarni qabul qilish API hali yakunlanmagan. " +
                            "Hozircha buyurtma yuborilmaydi va pul yechilmaydi.",
                            color = Color(0xFF8F4E00), fontSize = 13.sp)
                        Button(onClick = {
                            notice = if (deliveryAddress.isBlank()) "Avval aniq manzilni kiriting"
                            else "Buyurtma funksiyasi serverga ulangach ishga tushadi"
                        }, modifier = Modifier.fillMaxWidth()) {
                            Text("Buyurtmani tekshirish")
                        }
                    }
                }
                "profile" -> Column(Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Mijoz profili", fontSize = 23.sp, fontWeight = FontWeight.Black)
                    if (session != null) {
                        Text("✅ Mijoz hisobiga kirdingiz.")
                        Text("Buyurtma qilish uchun savatchaga qayting.")
                        OutlinedButton(onClick = { session = null }) { Text("Chiqish") }
                    } else {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            FilterChip(selected = !registerMode, onClick = { registerMode = false },
                                label = { Text("Kirish") })
                            Spacer(Modifier.width(8.dp))
                            FilterChip(selected = registerMode, onClick = { registerMode = true },
                                label = { Text("Ro‘yxatdan o‘tish") })
                        }
                        if (registerMode) {
                            OutlinedTextField(fullName, { fullName = it },
                                label = { Text("Ism-familiya") }, modifier = Modifier.fillMaxWidth())
                        }
                        OutlinedTextField(phone, { phone = it },
                            label = { Text("Telefon: +998XXXXXXXXX") },
                            modifier = Modifier.fillMaxWidth(), singleLine = true)
                        OutlinedTextField(password, { password = it },
                            label = { Text("Parol (kamida 8 belgi)") },
                            visualTransformation = PasswordVisualTransformation(),
                            modifier = Modifier.fillMaxWidth(), singleLine = true)
                        Button(
                            onClick = {
                                if (!Regex("^\\+998[0-9]{9}$").matches(phone) ||
                                    password.length < 8 || (registerMode && fullName.trim().length < 2)) {
                                    notice = "Ism, telefon yoki parolni tekshiring"
                                } else {
                                    scope.launch {
                                        busy = true
                                        try {
                                            if (registerMode) AliApi.register(fullName.trim(), phone, password)
                                            session = AliApi.login(phone, password)
                                            notice = "Mijoz sifatida muvaffaqiyatli kirdingiz"
                                            password = ""
                                        } catch (e: Exception) {
                                            notice = e.message ?: "Kirish amalga oshmadi"
                                        } finally { busy = false }
                                    }
                                }
                            }, modifier = Modifier.fillMaxWidth(), enabled = !busy
                        ) {
                            Text(if (registerMode) "Ro‘yxatdan o‘tish" else "Kirish")
                        }
                        Text("Kuryer, oshxona va admin kirishi bu ilovada mavjud emas.",
                            fontSize = 12.sp)
                    }
                }
            }
        }
    }
}
