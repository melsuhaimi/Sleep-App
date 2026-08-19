package com.melsuhaimi.sleepapp.bootstrap.feature.foundation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import com.melsuhaimi.sleepapp.bootstrap.navigation.AppRoute
import com.melsuhaimi.sleepapp.bootstrap.ui.state.ScreenStatus

@Composable
fun FoundationRoute(
    route: AppRoute,
    modifier: Modifier = Modifier,
) {
    val state = remember(route) { route.toFoundationUiState() }

    FoundationScreen(
        state = state,
        onAction = {},
        modifier = modifier,
    )
}

private fun AppRoute.toFoundationUiState(): FoundationUiState = when (this) {
    AppRoute.WORLD -> FoundationUiState(
        route = this,
        status = ScreenStatus.Content,
        title = "World",
        message = "P1 product foundation is installed: navigation, theme, Hilt, Room, and DataStore.",
    )
    AppRoute.SLEEP -> FoundationUiState(
        route = this,
        status = ScreenStatus.CapabilityUnavailable,
        title = "Sleep",
        message = "Sleep-session behavior begins in P2. P1 only installs the app foundation.",
    )
    AppRoute.JOURNAL -> FoundationUiState(
        route = this,
        status = ScreenStatus.Empty,
        title = "Journal",
        message = "Resolved sleep-session history starts after P2 creates manual anchors.",
    )
    AppRoute.MENU -> FoundationUiState(
        route = this,
        status = ScreenStatus.Content,
        title = "Menu",
        message = "Settings storage is backed by DataStore and structured product storage is backed by Room.",
    )
}
