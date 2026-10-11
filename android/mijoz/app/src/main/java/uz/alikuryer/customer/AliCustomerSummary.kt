package uz.alikuryer.customer

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.util.Locale

/**
 * Real customer history and informational bonus balance from authenticated API.
 * Bonus points are NOT money; cash wallet is intentionally disabled.
 */
@Composable
internal fun AliCustomerSummary(token: String) {
    val scope = rememberCoroutineScope()
    var summary by remember(token) { mutableStateOf<JSONObject?>(null) }
    var loading by remember(token) { mutableStateOf(true) }
    var error by remember(token) { mutableStateOf("") }

    suspend fun refresh() {
        loading = true
        try {
            summary = AliApi.customerSummary(token)
            error = ""
        } catch (ex: Exception) {
            error = ex.message ?: "Mijoz ma’lumotlari yuklanmadi"
        } finally {
            loading = false
        }
    }

    LaunchedEffect(token) { refresh() }

    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Surface(color = Color(0xFFFFEDF1), shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.fillMaxWidth().padding(17.dp)) {
                Text("BONUS BALANS", color = Color(0xFFAA1739),
                    fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(6.dp))
                val points = summary?.optJSONObject("bonus")?.optInt("points", 0) ?: 0
                Text("$points ball", color = Color(0xFFEB1737),
                    fontSize = 28.sp, fontWeight = FontWeight.Black)
                Text("Yetkazilgan har 10 000 so‘mlik xaridga 1 bonus ball. Hozircha ballni pulga aylantirish va sarflash yoqilmagan.",
                    color = Color(0xFF77545E), fontSize = 12.sp, lineHeight = 17.sp)
            }
        }

        Surface(color = Color.White, shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.fillMaxWidth().padding(17.dp)) {
                Text("Hamyon / Pul balansi", fontWeight = FontWeight.Bold,
                    fontSize = 17.sp, color = AliBlack)
                Spacer(Modifier.height(7.dp))
                Text("Haqiqiy pul hamyoni hali ulanmagan. Bank kartasi yoki depozit mavjud deb ko‘rsatilmaydi.",
                    fontSize = 12.sp, color = AliMuted)
            }
        }
        Surface(color = Color.White, shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.fillMaxWidth().padding(17.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Buyurtmalar tarixi", fontSize = 17.sp,
                        fontWeight = FontWeight.ExtraBold, color = AliBlack)
                    TextButton(onClick = { scope.launch { refresh() } }) {
                        Text("Yangilash", color = AliRed)
                    }
                }
                if (loading) LinearProgressIndicator(
                    Modifier.fillMaxWidth(), color = AliRed
                )
                if (error.isNotBlank()) Text(
                    error, color = Color(0xFFBD2536), fontSize = 12.sp
                )
                val history = summary?.optJSONArray("history")
                if (!loading && history != null && history.length() == 0) {
                    Text("Sizda hali buyurtmalar yo‘q.", fontSize = 13.sp, color = AliMuted)
                }
                if (history != null) {
                    for (index in 0 until minOf(history.length(), 5)) {
                        val order = history.optJSONObject(index) ?: continue
                        val id = order.optInt("id")
                        val amount = order.optDouble("total", 0.0).toLong()
                        val status = when (order.optString("status")) {
                            "pending" -> "Qabul qilindi"
                            "preparing" -> "Tayyorlanmoqda"
                            "ready" -> "Tayyor"
                            "assigned", "delivering" -> "Yo‘lda"
                            "delivered" -> "Yetkazildi"
                            "cancelled" -> "Bekor qilindi"
                            else -> "Tekshirilmoqda"
                        }
                        HorizontalDivider(color = Color(0xFFF1F0F0))
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 11.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text("Buyurtma #$id", fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold, color = AliBlack)
                                Text(status, fontSize = 11.sp, color = AliMuted)
                            }
                            Text(priceText(amount), fontSize = 12.sp,
                                fontWeight = FontWeight.Bold, color = AliRed)
                        }
                    }
                }
            }
        }
    }
}
