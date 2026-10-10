package uz.alikuryer.customer

import android.content.Intent
import android.net.Uri
import android.webkit.WebView
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.viewinterop.AndroidView
import java.util.Locale

private fun statusTitle(status: String): String = when (status) {
    "pending" -> "Qabul qilindi"
    "preparing" -> "Oshxonada tayyorlanmoqda"
    "ready" -> "Kuryer kutilmoqda"
    "assigned" -> "Kuryer biriktirildi"
    "delivering" -> "Yo‘lda"
    "delivered" -> "Yetkazildi"
    "cancelled" -> "Bekor qilindi"
    else -> status
}

@Composable
internal fun AliOrdersScreen(
    orders: List<AliOrder>, loggedIn: Boolean,
    onLogin: () -> Unit, onOpen: (AliOrder) -> Unit, onRefresh: () -> Unit
) {
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
        item {
            AliSectionTitle("Buyurtmalarim", "Buyurtmalar holatini kuzating",
                "Yangilash", onRefresh)
        }
        if (!loggedIn) item {
            AliEmptyState("🔐", "Hisobga kiring", "Buyurtmalarni ko‘rish uchun tizimga kiring.",
                "Kirish", onLogin)
        } else if (orders.isEmpty()) item {
            AliEmptyState("📦", "Buyurtmalar hali yo‘q",
                "Yangi buyurtma berilgach uning holati shu yerda ko‘rinadi.")
        }
        items(orders, key = { it.id }) { order ->
            Surface(
                onClick = { onOpen(order) },
                shape = RoundedCornerShape(18.dp), color = AliSurface,
                border = BorderStroke(1.dp, AliBorder)
            ) {
                Column(Modifier.fillMaxWidth().padding(16.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Buyurtma №${order.id}", fontWeight = FontWeight.ExtraBold,
                            modifier = Modifier.weight(1f))
                        Text(statusTitle(order.status), fontWeight = FontWeight.Bold,
                            fontSize = 12.sp, color = AliRed)
                    }
                    Spacer(Modifier.height(6.dp))
                    Text(order.address, fontSize = 13.sp, color = AliMuted)
                    Spacer(Modifier.height(11.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(priceText(order.total), fontWeight = FontWeight.Bold,
                            color = AliBlack, modifier = Modifier.weight(1f))
                        Text("Kuzatish  →", color = AliRed, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
internal fun AliOrderTracker(
    order: AliOrder?, onRefresh: () -> Unit,
    onSupport: () -> Unit, onOrderChat: () -> Unit
) {
    val context = LocalContext.current
    var showMap by remember { mutableStateOf(false) }
    LazyColumn(contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(13.dp)) {
        item {
            AliSectionTitle("Buyurtmani kuzatish",
                order?.let { "№${it.id}" } ?: "Holati yuklanmoqda",
                "Yangilash", onRefresh)
        }
        if (order == null) item {
            AliEmptyState("📦", "Buyurtma yuklanmoqda", "Internet ulanishini tekshiring.")
        } else {
            item {
                Surface(color = AliSurface, shape = RoundedCornerShape(21.dp)) {
                    Column(Modifier.fillMaxWidth().padding(19.dp)) {
                        Text("HOZIRGI HOLAT", fontWeight = FontWeight.Bold,
                            fontSize = 11.sp, color = AliMuted)
                        Spacer(Modifier.height(7.dp))
                        Text(statusTitle(order.status),
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 23.sp, color = AliBlack)
                        Spacer(Modifier.height(12.dp))
                        Text("Taomlar jami: ${priceText(order.total)}", fontSize = 15.sp)
                        Text(order.address, color = AliMuted, fontSize = 12.sp)
                    }
                }
            }
            if (order.courierName != null) item {
                Surface(color = AliSurface, shape = RoundedCornerShape(19.dp)) {
                    Column(Modifier.fillMaxWidth().padding(16.dp)) {
                        Text("Sizning kuryeringiz", fontWeight = FontWeight.Bold,
                            fontSize = 16.sp)
                        Spacer(Modifier.height(7.dp))
                        Text(order.courierName, color = AliBlack, fontWeight = FontWeight.SemiBold)
                        order.courierPhone?.let { number ->
                            Spacer(Modifier.height(8.dp))
                            OutlinedButton(onClick = {
                                context.startActivity(Intent(Intent.ACTION_DIAL,
                                    Uri.parse("tel:${Uri.encode(number)}")))
                            }) {
                                Icon(Icons.Default.Phone, null, tint = AliRed)
                                Spacer(Modifier.width(6.dp))
                                Text(number)
                            }
                        }
                    }
                }
            }
            item {
                if (order.courierLat != null && order.courierLng != null) {
                    val lat = order.courierLat
                    val lng = order.courierLng
                    val bbox = "${lng-0.008}%2C${lat-0.006}%2C${lng+0.008}%2C${lat+0.006}"
                    val url = "https://www.openstreetmap.org/export/embed.html?bbox=$bbox&layer=mapnik&marker=$lat%2C$lng"
                    Surface(color = AliSurface, shape = RoundedCornerShape(18.dp)) {
                        Column(Modifier.padding(14.dp)) {
                            Text("Kuryerning so‘nggi joylashuvi", fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(5.dp))
                            Text("Xarita ko‘rsatish uchun joylashuv OpenStreetMap'ga yuboriladi. " +
                                "Nuqta kuryer telefondan joylashuv yuborganida yangilanadi.",
                                fontSize = 11.sp, color = AliMuted)
                            Spacer(Modifier.height(9.dp))
                            Button(onClick = { showMap = !showMap },
                                colors = ButtonDefaults.buttonColors(containerColor = AliRed),
                                shape = RoundedCornerShape(13.dp)) {
                                Icon(Icons.Default.Map, null)
                                Spacer(Modifier.width(6.dp))
                                Text(if (showMap) "Xaritani yopish" else "Jonli xaritani ko‘rish")
                            }
                            if (showMap) {
                                Spacer(Modifier.height(10.dp))
                                AndroidView(
                                    modifier = Modifier.fillMaxWidth().height(260.dp),
                                    factory = { ctx ->
                                        WebView(ctx).apply {
                                            settings.javaScriptEnabled = true
                                            settings.domStorageEnabled = false
                                            loadUrl(url)
                                        }
                                    },
                                    update = { view -> if (view.url != url) view.loadUrl(url) }
                                )
                            }
                        }
                    }
                } else {
                    Surface(color = AliSurface, shape = RoundedCornerShape(18.dp)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp)) {
                            Text("📍 Jonli xarita", fontWeight = FontWeight.Bold)
                            Spacer(Modifier.height(6.dp))
                            Text("Kuryer biriktirilib, joylashuvini ulashgach " +
                                "uning harakatini shu yerda ko‘rasiz.",
                                color = AliMuted, fontSize = 12.sp)
                        }
                    }
                }
            }
            item {
                Button(onClick = onOrderChat, modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)) {
                    Icon(Icons.Default.Chat, null)
                    Spacer(Modifier.width(8.dp))
                    Text("Buyurtma bo‘yicha chat")
                }
                Spacer(Modifier.height(8.dp))
                OutlinedButton(onClick = onSupport, modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp)) {
                    Text("Operator bilan bog‘lanish", color = AliRed)
                }
            }
        }
    }
}

@Composable
internal fun AliConversationScreen(
    title: String,
    note: String,
    messages: List<AliChatMessage>,
    text: String, onText: (String) -> Unit,
    onSend: () -> Unit, onRefresh: () -> Unit
) {
    Column(Modifier.fillMaxSize().padding(15.dp)) {
        AliSectionTitle(title, note, "Yangilash", onRefresh)
        Spacer(Modifier.height(10.dp))
        Surface(color = Color(0xFFFFF1E6), shape = RoundedCornerShape(12.dp)) {
            Text("Xizmat sifatini nazorat qilish uchun buyurtma va operator yozishmalari " +
                "vakolatli administrator tomonidan ko‘rilishi mumkin.",
                modifier = Modifier.fillMaxWidth().padding(10.dp),
                fontSize = 11.sp, color = Color(0xFF17171B))
        }
        Spacer(Modifier.height(12.dp))
        LazyColumn(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            if (messages.isEmpty()) item {
                AliEmptyState("💬", "Suhbatni boshlang",
                    "Operator yoki buyurtma ishtirokchilariga xabar yozing.")
            }
            items(messages, key = { it.id }) { message ->
                Surface(color = AliSurface, shape = RoundedCornerShape(15.dp),
                    border = BorderStroke(1.dp, AliBorder)) {
                    Column(Modifier.fillMaxWidth().padding(12.dp)) {
                        Text(message.senderName, color = AliRed,
                            fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(4.dp))
                        Text(message.body, fontSize = 14.sp, color = AliBlack)
                    }
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(text, onText, modifier = Modifier.weight(1f),
                maxLines = 3, placeholder = { Text("Xabar yozing...") },
                shape = RoundedCornerShape(17.dp))
            Spacer(Modifier.width(8.dp))
            FilledIconButton(onClick = onSend, enabled = text.trim().isNotEmpty(),
                colors = IconButtonDefaults.filledIconButtonColors(containerColor = AliRed),
                modifier = Modifier.size(51.dp)) {
                Icon(Icons.Default.Send, "Yuborish")
            }
        }
    }
}
