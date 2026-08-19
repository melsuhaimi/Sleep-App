package com.melsuhaimi.sleepapp.bootstrap.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.runtime.remember
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.rememberNavController

@Stable
class NavigationState internal constructor(
    val navController: NavHostController,
) {
    fun navigateTo(route: AppRoute) {
        navController.navigate(route.routeId) {
            popUpTo(navController.graph.findStartDestination().id) {
                saveState = true
            }
            launchSingleTop = true
            restoreState = true
        }
    }
}

@Composable
fun rememberNavigationState(
    navController: NavHostController = rememberNavController(),
): NavigationState = remember(navController) {
    NavigationState(navController)
}
