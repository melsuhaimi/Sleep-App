package com.melsuhaimi.sleepapp.bootstrap.feature.foundation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.melsuhaimi.sleepapp.bootstrap.navigation.AppRoute
import com.melsuhaimi.sleepapp.bootstrap.ui.state.ScreenStatus
import com.melsuhaimi.sleepapp.bootstrap.ui.theme.LocalSleepSpacing

data class FoundationUiState(
    val route: AppRoute,
    val status: ScreenStatus,
    val title: String,
    val message: String,
)

sealed interface FoundationAction {
    data object Retry : FoundationAction
    data object OpenSettings : FoundationAction
}

@Composable
fun FoundationScreen(
    state: FoundationUiState,
    onAction: (FoundationAction) -> Unit,
    modifier: Modifier = Modifier,
) {
    val spacing = LocalSleepSpacing.current

    Surface(
        modifier = modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(spacing.large),
            verticalArrangement = Arrangement.spacedBy(spacing.medium),
        ) {
            Text(
                text = state.title,
                style = MaterialTheme.typography.headlineMedium,
                color = MaterialTheme.colorScheme.onBackground,
            )
            Text(
                text = state.status.name,
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = state.message,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onBackground,
            )
        }
    }
}
