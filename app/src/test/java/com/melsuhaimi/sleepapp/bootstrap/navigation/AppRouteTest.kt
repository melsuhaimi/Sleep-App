package com.melsuhaimi.sleepapp.bootstrap.navigation

import org.junit.Assert.assertEquals
import org.junit.Test

class AppRouteTest {
    @Test
    fun topLevelRoutesFollowArchitectureOrder() {
        assertEquals(
            listOf(
                AppRoute.WORLD,
                AppRoute.SLEEP,
                AppRoute.JOURNAL,
                AppRoute.MENU,
            ),
            AppRoute.topLevelRoutes,
        )
    }

    @Test
    fun topLevelRouteIdsAreStableAndUnique() {
        val routeIds = AppRoute.topLevelRoutes.map(AppRoute::routeId)

        assertEquals(
            listOf("world", "sleep", "journal", "menu"),
            routeIds,
        )
        assertEquals(routeIds.size, routeIds.toSet().size)
    }
}
