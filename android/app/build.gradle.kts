plugins {
    id("com.android.application")
}

android {
    namespace = "ru.reader.offline"
    compileSdk = 37

    defaultConfig {
        applicationId = "ru.reader.offline"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

// зависимостей нет вовсе: только framework API.
// Разрешений нет вовсе: ни INTERNET, ни STORAGE — приложению физически
// нечем отправить ваши книги куда-либо.
