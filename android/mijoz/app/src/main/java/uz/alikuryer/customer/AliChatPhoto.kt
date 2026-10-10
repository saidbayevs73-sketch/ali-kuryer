package uz.alikuryer.customer

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.util.Base64
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Resize locally and strip metadata before posting a photo to the AI API.
 * No file is written to Android app storage or sent to the order database.
 */
internal object AliChatPhoto {
    suspend fun encode(context: Context, uri: Uri): String = withContext(Dispatchers.IO) {
        val mime = context.contentResolver.getType(uri)
        if (mime !in listOf("image/jpeg", "image/png", "image/webp")) {
            throw IllegalStateException("Faqat JPEG, PNG yoki WEBP rasm yuboring.")
        }
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, bounds)
        } ?: throw IllegalStateException("Rasm ochilmadi.")
        val w = bounds.outWidth
        val h = bounds.outHeight
        if (w < 16 || h < 16 || w.toLong() * h.toLong() > 32_000_000L) {
            throw IllegalStateException("Rasm o‘lchami mos emas.")
        }
        var sample = 1
        while (w / sample > 1280 || h / sample > 1280) sample *= 2
        val opts = BitmapFactory.Options().apply { inSampleSize = sample }
        val bitmap = context.contentResolver.openInputStream(uri)?.use {
            BitmapFactory.decodeStream(it, null, opts)
        } ?: throw IllegalStateException("Rasmni o‘qib bo‘lmadi.")
        try {
            val buffer = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 77, buffer)
            if (buffer.size() > 4_000_000) {
                throw IllegalStateException("Rasm hajmi 4 MB dan oshmasligi kerak.")
            }
            Base64.encodeToString(buffer.toByteArray(), Base64.NO_WRAP)
        } finally {
            bitmap.recycle()
        }
    }
}
