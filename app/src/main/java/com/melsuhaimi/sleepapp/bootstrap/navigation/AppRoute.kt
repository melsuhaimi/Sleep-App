package com.melsuhaimi.sleepapp.bootstrap.navigation

enum class AppRoute(
    val routeId: String,
) {
    WORLD("world"),
    SLEEP("sleep"),
    JOURNAL("journal"),
    MENU("menu"),
    ;

    companion object {
        val topLevelRoutes: List<AppRoute> = entries.toList()
    }
}
