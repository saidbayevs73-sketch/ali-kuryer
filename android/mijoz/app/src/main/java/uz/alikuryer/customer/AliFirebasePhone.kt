package uz.alikuryer.customer

import android.app.Activity
import android.content.Context
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.firebase.FirebaseException
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthInvalidCredentialsException
import com.google.firebase.auth.PhoneAuthCredential
import com.google.firebase.auth.PhoneAuthOptions
import com.google.firebase.auth.PhoneAuthProvider
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Firebase config is customer-flavor only (not a service-account key).
 * Firebase verifies the SMS and returns a signed ID token. The Ali Kuryer
 * backend must independently verify that signed token before signing in.
 */
private object AliFirebasePhone {
    fun auth(context: Context): FirebaseAuth {
        check(BuildConfig.APP_ROLE == "customer") { "Firebase SMS only for customer app" }
        val name = "ali-kuryer-customer"
        val app = FirebaseApp.getApps(context).firstOrNull { it.name == name }
            ?: run {
                val settings = context.assets.open("google-services.json")
                    .bufferedReader().use { JSONObject(it.readText()) }
                val project = settings.getJSONObject("project_info")
                val client = settings.getJSONArray("client").getJSONObject(0)
                val android = client.getJSONObject("client_info")
                    .getJSONObject("android_client_info")
                require(android.getString("package_name") == context.packageName) {
                    "Firebase paket nomi mos emas"
                }
                val options = FirebaseOptions.Builder()
                    .setProjectId(project.getString("project_id"))
                    .setApplicationId(client.getJSONObject("client_info")
                        .getString("mobilesdk_app_id"))
                    .setApiKey(client.getJSONArray("api_key")
                        .getJSONObject(0).getString("current_key"))
                    .build()
                FirebaseApp.initializeApp(context, options, name)
            }
        return FirebaseAuth.getInstance(app)
    }
}

@Composable
internal fun AliFirebasePhonePanel(
    phone: String,
    onPhoneChange: (String) -> Unit,
    onTokenVerified: (String) -> Unit
) {
    val context = LocalContext.current
    val activity = context as? Activity
    val lastOnVerified by rememberUpdatedState(onTokenVerified)
    var code by remember { mutableStateOf("") }
    var verificationId by remember { mutableStateOf("") }
    var isBusy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    var info by remember { mutableStateOf("") }

    // One verification operation is sufficient. No SMS inbox permission needed.
    fun finishSignIn(credential: PhoneAuthCredential) {
        val auth = runCatching { AliFirebasePhone.auth(context) }.getOrElse {
            error = "Firebase sozlanmagan. Ilovani yangilang."
            isBusy = false
            return
        }
        auth.signInWithCredential(credential).addOnCompleteListener { signIn ->
            if (!signIn.isSuccessful) {
                error = "SMS kodi noto‘g‘ri yoki uning muddati tugagan"
                isBusy = false
                return@addOnCompleteListener
            }
            auth.currentUser?.getIdToken(true)?.addOnCompleteListener { result ->
                isBusy = false
                val signedIdToken = result.result?.token.takeIf {
                    result.isSuccessful && !it.isNullOrBlank()
                }
                if (signedIdToken != null) lastOnVerified(signedIdToken)
                else error = "Firebase ID tokenini olishning imkoni bo‘lmadi"
            } ?: run {
                error = "Firebase hisobini ochib bo‘lmadi"
                isBusy = false
            }
        }
    }

    Surface(
        color = androidx.compose.ui.graphics.Color.White,
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(
            Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("Google Firebase SMS tasdiqlash",
                fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
            Text(
                "Telefon raqamingiz tasdiqlash va firibgarlikni cheklash uchun " +
                    "Google Firebase xizmatiga yuboriladi. SMS uchun to‘lov bo‘lishi mumkin.",
                color = AliMuted, fontSize = 12.sp
            )
            OutlinedTextField(
                phone, onPhoneChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("Telefon: +998XXXXXXXXX") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone)
            )
            Button(
                enabled = !isBusy,
                onClick = {
                    if (!Regex("^\\+998[0-9]{9}$").matches(phone)) {
                        error = "Telefonni +998XXXXXXXXX shaklida kiriting"
                    } else if (activity == null) {
                        error = "Firebase SMS uchun Android oynasi ochilmadi"
                    } else {
                        isBusy = true
                        error = ""
                        info = "Firebase orqali SMS so‘ralmoqda..."
                        val auth = runCatching { AliFirebasePhone.auth(context) }.getOrElse {
                            error = "Firebase sozlamalari topilmadi"
                            isBusy = false
                            return@Button
                        }
                        val callbacks = object :
                            PhoneAuthProvider.OnVerificationStateChangedCallbacks() {
                            override fun onVerificationCompleted(credential: PhoneAuthCredential) {
                                info = "Telefon avtomatik tasdiqlandi"
                                finishSignIn(credential)
                            }

                            override fun onVerificationFailed(exception: FirebaseException) {
                                // Never show internal tokens or user secrets.
                                error = when (exception) {
                                    is FirebaseAuthInvalidCredentialsException ->
                                        "Raqam yoki Firebase ilova sozlamasi noto‘g‘ri"
                                    else -> "SMS yuborilmadi. Phone Authentication, " +
                                        "SMS mintaqasi va SHA sertifikatlarini tekshiring."
                                }
                                isBusy = false
                            }

                            override fun onCodeSent(
                                id: String,
                                resendToken: PhoneAuthProvider.ForceResendingToken
                            ) {
                                verificationId = id
                                info = "6 xonali kodni SMS orqali qabul qilib, quyiga kiriting."
                                isBusy = false
                            }
                        }
                        try {
                            PhoneAuthProvider.verifyPhoneNumber(
                                PhoneAuthOptions.newBuilder(auth)
                                    .setPhoneNumber(phone)
                                    .setTimeout(60L, TimeUnit.SECONDS)
                                    .setActivity(activity)
                                    .setCallbacks(callbacks)
                                    .build()
                            )
                        } catch (_: Exception) {
                            error = "Firebase SMS yuborishni boshlay olmadi"
                            isBusy = false
                        }
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = AliRed),
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp)
            ) {
                Icon(Icons.Default.PhoneAndroid, null)
                Spacer(Modifier.width(8.dp))
                Text(if (isBusy) "Kuting..." else "Firebase orqali SMS-kod olish")
            }
            if (verificationId.isNotBlank()) {
                OutlinedTextField(
                    code,
                    { code = it.filter(Char::isDigit).take(6) },
                    label = { Text("6 xonali SMS kodi") },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                    singleLine = true
                )
                Button(
                    enabled = !isBusy && code.length == 6,
                    onClick = {
                        isBusy = true
                        error = ""
                        finishSignIn(PhoneAuthProvider.getCredential(verificationId, code))
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                ) { Text("Telefonni tasdiqlash") }
            }
            if (info.isNotBlank()) Text(info, color = AliMuted, fontSize = 12.sp)
            if (error.isNotBlank()) Text(error, color = AliRed, fontSize = 12.sp)
        }
    }
}
