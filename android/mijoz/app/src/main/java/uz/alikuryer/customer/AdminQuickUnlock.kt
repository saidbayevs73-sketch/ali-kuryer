package uz.alikuryer.customer

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Optional password-free *repeat* unlock for an already authenticated admin.
 *
 * The admin JWT is encrypted under an Android Keystore AES key which cannot be
 * used until the device owner authenticates using biometric or screen lock.
 * No admin password is saved. This cannot provision/reset an admin account.
 */
internal object AdminQuickUnlock {
    private const val PREFS = "ali_admin_secure"
    private const val KEY_ALIAS = "ali_kuryer_admin_token_v1"
    private const val CIPHER_TEXT = "token_ciphertext"
    private const val IV = "token_iv"

    fun hasSaved(ctx: Context): Boolean {
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.contains(CIPHER_TEXT) && prefs.contains(IV)
    }

    fun isAvailable(activity: FragmentActivity): Boolean =
        BiometricManager.from(activity).canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG or
                BiometricManager.Authenticators.DEVICE_CREDENTIAL
        ) == BiometricManager.BIOMETRIC_SUCCESS

    fun authenticate(activity: FragmentActivity, onSuccess: () -> Unit,
                     onError: (String) -> Unit) {
        if (!isAvailable(activity)) {
            onError("Telefoningizda ekran qulfi yoki barmoq izi yoqilmagan")
            return
        }
        val prompt = BiometricPrompt(
            activity, ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(
                    result: BiometricPrompt.AuthenticationResult
                ) {
                    onSuccess()
                }
                override fun onAuthenticationError(code: Int, errString: CharSequence) {
                    if (code != BiometricPrompt.ERROR_USER_CANCELED &&
                        code != BiometricPrompt.ERROR_NEGATIVE_BUTTON &&
                        code != BiometricPrompt.ERROR_CANCELED) {
                        onError(errString.toString())
                    }
                }
            }
        )
        prompt.authenticate(
            BiometricPrompt.PromptInfo.Builder()
                .setTitle("Ali Kuryer Admin")
                .setSubtitle("Telefon egasini tasdiqlang")
                .setAllowedAuthenticators(
                    BiometricManager.Authenticators.BIOMETRIC_STRONG or
                        BiometricManager.Authenticators.DEVICE_CREDENTIAL
                )
                .build()
        )
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val old = store.getKey(KEY_ALIAS, null) as? SecretKey
        if (old != null) return old
        val generator = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore"
        )
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setUserAuthenticationRequired(true)
                // Authentication is required for *each* quick-unlock operation.
                // The short window only permits encryption/decryption after
                // the explicit system authentication prompt.
                .setUserAuthenticationValidityDurationSeconds(30)
                .build()
        )
        return generator.generateKey()
    }

    fun save(ctx: Context, adminToken: String) {
        require(adminToken.isNotBlank())
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(adminToken.toByteArray(Charsets.UTF_8))
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(CIPHER_TEXT, Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .putString(IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .apply()
    }

    fun read(ctx: Context): String? {
        val prefs = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val text = prefs.getString(CIPHER_TEXT, null) ?: return null
        val iv = prefs.getString(IV, null) ?: return null
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(),
            GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
        return String(
            cipher.doFinal(Base64.decode(text, Base64.NO_WRAP)), Charsets.UTF_8
        )
    }

    fun clear(ctx: Context) {
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit().remove(CIPHER_TEXT).remove(IV).apply()
    }
}
