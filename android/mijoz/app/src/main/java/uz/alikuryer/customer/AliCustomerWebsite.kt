package uz.alikuryer.customer

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.webkit.GeolocationPermissions
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.Button
import androidx.compose.material3.Column
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat

/**
 * Customer app shares the real mobile storefront with the website.
 * Customers never load /admin, /restaurant or /courier inside this surface.
 * Staff flavors keep their own native, role-protected views.
 */
@Composable
fun AliCustomerWebsite() {
    val context = LocalContext.current
    val site = "https://ali-kuryer.onrender.com/"
    var loadError by remember { mutableStateOf(false) }
    var pendingGeo by remember {
        mutableStateOf<Pair<String, GeolocationPermissions.Callback>?>(null)
    }
    val geolocationPermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { granted ->
        pendingGeo?.let { (origin, callback) ->
            val allowed = granted.values.any { it }
            callback.invoke(origin, allowed, false)
            pendingGeo = null
        }
    }
    val webView = remember {
        WebView(context).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.javaScriptCanOpenWindowsAutomatically = false
            settings.setSupportMultipleWindows(false)
            settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            settings.setGeolocationEnabled(true)
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    val uri = request.url
                    // Telegram's OAuth must keep the same WebView browser state
                    // so that its PKCE completion remains bound to this device.
                    val trusted = uri.scheme == "https" &&
                        (uri.host == "ali-kuryer.onrender.com" ||
                         (uri.host == "oauth.telegram.org" && uri.path == "/auth"))
                    if (trusted) return false
                    try { context.startActivity(Intent(Intent.ACTION_VIEW, uri)) }
                    catch (_: ActivityNotFoundException) { /* avoid crashing */ }
                    return true
                }
                override fun onReceivedError(
                    view: WebView, request: WebResourceRequest,
                    error: android.webkit.WebResourceError
                ) {
                    if (request.isForMainFrame) loadError = true
                }
                override fun onPageFinished(view: WebView, url: String) {
                    if (url.startsWith(site)) loadError = false
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onGeolocationPermissionsShowPrompt(
                    origin: String, callback: GeolocationPermissions.Callback
                ) {
                    if (origin != "https://ali-kuryer.onrender.com") {
                        callback.invoke(origin, false, false)
                        return
                    }
                    val fine = ContextCompat.checkSelfPermission(
                        context, Manifest.permission.ACCESS_FINE_LOCATION
                    ) == PackageManager.PERMISSION_GRANTED
                    val coarse = ContextCompat.checkSelfPermission(
                        context, Manifest.permission.ACCESS_COARSE_LOCATION
                    ) == PackageManager.PERMISSION_GRANTED
                    if (fine || coarse) callback.invoke(origin, true, false)
                    else {
                        pendingGeo = origin to callback
                        geolocationPermission.launch(
                            arrayOf(Manifest.permission.ACCESS_FINE_LOCATION,
                                    Manifest.permission.ACCESS_COARSE_LOCATION)
                        )
                    }
                }
            }
            loadUrl(site)
        }
    }
    DisposableEffect(webView) {
        onDispose {
            pendingGeo?.let { (origin, callback) ->
                callback.invoke(origin, false, false)
                pendingGeo = null
            }
            webView.stopLoading()
            webView.destroy()
        }
    }
    BackHandler(enabled = webView.canGoBack()) {
        webView.goBack()
    }
    Box(Modifier.fillMaxSize()) {
        AndroidView(factory = { webView }, modifier = Modifier.fillMaxSize())
        if (loadError) Column {
            Text("Internet bilan ulanishni tekshiring")
            Button(onClick = { loadError = false; webView.reload() }) {
                Text("Qayta urinish")
            }
        }
    }
}
