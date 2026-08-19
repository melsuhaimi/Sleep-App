package com.melsuhaimi.sleepapp.bootstrap.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Mineral,
    onPrimary = Color.White,
    background = OffWhite,
    onBackground = WarmCharcoal,
    surface = OffWhite,
    onSurface = WarmCharcoal,
    outline = MutedWarmGray,
)

private val DarkColors = darkColorScheme(
    primary = MutedWarmGray,
    onPrimary = DeepNeutral,
    background = DeepNeutral,
    onBackground = OffWhite,
    surface = WarmCharcoal,
    onSurface = OffWhite,
    outline = Mineral,
)

@Composable
fun SleepTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = SleepTypography,
        content = content,
    )
}
