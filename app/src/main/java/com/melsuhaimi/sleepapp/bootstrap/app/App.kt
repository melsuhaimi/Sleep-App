package com.melsuhaimi.sleepapp.bootstrap.app

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import com.melsuhaimi.sleepapp.bootstrap.feature.foundation.FoundationRoute
import com.melsuhaimi.sleepapp.bootstrap.navigation.AppNavigation
import com.melsuhaimi.sleepapp.bootstrap.navigation.AppRoute
import com.melsuhaimi.sleepapp.bootstrap.navigation.rememberNavigationState
import com.melsuhaimi.sleepapp.bootstrap.ui.components.SleepScaffold
import com.melsuhaimi.sleepapp.bootstrap.ui.theme.SleepTheme

@Composable
fun SleepApp() {
    SleepTheme {
        val navigationState = rememberNavigationState()
        val backStackEntry by navigationState.navController.currentBackStackEntryAsState()
        val currentRoute = AppRoute.fromRouteId(backStackEntry?.destination?.route) ?: AppRoute.WORLD

        SleepScaffold(
            currentRoute = currentRoute,
            onRouteSelected = navigationState::navigateTo,
        ) { contentPadding ->
            AppNavigation(
                navigationState = navigationState,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(contentPadding),
            ) {
                AppRoute.topLevelRoutes.forEach { route ->
                    composable(route.routeId) {
                        FoundationRoute(
                            route = route,
                            modifier = Modifier.fillMaxSize(),
                        )
                    }
                }
            }
        }
    }
}
