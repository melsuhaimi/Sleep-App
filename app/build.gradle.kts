plugins {
    id("com.android.application")
}

android {
    namespace = "com.melsuhaimi.sleepapp.bootstrap"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.melsuhaimi.sleepapp.bootstrap"
        minSdk = 26
        targetSdk = 37
        versionCode = 1
        versionName = "0.0.1-checkpoint2"

        manifestPlaceholders["buildCommit"] =
            providers.gradleProperty("buildCommit").orElse("LOCAL").get()
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
