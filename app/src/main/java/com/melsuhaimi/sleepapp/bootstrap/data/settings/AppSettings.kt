package com.melsuhaimi.sleepapp.bootstrap.data.settings

data class AppSettings(
    val themePreference: ThemePreference = ThemePreference.SYSTEM,
    val soundVolume: Int = 70,
    val reduceMotion: Boolean = false,
    val sleepTargetMinutes: Int = 480,
    val notificationsEnabled: Boolean = true,
    val onboardingCompleted: Boolean = false,
)

enum class ThemePreference {
    SYSTEM,
    LIGHT,
    DARK,
}

object AppSettingsPreferenceKeys {
    const val THEME = "theme"
    const val SOUND_VOLUME = "sound_volume"
    const val REDUCE_MOTION = "reduce_motion"
    const val SLEEP_TARGET_MINUTES = "sleep_target_minutes"
    const val NOTIFICATIONS_ENABLED = "notifications_enabled"
    const val ONBOARDING_COMPLETED = "onboarding_completed"

    val all: List<String> = listOf(
        THEME,
        SOUND_VOLUME,
        REDUCE_MOTION,
        SLEEP_TARGET_MINUTES,
        NOTIFICATIONS_ENABLED,
        ONBOARDING_COMPLETED,
    )
}
