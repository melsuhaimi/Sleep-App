package com.melsuhaimi.sleepapp.bootstrap.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.NavHost

@Composable
fun AppNavigation(
    navigationState: NavigationState,
    modifier: Modifier = Modifier,
    startDestination: AppRoute = AppRoute.WORLD,
    destinations: NavGraphBuilder.() -> Unit,
) {
    NavHost(
        navController = navigationState.navController,
        startDestination = startDestination.routeId,
        modifier = modifier,
        builder = destinations,
    )
}
