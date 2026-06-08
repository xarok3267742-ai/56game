package com.qgrid.mobile.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val NormalScheme = lightColorScheme(
    primary = LeafGreen,
    onPrimary = Paper,
    secondary = Clay,
    onSecondary = Paper,
    tertiary = SoftBlue,
    onTertiary = Paper,
    background = FieldMist,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = ColorTokens.SurfaceVariant,
    onSurfaceVariant = ColorTokens.OnSurfaceVariant,
    error = LineRed,
    onError = Paper,
)

private val HighContrastScheme = lightColorScheme(
    primary = HighContrastGreen,
    onPrimary = Paper,
    secondary = Clay,
    onSecondary = Paper,
    tertiary = SoftBlue,
    onTertiary = Paper,
    background = Paper,
    onBackground = Ink,
    surface = Paper,
    onSurface = Ink,
    surfaceVariant = ColorTokens.HighContrastSurfaceVariant,
    onSurfaceVariant = Ink,
    error = LineRed,
    onError = Paper,
)

private val Line56Typography = Typography(
    headlineLarge = Typography().headlineLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 30.sp,
        lineHeight = 36.sp,
    ),
    headlineMedium = Typography().headlineMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 24.sp,
        lineHeight = 30.sp,
    ),
    titleLarge = Typography().titleLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 20.sp,
        lineHeight = 26.sp,
    ),
    titleMedium = Typography().titleMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 16.sp,
        lineHeight = 22.sp,
    ),
    bodyLarge = Typography().bodyLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontSize = 16.sp,
        lineHeight = 24.sp,
    ),
    bodyMedium = Typography().bodyMedium.copy(
        fontFamily = FontFamily.SansSerif,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    labelLarge = Typography().labelLarge.copy(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 15.sp,
        lineHeight = 20.sp,
    ),
)

private val Line56Shapes = Shapes(
    extraSmall = RoundedCornerShape(4.dp),
    small = RoundedCornerShape(6.dp),
    medium = RoundedCornerShape(8.dp),
    large = RoundedCornerShape(8.dp),
    extraLarge = RoundedCornerShape(8.dp),
)

@Composable
fun Line56Theme(
    highContrast: Boolean,
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (highContrast) HighContrastScheme else NormalScheme,
        typography = Line56Typography,
        shapes = Line56Shapes,
        content = content,
    )
}

private object ColorTokens {
    val SurfaceVariant = androidx.compose.ui.graphics.Color(0xFFE3ECE6)
    val OnSurfaceVariant = androidx.compose.ui.graphics.Color(0xFF3D4C46)
    val HighContrastSurfaceVariant = androidx.compose.ui.graphics.Color(0xFFEAF1EC)
}
