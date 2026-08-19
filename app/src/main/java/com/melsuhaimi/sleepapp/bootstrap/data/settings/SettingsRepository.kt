package com.melsuhaimi.sleepapp.bootstrap.data.settings

import kotlinx.coroutines.flow.Flow

interface SettingsRepository {
    val settings: Flow<AppSettings>

    suspend fun setThemePreference(themePreference: ThemePreference)
    suspend fun setSoundVolume(volume: Int)
    suspend fun setReduceMotion(enabled: Boolean)
    suspend fun setSleepTargetMinutes(minutes: Int)
    suspend fun setNotificationsEnabled(enabled: Boolean)
    suspend fun setOnboardingCompleted(completed: Boolean)
}
