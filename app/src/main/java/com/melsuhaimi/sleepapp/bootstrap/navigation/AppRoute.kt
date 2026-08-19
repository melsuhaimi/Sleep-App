package com.melsuhaimi.sleepapp.bootstrap.navigation

enum class AppRoute(
    val routeId: String,
    val label: String,
) {
    WORLD("world", "World"),
    SLEEP("sleep", "Sleep"),
    JOURNAL("journal", "Journal"),
    MENU("menu", "Menu");

    companion object {
        val topLevelRoutes: List<AppRoute> = entries.toList()

        fun fromRouteId(routeId: String?): AppRoute? =
            topLevelRoutes.firstOrNull { it.routeId == routeId }
    }
}
