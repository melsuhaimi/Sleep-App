package com.melsuhaimi.sleepapp.bootstrap.data.settings

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.IOException
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map

private val Context.appSettingsDataStore: DataStore<Preferences> by preferencesDataStore(name = "app_settings")

class DataStoreSettingsRepository @Inject constructor(
    @ApplicationContext private val context: Context,
) : SettingsRepository {
    override val settings: Flow<AppSettings> = context.appSettingsDataStore.data
        .catch { throwable ->
            if (throwable is IOException) {
                emit(emptyPreferences())
            } else {
                throw throwable
            }
        }
        .map { preferences ->
            AppSettings(
                themePreference = preferences[PreferenceKeys.theme].toThemePreference(),
                soundVolume = preferences[PreferenceKeys.soundVolume] ?: 70,
                reduceMotion = preferences[PreferenceKeys.reduceMotion] ?: false,
                sleepTargetMinutes = preferences[PreferenceKeys.sleepTargetMinutes] ?: 480,
                notificationsEnabled = preferences[PreferenceKeys.notificationsEnabled] ?: true,
                onboardingCompleted = preferences[PreferenceKeys.onboardingCompleted] ?: false,
            )
        }

    override suspend fun setThemePreference(themePreference: ThemePreference) {
        context.appSettingsDataStore.edit { preferences ->
            preferences[PreferenceKeys.theme] = themePreference.name
        }
    }

    override suspend fun setSoundVolume(volume: Int) {
        context.appSettingsDataStore.edit { preferences ->
            preferences[PreferenceKeys.soundVolume] = volume.coerceIn(0, 100)
        }
    }

    override suspend fun setReduceMotion(enabled: Boolean) {
        context.appSettingsDataStore.edit { preferences ->
            preferences[PreferenceKeys.reduceMotion] = enabled
        }
    }

    override suspend fun setSleepTargetMinutes(minutes: Int) {
        context.appSettingsDataStore.edit { preferences ->
            preferences[PreferenceKeys.sleepTargetMinutes] = minutes.coerceAtLeast(1)
        }
    }

    override suspend fun setNotificationsEnabled(enabled: Boolean) {
        context.appSettingsDataStore.edit { preferences ->
            preferences[PreferenceKeys.notificationsEnabled] = enabled
        }
    }

    override suspend fun setOnboardingCompleted(completed: Boolean) {
        context.appSettingsDataStore.edit { preferences ->
            preferences[PreferenceKeys.onboardingCompleted] = completed
        }
    }

    private fun String?.toThemePreference(): ThemePreference =
        ThemePreference.entries.firstOrNull { it.name == this } ?: ThemePreference.SYSTEM

    private object PreferenceKeys {
        val theme = stringPreferencesKey(AppSettingsPreferenceKeys.THEME)
        val soundVolume = intPreferencesKey(AppSettingsPreferenceKeys.SOUND_VOLUME)
        val reduceMotion = booleanPreferencesKey(AppSettingsPreferenceKeys.REDUCE_MOTION)
        val sleepTargetMinutes = intPreferencesKey(AppSettingsPreferenceKeys.SLEEP_TARGET_MINUTES)
        val notificationsEnabled = booleanPreferencesKey(AppSettingsPreferenceKeys.NOTIFICATIONS_ENABLED)
        val onboardingCompleted = booleanPreferencesKey(AppSettingsPreferenceKeys.ONBOARDING_COMPLETED)
    }
}
