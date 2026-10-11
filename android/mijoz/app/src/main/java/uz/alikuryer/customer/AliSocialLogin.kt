package uz.alikuryer.customer

import android.app.Activity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import kotlinx.coroutines.launch

/**
 * Two real identity providers only: Google ID token validated on the server,
 * or Telegram OIDC/PKCE validated on the server.
 * No fake local login, SMS, password or self-asserted verification.
 */
@Composable
internal fun AliSocialLogin(
    onAuthorized: (Session, String, String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    val webClientId = BuildConfig.GOOGLE_WEB_CLIENT_ID

    val googleLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode != Activity.RESULT_OK || result.data == null) {
            busy = false
            return@rememberLauncherForActivityResult
        }
        try {
            val account = GoogleSignIn.getSignedInAccountFromIntent(result.data)
                .getResult(ApiException::class.java)
            val token = account.idToken
            if (token.isNullOrBlank()) {
                error = "Google token olinmadi. Ilova Google sozlamalarini tekshiring."
                busy = false
            } else {
                scope.launch {
                    try {
                        val session = AliApi.googleLogin(token)
                        onAuthorized(session, account.displayName.orEmpty(), "")
                    } catch (e: Exception) {
                        error = e.message ?: "Google orqali kirishda xatolik"
                    } finally {
                        busy = false
                    }
                }
            }
        } catch (e: Exception) {
            error = "Google orqali kirish yakunlanmadi: " + (e.message ?: "")
            busy = false
        }
    }

    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Box(
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(26.dp))
                .background(Brush.linearGradient(listOf(
                    Color(0xFFB9001F), Color(0xFFEC1733), Color(0xFFFF5866)
                )))
                .padding(23.dp)
        ) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                AliMark(size = 82)
                Spacer(Modifier.height(13.dp))
                Text("ALI KURYER", color = Color.White, fontSize = 27.sp,
                    fontWeight = FontWeight.Black, letterSpacing = 1.1.sp)
                Text("Siz tanlaysiz. Biz yetkazamiz!", color = Color.White.copy(alpha = .9f),
                    fontSize = 13.sp, textAlign = TextAlign.Center)
                Spacer(Modifier.height(15.dp))
                Text("Qulay, tez va xavfsiz kirish", color = Color.White,
                    fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }
        }

        Surface(shape = RoundedCornerShape(23.dp), color = Color.White) {
            Column(Modifier.fillMaxWidth().padding(18.dp),
                verticalArrangement = Arrangement.spacedBy(11.dp)) {
                Text("Hisobga kirish", color = Color(0xFF19202D),
                    fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                Text("Google hisobingizni tanlang yoki Telegram orqali kiring.",
                    color = Color(0xFF747C88), fontSize = 12.sp)

                Button(
                    onClick = {
                        if (webClientId.isBlank()) {
                            error = "Google kirish uchun GOOGLE_WEB_CLIENT_ID sozlang."
                            return@Button
                        }
                        try {
                            error = ""
                            busy = true
                            val options = GoogleSignInOptions.Builder(
                                GoogleSignInOptions.DEFAULT_SIGN_IN
                            ).requestIdToken(webClientId).requestEmail().build()
                            val intent = GoogleSignIn.getClient(context, options).signInIntent
                            googleLauncher.launch(intent)
                        } catch (e: Exception) {
                            busy = false
                            error = e.message ?: "Google oynasi ochilmadi"
                        }
                    },
                    enabled = !busy,
                    shape = RoundedCornerShape(17.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFEC1733), contentColor = Color.White
                    ),
                    modifier = Modifier.fillMaxWidth().height(56.dp)
                ) {
                    Text("G", fontSize = 23.sp, fontWeight = FontWeight.Black)
                    Spacer(Modifier.width(12.dp))
                    Text("Google orqali kirish", fontWeight = FontWeight.Bold)
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    HorizontalDivider(Modifier.weight(1f), color = Color(0xFFE8E8E8))
                    Text("  yoki  ", color = Color.Gray, fontSize = 12.sp)
                    HorizontalDivider(Modifier.weight(1f), color = Color(0xFFE8E8E8))
                }

                AliTelegramLoginPanel { result ->
                    onAuthorized(result.session, "", result.phone)
                }
                if (busy) LinearProgressIndicator(Modifier.fillMaxWidth(), color = Color(0xFFEC1733))
                if (error.isNotBlank()) {
                    Text(error, color = Color(0xFFC62828), fontSize = 12.sp)
                }
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.VerifiedUser, null, tint = Color(0xFF139A65))
            Spacer(Modifier.width(8.dp))
            Text("SMS-kod va parol talab qilinmaydi.",
                color = Color(0xFF576071), fontSize = 12.sp)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.CheckCircle, null, tint = Color(0xFF139A65))
            Spacer(Modifier.width(8.dp))
            Text("Kirgach, ism, familiya va telefon raqamingizni kiriting.",
                color = Color(0xFF576071), fontSize = 12.sp)
        }
    }
}
