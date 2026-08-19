package com.melsuhaimi.sleepapp.bootstrap

import com.melsuhaimi.sleepapp.bootstrap.data.persistence.InitialRoomTables
import com.melsuhaimi.sleepapp.bootstrap.data.persistence.SleepDatabase
import com.melsuhaimi.sleepapp.bootstrap.data.persistence.SleepDatabaseMigrations
import com.melsuhaimi.sleepapp.bootstrap.data.settings.AppSettingsPreferenceKeys
import com.melsuhaimi.sleepapp.bootstrap.navigation.AppRoute
import com.melsuhaimi.sleepapp.bootstrap.ui.state.ScreenStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class P1FoundationContractTest {
    @Test
    fun p1TopLevelNavigationMatchesArchitecture() {
        assertEquals(
            listOf("world", "sleep", "journal", "menu"),
            AppRoute.topLevelRoutes.map(AppRoute::routeId),
        )
    }

    @Test
    fun completeUiStatesAreDeclared() {
        assertEquals(
            setOf(
                ScreenStatus.Loading,
                ScreenStatus.Content,
                ScreenStatus.Empty,
                ScreenStatus.Error,
                ScreenStatus.PermissionDenied,
                ScreenStatus.CapabilityUnavailable,
            ),
            ScreenStatus.entries.toSet(),
        )
    }

    @Test
    fun roomInitialTablesMatchPersistenceArchitecture() {
        assertEquals(
            listOf(
                "sleep_session",
                "sleep_signal",
                "night_outcome",
                "expedition",
                "expedition_path_node",
                "expedition_reward",
                "pet",
                "pet_progression_event",
                "inventory_stack",
                "inventory_instance",
                "inventory_transaction",
                "equipment_slot",
                "quest_progress",
                "quest_objective_progress",
                "world_unlock",
                "world_discovery",
                "collection_entry",
            ),
            InitialRoomTables.all,
        )
        assertEquals(1, SleepDatabase.SCHEMA_VERSION)
        assertTrue(SleepDatabaseMigrations.ALL.isEmpty())
    }

    @Test
    fun dataStoreKeysMatchSmallSettingsArchitecture() {
        assertEquals(
            listOf(
                "theme",
                "sound_volume",
                "reduce_motion",
                "sleep_target_minutes",
                "notifications_enabled",
                "onboarding_completed",
            ),
            AppSettingsPreferenceKeys.all,
        )
    }
}
