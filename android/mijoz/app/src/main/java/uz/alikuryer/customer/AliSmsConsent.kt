package uz.alikuryer.customer

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import com.google.android.gms.auth.api.phone.SmsRetriever
import com.google.android.gms.common.api.CommonStatusCodes
import com.google.android.gms.common.api.Status

/**
 * A single SMS can be read ONLY when the user approves Android's consent dialog.
 * No READ_SMS or RECEIVE_SMS permissions; no access to inbox/history.
 * If Google Play Services is missing, manual OTP entry remains available.
 */
@Composable
internal fun AliSmsConsent(enabled: Boolean, requestNonce: Int, onCode: (String) -> Unit) {
    val context = LocalContext.current
    val latestOnCode = rememberUpdatedState(onCode)
    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val body = result.data?.getStringExtra(SmsRetriever.EXTRA_SMS_MESSAGE).orEmpty()
            // Ignore unrelated OTPs. The app only expects Ali Kuryer messages.
            if (body.contains("Ali Kuryer", ignoreCase = true)) {
                val code = Regex("""\b[0-9]{6}\b""").find(body)?.value
                if (code != null) latestOnCode.value(code)
            }
        }
    }

    DisposableEffect(enabled, requestNonce) {
        if (!enabled) {
            onDispose {}
        } else {
            val receiver = object : BroadcastReceiver() {
                override fun onReceive(receiverContext: Context, intent: Intent) {
                    if (intent.action != SmsRetriever.SMS_RETRIEVED_ACTION) return
                    val status = if (Build.VERSION.SDK_INT >= 33) {
                        intent.getParcelableExtra(SmsRetriever.EXTRA_STATUS, Status::class.java)
                    } else {
                        @Suppress("DEPRECATION")
                        intent.getParcelableExtra(SmsRetriever.EXTRA_STATUS) as? Status
                    }
                    if (status?.statusCode == CommonStatusCodes.SUCCESS) {
                        val consent = if (Build.VERSION.SDK_INT >= 33) {
                            intent.getParcelableExtra(
                                SmsRetriever.EXTRA_CONSENT_INTENT, Intent::class.java)
                        } else {
                            @Suppress("DEPRECATION")
                            intent.getParcelableExtra(SmsRetriever.EXTRA_CONSENT_INTENT) as? Intent
                        }
                        if (consent != null) launcher.launch(consent)
                    }
                }
            }
            val filter = IntentFilter(SmsRetriever.SMS_RETRIEVED_ACTION)
            ContextCompat.registerReceiver(
                context, receiver, filter, SmsRetriever.SEND_PERMISSION,
                null, ContextCompat.RECEIVER_EXPORTED
            )
            SmsRetriever.getClient(context).startSmsUserConsent(null)
            onDispose {
                try { context.unregisterReceiver(receiver) }
                catch (_: IllegalArgumentException) { }
            }
        }
    }
}
