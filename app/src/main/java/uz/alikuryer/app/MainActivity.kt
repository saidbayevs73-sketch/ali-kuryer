package uz.alikuryer.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

private val Red = Color(0xFFE53935)
private val Ink = Color(0xFF171717)
private val Soft = Color(0xFFF6F6F6)
private const val WEB_CLIENT_ID = "1088566467185-1tefomqi153ho33u18r40u3p27le8gbm.apps.googleusercontent.com"

private data class Food(val id: Int, val name: String, val category: String, val price: Int, val emoji: String, val note: String)
private val foods = listOf(
    Food(1, "Lavash max", "Fast food", 32000, "🌯", "Mol go‘shti, sous va sabzavotlar"),
    Food(2, "Cheese burger", "Fast food", 28000, "🍔", "Pishloq va maxsus sous"),
    Food(3, "Pepperoni pizza", "Pizza", 69000, "🍕", "Pishloq va pepperoni"),
    Food(4, "Margarita pizza", "Pizza", 59000, "🍕", "Pomidor va mozzarella"),
    Food(5, "Sushi set", "Sushi", 85000, "🍣", "Oshpaz tanlovi"),
    Food(6, "Cola 1L", "Ichimlik", 12000, "🥤", "Sovutilgan ichimlik")
)

class MainActivity : ComponentActivity() {
    private val auth by lazy { FirebaseAuth.getInstance() }
    private var authStatus by mutableStateOf("Google hisob orqali kiring")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = android.graphics.Color.WHITE
        window.navigationBarColor = android.graphics.Color.WHITE
        window.decorView.systemUiVisibility =
            android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
            android.view.View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR

        setContent {
            var page by remember { mutableStateOf("home") }
            var category by remember { mutableStateOf("Barchasi") }
            val cart = remember { mutableStateMapOf<Int, Int>() }
            val count = cart.values.sum()
            val total = foods.sumOf { food -> food.price * (cart[food.id] ?: 0) }

            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = Red,
                    background = Color.White,
                    surface = Color.White,
                    onPrimary = Color.White,
                    onSurface = Ink
                )
            ) {
                Scaffold(
                    containerColor = Color.White,
                    bottomBar = {
                        NavigationBar(containerColor = Color.White) {
                            listOf("home" to "Bosh sahifa", "cart" to "Savat", "orders" to "Buyurtmalar", "profile" to "Profil").forEach { (key, label) ->
                                NavigationBarItem(
                                    selected = page == key,
                                    onClick = { page = key },
                                    icon = { Text(when (key) { "home" -> "⌂"; "cart" -> "🛒"; "orders" -> "▤"; else -> "♙" }, fontSize = 19.sp) },
                                    label = { Text(if (key == "cart" && count > 0) "$label ($count)" else label, fontSize = 10.sp) },
                                    colors = NavigationBarItemDefaults.colors(selectedIconColor = Red, selectedTextColor = Red, indicatorColor = Color(0xFFFFE8E7))
                                )
                            }
                        }
                    }
                ) { padding ->
                    Column(Modifier.fillMaxSize().padding(padding).background(Color.White)) {
                        when (page) {
                            "home" -> HomePage(category, { category = it }, cart, { page = "cart" }, { id -> cart[id] = (cart[id] ?: 0) + 1 })
                            "cart" -> CartPage(cart, total, onAdd = { id -> cart[id] = (cart[id] ?: 0) + 1 }, onRemove = { id ->
                                val n = (cart[id] ?: 0) - 1
                                if (n <= 0) cart.remove(id) else cart[id] = n
                            })
                            "orders" -> OrdersPage()
                            else -> ProfilePage(auth.currentUser?.displayName, auth.currentUser?.email, authStatus, { signInWithGoogle() }, { auth.signOut(); authStatus = "Hisobdan chiqdingiz" })
                        }
                    }
                }
            }
        }
    }

    private fun signInWithGoogle() {
        lifecycleScope.launch {
            try {
                val option = GetGoogleIdOption.Builder()
                    .setServerClientId(WEB_CLIENT_ID)
                    .setFilterByAuthorizedAccounts(false)
                    .setAutoSelectEnabled(false)
                    .build()
                val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
                val result = CredentialManager.create(this@MainActivity).getCredential(this@MainActivity, request)
                val credential = result.credential
                if (credential is CustomCredential && credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                    val token = GoogleIdTokenCredential.createFrom(credential.data).idToken
                    auth.signInWithCredential(GoogleAuthProvider.getCredential(token, null))
                        .addOnCompleteListener(this@MainActivity) { task ->
                            authStatus = if (task.isSuccessful) "Google hisobi ulandi" else "Kirish amalga oshmadi: ${task.exception?.localizedMessage ?: "xatolik"}"
                        }
                } else authStatus = "Google hisob ma’lumoti olinmadi"
            } catch (e: Exception) {
                authStatus = e.localizedMessage ?: "Google orqali kirishda xatolik"
            }
        }
    }
}

@Composable
private fun Header() {
    Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text("ALI KURYER", color = Red, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 2.sp)
            Text("Mazali taomlar, tez yetkazish", color = Ink, fontSize = 19.sp, fontWeight = FontWeight.Bold)
        }
        Box(Modifier.background(Red, RoundedCornerShape(12.dp)).padding(horizontal = 12.dp, vertical = 9.dp)) {
            Text("NAMANGAN", color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun HomePage(category: String, onCategory: (String) -> Unit, cart: Map<Int, Int>, goCart: () -> Unit, onAdd: (Int) -> Unit) {
    val categories = listOf("Barchasi", "Fast food", "Pizza", "Sushi", "Ichimlik")
    val visible = foods.filter { category == "Barchasi" || it.category == category }
    LazyColumn(Modifier.fillMaxSize()) {
        item { Header() }
        item {
            Column(Modifier.padding(horizontal = 18.dp).fillMaxWidth().background(Ink, RoundedCornerShape(22.dp)).padding(20.dp)) {
                Text("BUYURTMANGIZ", color = Color(0xFFFFB7B3), fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.5.sp)
                Text("Sevimli taomingiz\neshigingizgacha!", color = Color.White, fontSize = 25.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 31.sp)
                Spacer(Modifier.height(12.dp))
                Button(onClick = goCart, colors = ButtonDefaults.buttonColors(containerColor = Red), shape = RoundedCornerShape(12.dp)) {
                    Text("Savatni ko‘rish  →")
                }
            }
        }
        item { Text("Kategoriyalar", Modifier.padding(start = 20.dp, top = 22.dp, bottom = 10.dp), fontSize = 18.sp, fontWeight = FontWeight.Bold) }
        item {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                categories.forEach { item ->
                    FilterChip(selected = category == item, onClick = { onCategory(item) }, label = { Text(item, fontSize = 11.sp) }, colors = FilterChipDefaults.filterChipColors(selectedContainerColor = Red, selectedLabelColor = Color.White))
                }
            }
        }
        item { Text("Ommabop taomlar", Modifier.padding(start = 20.dp, top = 20.dp, bottom = 8.dp), fontSize = 18.sp, fontWeight = FontWeight.Bold) }
        items(visible) { food ->
            Row(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 6.dp).background(Soft, RoundedCornerShape(16.dp)).padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(66.dp).background(Color.White, RoundedCornerShape(14.dp)), contentAlignment = Alignment.Center) { Text(food.emoji, fontSize = 34.sp) }
                Column(Modifier.weight(1f).padding(start = 12.dp)) {
                    Text(food.name, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Text(food.note, color = Color.Gray, fontSize = 11.sp)
                    Text("${food.price} so‘m", color = Red, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                Button(onClick = { onAdd(food.id) }, contentPadding = PaddingValues(horizontal = 10.dp), shape = RoundedCornerShape(10.dp)) { Text("+") }
            }
        }
        item { Spacer(Modifier.height(20.dp)) }
    }
}

@Composable
private fun CartPage(cart: Map<Int, Int>, total: Int, onAdd: (Int) -> Unit, onRemove: (Int) -> Unit) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text("Savat", fontSize = 25.sp, fontWeight = FontWeight.ExtraBold)
        Spacer(Modifier.height(14.dp))
        if (cart.isEmpty()) {
            Text("Savatingiz hozircha bo‘sh.", color = Color.Gray)
            Text("Bosh sahifadan taom tanlang.", color = Color.Gray)
        } else {
            LazyColumn(Modifier.weight(1f)) {
                items(foods.filter { (cart[it.id] ?: 0) > 0 }) { food ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(food.emoji, fontSize = 28.sp)
                        Column(Modifier.weight(1f).padding(start = 10.dp)) {
                            Text(food.name, fontWeight = FontWeight.Bold)
                            Text("${food.price} so‘m", color = Red, fontSize = 12.sp)
                        }
                        TextButton(onClick = { onRemove(food.id) }) { Text("−") }
                        Text("${cart[food.id] ?: 0}", fontWeight = FontWeight.Bold)
                        TextButton(onClick = { onAdd(food.id) }) { Text("+") }
                    }
                }
            }
            Divider()
            Text("Jami: $total so‘m", Modifier.padding(vertical = 14.dp), fontSize = 20.sp, fontWeight = FontWeight.Bold)
            Text("Buyurtmani rasmiylashtirish server API ulangandan keyin yoqiladi.", color = Color.Gray, fontSize = 12.sp)
        }
    }
}

@Composable
private fun OrdersPage() {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text("Buyurtmalar", fontSize = 25.sp, fontWeight = FontWeight.ExtraBold)
        Spacer(Modifier.height(12.dp))
        Text("Hozircha buyurtmalar yo‘q.", color = Color.Gray)
        Text("Buyurtmalar tarixi server bilan ulanishdan so‘ng ko‘rinadi.", color = Color.Gray, fontSize = 12.sp)
    }
}

@Composable
private fun ProfilePage(name: String?, email: String?, status: String, signIn: () -> Unit, signOut: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Text("Profil", fontSize = 25.sp, fontWeight = FontWeight.ExtraBold)
        Spacer(Modifier.height(20.dp))
        Text(name ?: "Mehmon", fontSize = 18.sp, fontWeight = FontWeight.Bold)
        if (!email.isNullOrBlank()) Text(email, color = Color.Gray)
        Spacer(Modifier.height(16.dp))
        Button(onClick = if (email.isNullOrBlank()) signIn else signOut, colors = ButtonDefaults.buttonColors(containerColor = Red), modifier = Modifier.fillMaxWidth()) {
            Text(if (email.isNullOrBlank()) "Google orqali kirish" else "Hisobdan chiqish")
        }
        Text(status, Modifier.padding(top = 10.dp), color = Color.Gray, fontSize = 12.sp)
        Spacer(Modifier.height(22.dp))
        Text("Til: O‘zbekcha  •  Русский  •  中文", color = Color.Gray, fontSize = 13.sp)
    }
}
