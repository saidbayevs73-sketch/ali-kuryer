package uz.alikuryer.customer

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.util.Base64
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import java.security.SecureRandom

/**
 * Telegram OIDC uses the system browser and a one-use callback ticket.
 * A 256-bit random device secret is never sent in a callback link; only
 * the app process and the backend know it.
 */
internal object AliTelegramBridge {
    var ticket by mutableStateOf("")
    var deviceSecret: String? = null

    fun handle(intent: Intent?) {
        val uri = intent?.data ?: return
        if (uri.scheme == "alikuryer" && uri.host == "telegram-login") {
            val value = uri.getQueryParameter("ticket").orEmpty()
            if (Regex("^[A-Za-z0-9_-]{43}$").matches(value)) {
                ticket = value
            }
        }
    }

    fun newDeviceSecret(): String {
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        val key = Base64.encodeToString(bytes, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
        deviceSecret = key
        ticket = ""
        return key
    }

    fun clear() {
        deviceSecret = null
        ticket = ""
    }
}

@Composable
internal fun AliTelegramLoginPanel(
    onAuthorized: (TelegramSession) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val latestAuthorization by rememberUpdatedState(onAuthorized)
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    var info by remember { mutableStateOf("") }
    var statusChecked by remember { mutableStateOf(false) }
    var telegramReady by remember { mutableStateOf(false) }
    val ticket = AliTelegramBridge.ticket

    LaunchedEffect(Unit) {
        telegramReady = try { AliApi.telegramAvailable() } catch (_: Exception) { false }
        statusChecked = true
    }

    LaunchedEffect(ticket) {
        if (ticket.isBlank()) return@LaunchedEffect
        val deviceSecret = AliTelegramBridge.deviceSecret
        if (deviceSecret.isNullOrBlank()) {
            error = "Telegram tasdiqlash oynasi qayta ochilishi kerak. Yana bosing."
            AliTelegramBridge.clear()
            return@LaunchedEffect
        }
        busy = true
        error = ""
        try {
            val result = AliApi.telegramFinish(ticket, deviceSecret)
            latestAuthorization(result)
            info = "Telegram orqali xavfsiz kirdingiz."
        } catch (e: Exception) {
            error = e.message ?: "Telegram orqali kirishni yakunlab bo‘lmadi"
        } finally {
            AliTelegramBridge.clear()
            busy = false
        }
    }

    Surface(color = AliSurface,
        shape = RoundedCornerShape(17.dp)) {
        Column(Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Telegram orqali oson kirish", color = AliBlack,
                fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
            Text(
                if (telegramReady) {
                    "Telegram hisobingizni tasdiqlang va telefon raqamingizni ulashishga rozilik bering."
                } else {
                    "Telegram orqali kirish serverda hali to‘liq sozlanmagan. " +
                    "Ro‘yxatdan o‘tish uchun pastdagi SMS tasdiqlashni tanlang. " +
                    "Sizga ishlamaydigan tugmani bosishni taklif qilmaymiz."
                },
                color = AliMuted, fontSize = 12.sp
            )
            Button(
                onClick = {
                    scope.launch {
                        busy = true
                        error = ""
                        info = "Telegram ochilmoqda..."
                        try {
                            val secret = AliTelegramBridge.newDeviceSecret()
                            val url = AliApi.telegramStart(secret)
                            // Only open Telegram's official HTTPS authorization URL.
                            if (!url.startsWith("https://oauth.telegram.org/auth?")) {
                                error("Telegram avtorizatsiya manzili noto‘g‘ri")
                            }
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                            info = "Tasdiqlang va telefon raqamingizni ulashing. " +
                                "So‘ng ilovaga avtomatik qaytasiz."
                        } catch (e: Exception) {
                            AliTelegramBridge.clear()
                            info = ""
                            val reason = e.message.orEmpty()
                            error = when {
                                reason.contains("PostgreSQL", ignoreCase = true) ||
                                    reason.contains("baza", ignoreCase = true) ->
                                    "Hisobga kirish serveri sozlanmoqda. Birozdan keyin yana urinib ko‘ring."
                                reason.contains("so zlanmagan", ignoreCase = true) ||
                                    reason.contains("sozlanmagan", ignoreCase = true) ->
                                    "Telegram orqali kirish xizmati hali faollashtirilmagan."
                                else -> reason.ifBlank { "Telegram kirishni ochib bo‘lmadi." }
                            }
                        } finally { busy = false }
                    }
                },
                enabled = !busy && statusChecked && telegramReady,
                colors = ButtonDefaults.buttonColors(containerColor = AliRed),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth().height(52.dp)
            ) {
                Icon(Icons.Default.Send, null)
                Spacer(Modifier.width(9.dp))
                Text(
                    when {
                        !statusChecked -> "Telegram xizmati tekshirilmoqda..."
                        !telegramReady -> "Telegram kirish hozircha mavjud emas"
                        busy -> "Kuting..."
                        else -> "Telegram orqali kirish"
                    },
                    fontWeight = FontWeight.Bold
                )
            }
            if (info.isNotBlank()) Text(info, color = AliMuted, fontSize = 12.sp)
            if (error.isNotBlank()) Text(error, color = AliRed, fontSize = 12.sp)
        }
    }
}
