plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "uz.alikuryer.customer"
    compileSdk = 35

    defaultConfig {
        applicationId = "uz.alikuryer.customer"
        minSdk = 26
        targetSdk = 35
        versionCode = 10
        versionName = "1.6.2"
        buildConfigField("String", "API_BASE_URL", "\"https://ali-kuryer.onrender.com\"")
    }

    flavorDimensions += "audience"
    productFlavors {
        create("mijoz") {
            dimension = "audience"
            applicationId = "uz.alikuryer.customer"
            buildConfigField("String", "APP_ROLE", "\"customer\"")
            resValue("string", "app_name", "Ali Kuryer — Mijoz")
        }
        create("kuryer") {
            dimension = "audience"
            applicationId = "uz.alikuryer.courier"
            buildConfigField("String", "APP_ROLE", "\"courier\"")
            resValue("string", "app_name", "Ali Kuryer — Kuryer")
        }
        create("oshxona") {
            dimension = "audience"
            applicationId = "uz.alikuryer.restaurant"
            buildConfigField("String", "APP_ROLE", "\"restaurant\"")
            resValue("string", "app_name", "Ali Kuryer — Oshxona")
        }
        create("admin") {
            dimension = "audience"
            applicationId = "uz.alikuryer.admin"
            buildConfigField("String", "APP_ROLE", "\"admin\"")
            resValue("string", "app_name", "Ali Kuryer — Admin")
        }
    }

    buildFeatures { compose = true; buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    val bom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(bom)
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("com.google.android.gms:play-services-auth-api-phone:18.2.0")
    // Firebase phone authentication is initialized ONLY for the mijoz flavor
    // using its src/mijoz/assets/google-services.json config.
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-auth")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
