package uz.alikuryer.app

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.FrameLayout
import android.webkit.GeolocationPermissions
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.lifecycle.lifecycleScope
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import kotlinx.coroutines.launch
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var root: FrameLayout
    private var fileCallback: ValueCallback<Array<Uri>>? = null
    private var geoCallback: GeolocationPermissions.Callback? = null
    private var geoOrigin: String? = null
    private val filePickerRequest = 2101
    private val locationRequest = 2102
    private val webClientId = "1088566467185-1tefomqi153ho33u18r40u3p27le8gbm.apps.googleusercontent.com"
    private val firebaseAuth: FirebaseAuth by lazy { FirebaseAuth.getInstance() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        WindowCompat.setDecorFitsSystemWindows(window, false)
        window.statusBarColor = android.graphics.Color.WHITE
        window.navigationBarColor = android.graphics.Color.WHITE
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            window.isNavigationBarContrastEnforced = false
        }
        WindowInsetsControllerCompat(window, window.decorView).apply {
            isAppearanceLightStatusBars = true
            isAppearanceLightNavigationBars = true
        }

        root = FrameLayout(this).apply {
            setBackgroundColor(android.graphics.Color.WHITE)
            clipToPadding = true
        }

        webView = WebView(this)
        webView.setBackgroundColor(android.graphics.Color.WHITE)
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null)
        webView.isVerticalScrollBarEnabled = false
        webView.isHorizontalScrollBarEnabled = false
        webView.clipToPadding = true
        root.addView(
            webView,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )

        ViewCompat.setOnApplyWindowInsetsListener(root) { _, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout()
            )
            val params = webView.layoutParams as FrameLayout.LayoutParams
            if (params.leftMargin != bars.left ||
                params.topMargin != bars.top ||
                params.rightMargin != bars.right ||
                params.bottomMargin != bars.bottom
            ) {
                params.setMargins(bars.left, bars.top, bars.right, bars.bottom)
                webView.layoutParams = params
            }
            insets
        }

        val settings: WebSettings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        settings.allowFileAccessFromFileURLs = true
        settings.javaScriptCanOpenWindowsAutomatically = true
        settings.setGeolocationEnabled(true)
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = false
        settings.textZoom = 100
        settings.setSupportZoom(false)
        settings.builtInZoomControls = false
        settings.displayZoomControls = false

        webView.addJavascriptInterface(AliKuryerBridge(), "AliKuryerNative")

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                view?.evaluateJavascript(
                    """
                    (function(){
                      if(!document.getElementById('ali-android-layout-fix')){
                        var style=document.createElement('style');
                        style.id='ali-android-layout-fix';
                        style.textContent=
                          'html,body{height:100%;min-height:0;overflow:hidden}' +
                          '.app{height:100%!important;min-height:0!important;overflow:hidden!important}' +
                          '.app-main{min-height:0!important;overscroll-behavior:contain;padding-bottom:18px!important;scroll-padding-bottom:24px}' +
                          '.tabbar{height:68px!important;min-height:68px!important;flex:0 0 68px!important;padding-bottom:8px!important}' +
                          '.language{height:100%!important;min-height:0!important;padding:56px 18px 22px!important}' +
                          '.language h2{margin:28px 0 6px!important}' +
                          '.lang-list{margin-top:22px!important}' +
                          '.home-premium{padding-bottom:18px!important}' +
                          '.home-premium-head{padding-top:6px!important}' +
                          '.home-food-section{padding-bottom:26px!important}';
                        document.head.appendChild(style);
                      }
                      if(!window.__aliGoogleLoginBound){
                        window.__aliGoogleLoginBound=true;
                        document.addEventListener('click',function(e){
                          var b=e.target && e.target.closest ? e.target.closest('#loginBtn, [data-google-login]') : null;
                          if(!b) return;
                          e.preventDefault();
                          e.stopPropagation();
                          if(e.stopImmediatePropagation) e.stopImmediatePropagation();
                          if(window.AliKuryerNative) window.AliKuryerNative.signInWithGoogle();
                        },true);
                      }
                      window.aliKuryerGoogleAuthSuccess=function(name,email){
                        var panel=document.getElementById('accountPanel');
                        if(panel){
                          panel.hidden=false;
                          panel.innerHTML='';
                          var wrap=document.createElement('div');
                          wrap.style.cssText='padding:20px;border-radius:18px;background:#fff;border:1px solid #e8e8e8;margin:16px 0';
                          var heading=document.createElement('h2'); heading.textContent='Profil';
                          var user=document.createElement('p'); user.textContent=name || 'Google foydalanuvchisi';
                          var mail=document.createElement('p'); mail.textContent=email || '';
                          var state=document.createElement('small'); state.textContent='Google orqali muvaffaqiyatli kirdingiz';
                          wrap.append(heading,user,mail,state); panel.appendChild(wrap);
                          panel.scrollIntoView({behavior:'smooth',block:'center'});
                        }
                        var btn=document.getElementById('loginBtn');
                        if(btn){btn.innerHTML='♙ <span>'+String(name||'Profil').replace(/[<>&"]/g,'')+'</span>';}
                      };
                      window.aliKuryerGoogleAuthError=function(message){
                        alert(message || 'Google orqali kirishda xatolik yuz berdi. Qayta urinib ko‘ring.');
                      };
                    })();
                    """.trimIndent(),
                    null
                )
                firebaseAuth.currentUser?.let { user ->
                    view?.evaluateJavascript(
                        "if(window.aliKuryerGoogleAuthSuccess)window.aliKuryerGoogleAuthSuccess(${JSONObject.quote(user.displayName ?: "")},${JSONObject.quote(user.email ?: "")});",
                        null
                    )
                }
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                view: WebView?,
                callback: ValueCallback<Array<Uri>>?,
                params: FileChooserParams?
            ): Boolean {
                fileCallback?.onReceiveValue(null)
                fileCallback = callback
                val intent = params?.createIntent() ?: return false
                return try {
                    startActivityForResult(intent, filePickerRequest)
                    true
                } catch (_: Exception) {
                    fileCallback = null
                    false
                }
            }

            override fun onGeolocationPermissionsShowPrompt(
                origin: String?,
                callback: GeolocationPermissions.Callback?
            ) {
                if (checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED ||
                    checkSelfPermission(android.Manifest.permission.ACCESS_COARSE_LOCATION) == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    callback?.invoke(origin, true, false)
                } else {
                    geoOrigin = origin
                    geoCallback = callback
                    requestPermissions(
                        arrayOf(android.Manifest.permission.ACCESS_FINE_LOCATION, android.Manifest.permission.ACCESS_COARSE_LOCATION),
                        locationRequest
                    )
                }
            }
        }

        setContentView(root)
        ViewCompat.requestApplyInsets(root)
        webView.loadUrl("file:///android_asset/index.html")
    }

    private inner class AliKuryerBridge {
        @JavascriptInterface
        fun signInWithGoogle() {
            runOnUiThread {
                this@MainActivity.lifecycleScope.launch {
                    try {
                        val googleOption = GetGoogleIdOption.Builder()
                            .setServerClientId(webClientId)
                            .setFilterByAuthorizedAccounts(false)
                            .setAutoSelectEnabled(false)
                            .build()
                        val request = GetCredentialRequest.Builder()
                            .addCredentialOption(googleOption)
                            .build()
                        val credentialManager = CredentialManager.create(this@MainActivity)
                        val result = credentialManager.getCredential(this@MainActivity, request)
                        val credential = result.credential
                        if (credential is CustomCredential &&
                            credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
                        ) {
                            val googleCredential = GoogleIdTokenCredential.createFrom(credential.data)
                            val firebaseCredential = GoogleAuthProvider.getCredential(googleCredential.idToken, null)
                            firebaseAuth.signInWithCredential(firebaseCredential)
                                .addOnCompleteListener(this@MainActivity) { task ->
                                    if (task.isSuccessful) {
                                        val user = task.result?.user
                                        val name = JSONObject.quote(user?.displayName ?: "")
                                        val email = JSONObject.quote(user?.email ?: "")
                                        webView.evaluateJavascript(
                                            "if(window.aliKuryerGoogleAuthSuccess)window.aliKuryerGoogleAuthSuccess($name,$email);",
                                            null
                                        )
                                    } else {
                                        showGoogleError(task.exception?.localizedMessage)
                                    }
                                }
                        } else {
                            showGoogleError("Google hisob ma’lumoti olinmadi. Qayta urinib ko‘ring.")
                        }
                    } catch (e: Exception) {
                        showGoogleError(e.localizedMessage)
                    }
                }
            }
        }
    }

    private fun showGoogleError(message: String?) {
        val safeMessage = JSONObject.quote(message ?: "Google orqali kirishda xatolik yuz berdi.")
        runOnUiThread {
            if (::webView.isInitialized) {
                webView.evaluateJavascript(
                    "if(window.aliKuryerGoogleAuthError)window.aliKuryerGoogleAuthError($safeMessage);else alert($safeMessage);",
                    null
                )
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == locationRequest && geoCallback != null) {
            val granted = grantResults.any { it == android.content.pm.PackageManager.PERMISSION_GRANTED }
            geoCallback?.invoke(geoOrigin, granted, false)
            geoCallback = null
            geoOrigin = null
        }
    }

    @Deprecated("Deprecated for WebView file chooser compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == filePickerRequest && fileCallback != null) {
            val result = WebChromeClient.FileChooserParams.parseResult(resultCode, data)
            fileCallback?.onReceiveValue(result)
            fileCallback = null
        }
    }

    @Deprecated("Deprecated in Android API")
    override fun onBackPressed() {
        if (!::webView.isInitialized) {
            super.onBackPressed()
            return
        }
        webView.evaluateJavascript(
            "(function(){try{if(typeof s!=='undefined'&&s.history&&s.history.length>0&&typeof back==='function'){back();return 'handled';}}catch(e){}return 'exit';})()"
        ) { result ->
            if (result == null || result == "\"exit\"") finish()
        }
    }

    override fun onDestroy() {
        if (::webView.isInitialized) webView.destroy()
        super.onDestroy()
    }
}
