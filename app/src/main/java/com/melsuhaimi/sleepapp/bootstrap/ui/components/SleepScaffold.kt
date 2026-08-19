package com.melsuhaimi.sleepapp.bootstrap.ui.components

import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import com.melsuhaimi.sleepapp.bootstrap.navigation.AppRoute

@Composable
fun SleepScaffold(
    currentRoute: AppRoute,
    onRouteSelected: (AppRoute) -> Unit,
    content: @Composable (PaddingValues) -> Unit,
) {
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            NavigationBar {
                AppRoute.topLevelRoutes.forEach { route ->
                    NavigationBarItem(
                        selected = route == currentRoute,
                        onClick = { onRouteSelected(route) },
                        icon = { Text(route.label.first().toString()) },
                        label = { Text(route.label) },
                    )
                }
            }
        },
        content = content,
    )
}
