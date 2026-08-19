plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.melsuhaimi.sleepapp.bootstrap"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.melsuhaimi.sleepapp.bootstrap"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.0.1-checkpoint2"

        manifestPlaceholders["buildCommit"] =
            providers.gradleProperty("buildCommit").orElse("LOCAL").get()
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.08.00")

    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")

    debugImplementation("androidx.compose.ui:ui-tooling")

    testImplementation("junit:junit:4.13.2")
}
