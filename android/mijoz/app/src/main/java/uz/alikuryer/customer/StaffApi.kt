package uz.alikuryer.customer

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Staff API; all role permissions are also enforced by the server. */
internal object StaffApi {
    private val base = BuildConfig.API_BASE_URL.trimEnd('/')

    private suspend fun call(path: String, method: String = "GET",
                             token: String? = null, body: JSONObject? = null): String =
        withContext(Dispatchers.IO) {
            val connection = URL(base + path).openConnection() as HttpURLConnection
            try {
                connection.requestMethod = method
                connection.connectTimeout = 15000
                connection.readTimeout = 25000
                connection.setRequestProperty("Accept", "application/json")
                if (!token.isNullOrBlank())
                    connection.setRequestProperty("Authorization", "Bearer $token")
                if (body != null) {
                    connection.doOutput = true
                    connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                    connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
                }
                val status = connection.responseCode
                val response = (if (status in 200..299) connection.inputStream else connection.errorStream)
                    ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                if (status !in 200..299) {
                    val detail = runCatching { JSONObject(response).optString("detail", "") }.getOrDefault("")
                    throw IllegalStateException(if (detail.isBlank()) "Server xatosi: $status" else detail)
                }
                response
            } finally { connection.disconnect() }
        }

    suspend fun login(phone: String, password: String, expectedRole: String): String {
        val endpoint = if (expectedRole == "admin") "/api/auth/admin/login" else "/api/auth/login"
        val body = if (expectedRole == "admin") {
            JSONObject().put("username", phone).put("password", password)
        } else {
            JSONObject().put("phone", phone).put("password", password)
        }
        val json = JSONObject(call(endpoint, "POST", body = body))
        if (json.optString("role") != expectedRole)
            throw IllegalStateException("Bu ilovaga faqat ${roleLabel(expectedRole)} hisobi bilan kiriladi")
        return json.optString("access_token").takeIf { it.isNotBlank() }
            ?: throw IllegalStateException("Kirish tokeni olinmadi")
    }
    suspend fun changeAdminPassword(token: String, current: String, updated: String) {
        call("/api/auth/admin/change-password", "POST", token,
            JSONObject().put("current_password", current).put("new_password", updated))
    }

    suspend fun getOrders(token: String): JSONArray = JSONArray(call("/api/v1/staff/orders", token = token))
    suspend fun offers(token: String): JSONArray = JSONArray(call("/api/v1/courier/offers", token = token))
    suspend fun accept(token: String, orderId: Int): JSONObject =
        JSONObject(call("/api/v1/courier/orders/$orderId/accept", "POST", token))
    suspend fun setStatus(token: String, orderId: Int, status: String): JSONObject =
        JSONObject(call("/api/v1/orders/$orderId/status", "POST", token,
            JSONObject().put("status", status)))
    suspend fun updatePosition(token: String, lat: Double, lng: Double, online: Boolean) {
        call("/api/v1/courier/position", "POST", token,
            JSONObject().put("latitude", lat).put("longitude", lng)
                .put("available", online).put("tracking_consent", online))
    }
    suspend fun restaurants(token: String): JSONArray =
        JSONArray(call("/api/v1/staff/restaurants", token = token))
    suspend fun manageMenu(token: String, id: Int): JSONArray =
        JSONArray(call("/api/v1/restaurants/$id/manage-menu", token = token))
    suspend fun stats(token: String, id: Int): JSONArray =
        JSONArray(call("/api/v1/restaurants/$id/statistics", token = token))
    suspend fun addFood(token: String, restaurantId: Int, name: String, price: Double,
                        category: String, description: String): Int =
        JSONObject(call("/api/v1/restaurants/$restaurantId/menu", "POST", token,
            JSONObject().put("name", name).put("price", price).put("category", category)
                .put("description", description).put("is_available", true))).optInt("id")
    suspend fun updateFood(token: String, restaurantId: Int, itemId: Int,
                           price: Double, available: Boolean) {
        call("/api/v1/restaurants/$restaurantId/menu/$itemId", "PATCH", token,
            JSONObject().put("price", price).put("is_available", available))
    }
    suspend fun uploadPhoto(token: String, restaurantId: Int, itemId: Int,
                            imageBytes: ByteArray, mime: String) = withContext(Dispatchers.IO) {
        if (imageBytes.size > 2_000_000) throw IllegalStateException("Rasm 2 MB dan oshmasin")
        val boundary = "AliKuryerForm${System.nanoTime()}"
        val connection = URL("$base/api/v1/restaurants/$restaurantId/menu/$itemId/photo")
            .openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 15000
            connection.readTimeout = 25000
            connection.doOutput = true
            connection.setRequestProperty("Authorization", "Bearer $token")
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
            val start = ("--$boundary\r\n" +
                "Content-Disposition: form-data; name=\"file\"; filename=\"food.jpg\"\r\n" +
                "Content-Type: $mime\r\n\r\n").toByteArray(Charsets.UTF_8)
            val end = "\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8)
            connection.outputStream.use { stream ->
                stream.write(start); stream.write(imageBytes); stream.write(end)
            }
            if (connection.responseCode !in 200..299)
                throw IllegalStateException("Rasm saqlanmadi: ${connection.responseCode}")
        } finally { connection.disconnect() }
    }
    suspend fun setRestaurantGeo(token: String, restaurantId: Int, lat: Double, lng: Double) {
        call("/api/v1/restaurants/$restaurantId/geo", "PUT", token,
            JSONObject().put("latitude", lat).put("longitude", lng))
    }
    suspend fun approval(token: String, restaurantId: Int, approved: Boolean) {
        call("/api/v1/admin/restaurants/$restaurantId/approval", "POST", token,
            JSONObject().put("approved", approved))
    }
    suspend fun messages(token: String, orderId: Int): JSONArray =
        JSONArray(call("/api/v1/orders/$orderId/messages", token = token))
    suspend fun sendMessage(token: String, orderId: Int, text: String) {
        call("/api/v1/orders/$orderId/messages", "POST", token, JSONObject().put("body", text))
    }
    suspend fun supportThreads(token: String): JSONArray =
        JSONArray(call("/api/v1/admin/support/threads", token = token))
    suspend fun supportMessages(token: String, customerId: Int): JSONArray =
        JSONArray(call("/api/v1/support/messages?customer_id=$customerId", token = token))
    suspend fun sendSupport(token: String, customerId: Int, text: String) {
        call("/api/v1/support/messages?customer_id=$customerId", "POST", token,
            JSONObject().put("body", text))
    }
    suspend fun aiHistory(token: String): JSONArray =
        JSONArray(call("/api/v1/admin/assistant-conversations", token = token))
    suspend fun addStaff(token: String, name: String, phone: String, password: String,
                         role: String, restaurantId: Int?): JSONObject {
        val body = JSONObject().put("name", name).put("phone", phone)
            .put("password", password).put("role", role)
        if (restaurantId != null) body.put("restaurant_id", restaurantId)
        return JSONObject(call("/api/v1/admin/staff", "POST", token, body))
    }
}
internal fun roleLabel(role: String) = when (role) {
    "courier" -> "Kuryer"
    "restaurant" -> "Oshxona"
    "admin" -> "Admin"
    else -> "Mijoz"
}
