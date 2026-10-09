package uz.alikuryer.customer

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class Restaurant(
    val id: Int,
    val name: String,
    val address: String,
    val logoUrl: String? = null
)
data class Food(
    val id: Int,
    val name: String,
    val price: Long,
    val imageUrl: String? = null,
    val category: String = ""
)
data class FoodHit(val restaurant: Restaurant, val food: Food)
data class Session(val token: String, val role: String)

object AliApi {
    private const val BASE = BuildConfig.API_BASE_URL

    private suspend fun request(method: String, path: String, body: JSONObject? = null): String =
        withContext(Dispatchers.IO) {
            val conn = URL(BASE.trimEnd('/') + path).openConnection() as HttpURLConnection
            try {
                conn.requestMethod = method
                conn.connectTimeout = 15000
                conn.readTimeout = 20000
                conn.setRequestProperty("Accept", "application/json")
                if (body != null) {
                    conn.doOutput = true
                    conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    conn.outputStream.use { out ->
                        out.write(body.toString().toByteArray(Charsets.UTF_8))
                    }
                }
                val status = conn.responseCode
                val response = (if (status in 200..299) conn.inputStream else conn.errorStream)
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (status !in 200..299) {
                    val detail = runCatching {
                        JSONObject(response).optString("detail")
                    }.getOrDefault("")
                    throw IllegalStateException(detail.ifBlank { "Server xatosi: " + status })
                }
                response
            } finally {
                conn.disconnect()
            }
        }

    suspend fun restaurants(): List<Restaurant> {
        val arr = JSONArray(request("GET", "/api/customer/restaurants"))
        return (0 until arr.length()).mapNotNull { i ->
            val item = arr.optJSONObject(i) ?: return@mapNotNull null
            val id = item.optInt("id", 0)
            if (id <= 0 || !item.optBoolean("is_approved", false)) return@mapNotNull null
            Restaurant(
                id = id,
                name = item.optString("name", "Restoran"),
                address = item.optString("address", "").takeUnless { it == "null" }.orEmpty(),
                logoUrl = item.optString("logo_url", "").takeIf { it.startsWith("https://") }
            )
        }
    }

    suspend fun menu(restaurantId: Int): List<Food> {
        val response = JSONObject(request("GET", "/api/customer/restaurants/$restaurantId/menu"))
        val arr = response.optJSONArray("items") ?: JSONArray()
        return (0 until arr.length()).mapNotNull { i ->
            val item = arr.optJSONObject(i) ?: return@mapNotNull null
            val id = item.optInt("id", 0)
            if (id <= 0 || !item.optBoolean("is_available", true)) return@mapNotNull null
            Food(
                id = id,
                name = item.optString("name", "Taom"),
                price = item.optDouble("price", 0.0).toLong().coerceAtLeast(0L),
                imageUrl = item.optString("image_url", "").takeIf { it.startsWith("https://") },
                category = item.optString("category", "").takeUnless { it == "null" }.orEmpty()
            )
        }
    }

    suspend fun register(name: String, phone: String, password: String) {
        val body = JSONObject().put("name", name).put("phone", phone).put("password", password)
        request("POST", "/api/auth/register", body)
    }

    suspend fun login(phone: String, password: String): Session {
        val body = JSONObject().put("phone", phone).put("password", password)
        val json = JSONObject(request("POST", "/api/auth/login", body))
        if (json.optString("role") != "customer") {
            throw IllegalStateException("Bu dastur faqat mijozlar uchun")
        }
        val token = json.optString("access_token", "")
        if (token.isBlank()) throw IllegalStateException("Kirish tokeni olinmadi")
        return Session(token, "customer")
    }

    suspend fun chat(message: String): String {
        val body = JSONObject().put("message", message)
        val reply = JSONObject(request("POST", "/api/assistant/chat", body))
            .optString("reply", "")
        if (reply.isBlank()) throw IllegalStateException("Yordamchi javob bermadi")
        return reply
    }
}
