package uz.alikuryer.app

import android.annotation.SuppressLint
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback

class MainActivity : ComponentActivity() {
    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.statusBarColor = android.graphics.Color.WHITE
        window.navigationBarColor = android.graphics.Color.WHITE
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or
            View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        )

        webView = WebView(this).apply {
            setBackgroundColor(android.graphics.Color.WHITE)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = true
            settings.loadWithOverviewMode = true
            settings.useWideViewPort = true
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, url: String) {
                    // Keep the approved screen artwork and its hotspots unchanged;
                    // remove only the desktop presentation panel around the phone.
                    view.evaluateJavascript("""
                        (function() {
                          var style = document.createElement('style');
                          style.textContent = `
                            html, body { margin:0 !important; padding:0 !important;
                              width:100% !important; height:100% !important;
                              overflow:hidden !important; background:#fff !important; }
                            .layout { display:flex !important; align-items:center !important;
                              justify-content:center !important; width:100vw !important;
                              height:100dvh !important; max-width:none !important;
                              margin:0 !important; padding:0 !important; }
                            .panel { display:none !important; }
                            .phone { position:relative !important; width:auto !important;
                              height:100dvh !important; max-width:100vw !important;
                              max-height:100dvh !important; margin:0 auto !important;
                              filter:none !important; }
                            .phone img { display:block !important; width:auto !important;
                              height:100% !important; max-width:100vw !important;
                              max-height:100dvh !important; object-fit:contain !important;
                              border-radius:0 !important; }
                            #hot { position:absolute !important; inset:0 !important; }
                          `;
                          document.head.appendChild(style);
                        })();
                    """.trimIndent(), null)
                }
            }
        }

        setContentView(webView)
        webView.loadUrl("file:///android_asset/index.html")

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack() else finish()
            }
        })
    }

    override fun onDestroy() {
        if (::webView.isInitialized) {
            webView.stopLoading()
            webView.destroy()
        }
        super.onDestroy()
    }
}
