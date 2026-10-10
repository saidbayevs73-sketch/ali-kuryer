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
data class AliOrder(
    val id: Int, val status: String, val total: Long,
    val restaurantId: Int, val address: String,
    val courierName: String?, val courierPhone: String?,
    val courierLat: Double?, val courierLng: Double?
)
data class AliChatMessage(
    val id: Int, val senderId: Int, val senderName: String, val body: String
)


object AliApi {
    private const val BASE = BuildConfig.API_BASE_URL

    private suspend fun request(method: String, path: String, body: JSONObject? = null, token: String? = null): String =
        withContext(Dispatchers.IO) {
            val conn = URL(BASE.trimEnd('/') + path).openConnection() as HttpURLConnection
            try {
                conn.requestMethod = method
                conn.connectTimeout = 15000
                conn.readTimeout = 20000
                conn.setRequestProperty("Accept", "application/json")
                if (!token.isNullOrBlank()) {
                    conn.setRequestProperty("Authorization", "Bearer $token")
                }
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

    suspend fun requestRegistrationCode(phone: String) {
        request("POST", "/api/auth/otp/request", JSONObject().put("phone", phone))
    }

    suspend fun requestExistingPhoneCode(token: String, phone: String) {
        request("POST", "/api/auth/phone/request", JSONObject().put("phone", phone), token)
    }

    suspend fun confirmExistingPhone(token: String, phone: String, code: String) {
        request("POST", "/api/auth/phone/confirm",
            JSONObject().put("phone", phone).put("otp_code", code), token)
    }

    suspend fun isPhoneVerified(token: String): Boolean =
        JSONObject(request("GET", "/api/auth/phone/status", token = token))
            .optBoolean("verified", false)

    suspend fun register(name: String, phone: String, password: String, otpCode: String) {
        val body = JSONObject().put("name", name).put("phone", phone)
            .put("password", password).put("otp_code", otpCode)
        request("POST", "/api/auth/register", body)
    }

    suspend fun firebasePhoneLogin(idToken: String, name: String): Session {
        val body = JSONObject().put("id_token", idToken)
            .put("name", name.take(150))
        val response = JSONObject(request("POST", "/api/auth/firebase/phone-login", body))
        if (response.optString("role") != "customer") {
            throw IllegalStateException("Firebase tasdiqlagan hisob mijoz bo‘lishi kerak")
        }
        val token = response.optString("access_token", "")
        if (token.isBlank()) throw IllegalStateException("Server kirish tokenini bermadi")
        return Session(token, "customer")
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


    private fun parseOrder(json: JSONObject): AliOrder {
        val courier = json.optJSONObject("courier")
        val location = json.optJSONObject("courier_location")
        return AliOrder(
            id = json.optInt("id", 0),
            status = json.optString("status", "pending"),
            total = json.optDouble("total", 0.0).toLong(),
            restaurantId = json.optInt("restaurant_id"),
            address = json.optString("address", ""),
            courierName = courier?.optString("name")?.takeIf { it.isNotBlank() },
            courierPhone = courier?.optString("phone")?.takeIf { it.startsWith("+998") },
            courierLat = location?.optDouble("latitude"),
            courierLng = location?.optDouble("longitude")
        )
    }

    private fun parseMessages(data: String): List<AliChatMessage> {
        val arr = JSONArray(data)
        return (0 until arr.length()).map { idx ->
            val item = arr.getJSONObject(idx)
            AliChatMessage(
                id = item.optInt("id"), senderId = item.optInt("sender_id"),
                senderName = item.optString("sender_name", ""),
                body = item.optString("body", "")
            )
        }
    }

    suspend fun createOrder(
        token: String, restaurantId: Int, address: String, phone: String,
        items: Map<Int, Int>, privacyAccepted: Boolean,
        latitude: Double? = null, longitude: Double? = null
    ): AliOrder {
        val lines = JSONArray()
        items.filterValues { it > 0 }.forEach { (id, qty) ->
            lines.put(JSONObject().put("menu_item_id", id).put("quantity", qty))
        }
        val data = JSONObject()
            .put("restaurant_id", restaurantId)
            .put("address", address.trim())
            .put("phone", phone.trim())
            .put("payment_method", "cash")
            .put("privacy_accepted", privacyAccepted)
            .put("items", lines)
        if (latitude != null && longitude != null) {
            data.put("latitude", latitude).put("longitude", longitude)
        }
        return parseOrder(JSONObject(request("POST", "/api/v1/orders", data, token)))
    }

    suspend fun myOrders(token: String): List<AliOrder> {
        val arr = JSONArray(request("GET", "/api/v1/orders/my", token = token))
        return (0 until arr.length()).map { parseOrder(arr.getJSONObject(it)) }
    }

    suspend fun orderDetails(token: String, orderId: Int): AliOrder =
        parseOrder(JSONObject(request("GET", "/api/v1/orders/$orderId", token = token)))

    suspend fun orderMessages(token: String, orderId: Int): List<AliChatMessage> =
        parseMessages(request("GET", "/api/v1/orders/$orderId/messages", token = token))

    suspend fun sendOrderMessage(token: String, orderId: Int, body: String) {
        request("POST", "/api/v1/orders/$orderId/messages",
            JSONObject().put("body", body), token)
    }

    suspend fun supportMessages(token: String): List<AliChatMessage> =
        parseMessages(request("GET", "/api/v1/support/messages", token = token))

    suspend fun sendSupportMessage(token: String, body: String) {
        request("POST", "/api/v1/support/messages",
            JSONObject().put("body", body), token)
    }

    suspend fun chat(
        message: String, token: String? = null, retainHistory: Boolean = false,
        imageBase64: String? = null
    ): String {
        val body = JSONObject().put("message", message)
        val endpoint = if (token == null) "/api/assistant/chat" else "/api/v1/assistant/chat"
        if (token != null) body.put("retain_history", retainHistory)
        if (imageBase64 != null) body.put("image_base64", imageBase64)
        val payload = JSONObject(request("POST", endpoint, body, token))
        val reply = payload.optString("reply", "")
        if (reply.isBlank()) throw IllegalStateException("Yordamchi javob bermadi")
        return when (payload.optString("mode")) {
            "basic" -> "Ma’lumot rejimi: $reply"
            "operator" -> "Operator: $reply\n" +
                payload.optString("operator_url", "https://t.me/AliKuryerYordamBot")
            else -> reply
        }
    }
}
