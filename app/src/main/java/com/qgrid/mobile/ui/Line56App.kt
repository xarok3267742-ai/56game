package com.qgrid.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.GridView
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.ProgressBarRangeInfo
import androidx.compose.ui.semantics.progressBarRangeInfo
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.qgrid.mobile.R
import com.qgrid.mobile.game.Cell
import com.qgrid.mobile.game.CellPosition
import com.qgrid.mobile.game.Difficulty
import com.qgrid.mobile.game.GameMessage
import com.qgrid.mobile.game.GameState
import com.qgrid.mobile.game.GameStatus
import com.qgrid.mobile.game.LevelDefinition
import com.qgrid.mobile.game.SettingsState
import com.qgrid.mobile.game.TARGET_SUM
import com.qgrid.mobile.ui.theme.HighContrastGold
import com.qgrid.mobile.ui.theme.WarmGold

@Composable
fun Line56App(
    state: AppUiState,
    viewModel: GameViewModel,
) {
    BackHandler(
        enabled = state.screen != AppScreen.LOADING &&
            state.screen != AppScreen.ONBOARDING &&
            state.screen != AppScreen.HOME,
    ) {
        when (state.screen) {
            AppScreen.GAME -> viewModel.openGameReturnScreen()
            else -> viewModel.openHome()
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        when (state.screen) {
            AppScreen.LOADING -> LoadingScreen()
            AppScreen.ONBOARDING -> OnboardingScreen(
                onStart = viewModel::finishOnboarding,
            )
            AppScreen.HOME -> HomeScreen(
                state = state,
                onContinue = viewModel::continueGame,
                onLevels = viewModel::openLevels,
                onSettings = viewModel::openSettings,
                onAbout = viewModel::openAbout,
            )
            AppScreen.LEVELS -> LevelsScreen(
                state = state,
                onBack = viewModel::openHome,
                onLevel = viewModel::startLevelFromLevels,
            )
            AppScreen.GAME -> GameScreen(
                state = state,
                onBack = viewModel::openGameReturnScreen,
                onLevels = viewModel::openLevels,
                onCell = viewModel::selectCell,
                onUndo = viewModel::undo,
                onReset = viewModel::reset,
                onHint = viewModel::hint,
                onNext = viewModel::nextLevel,
                onReplay = viewModel::replayCurrentLevel,
            )
            AppScreen.SETTINGS -> SettingsScreen(
                settings = state.progress.settings,
                onBack = viewModel::openHome,
                onHaptics = viewModel::setHapticsEnabled,
                onHighContrast = viewModel::setHighContrast,
                onReduceMotion = viewModel::setReduceMotion,
            )
            AppScreen.ABOUT -> AboutScreen(
                onBack = viewModel::openHome,
            )
        }
    }
}

@Composable
private fun LoadingScreen() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = stringResource(R.string.loading),
            style = MaterialTheme.typography.titleMedium,
        )
    }
}

@Composable
private fun OnboardingScreen(
    onStart: () -> Unit,
) {
    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val compactHeight = maxHeight < 720.dp
        val landscapeCompact = maxHeight < 520.dp && maxWidth > maxHeight
        if (landscapeCompact) {
            LandscapeOnboardingScreen(onStart = onStart)
            return@BoxWithConstraints
        }
        val topSpacer = when {
            compactHeight -> 10.dp
            maxHeight < 820.dp -> 44.dp
            else -> 72.dp
        }
        ScreenColumn(
            verticalArrangement = Arrangement.Top,
        ) {
            Spacer(Modifier.height(topSpacer))
            NumberMark(
                modifier = Modifier.align(Alignment.CenterHorizontally),
                size = if (compactHeight) 64 else 72,
            )
            Spacer(Modifier.height(if (compactHeight) 12.dp else 14.dp))
            Text(
                text = stringResource(R.string.onboarding_title),
                style = MaterialTheme.typography.headlineLarge,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.onboarding_subtitle),
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth(),
            )
            if (!compactHeight) {
                Spacer(Modifier.height(12.dp))
                Surface(
                    shape = MaterialTheme.shapes.large,
                    color = MaterialTheme.colorScheme.primary,
                    shadowElevation = 2.dp,
                    modifier = Modifier
                        .align(Alignment.CenterHorizontally)
                        .widthIn(max = 164.dp),
                ) {
                    MiniRoutePreview(
                        modifier = Modifier
                            .padding(12.dp)
                            .size(132.dp),
                    )
                }
            }
            Spacer(Modifier.height(if (compactHeight) 14.dp else 16.dp))
            RuleRow("1", stringResource(R.string.onboarding_rule_one))
            RuleRow("2", stringResource(R.string.onboarding_rule_two))
            RuleRow("3", stringResource(R.string.onboarding_rule_three))
            Spacer(Modifier.height(if (compactHeight) 14.dp else 16.dp))
            Button(
                onClick = onStart,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Filled.PlayArrow, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.start_game))
            }
        }
    }
}

@Composable
private fun LandscapeOnboardingScreen(
    onStart: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .padding(horizontal = 26.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.spacedBy(28.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(
            modifier = Modifier.weight(0.9f),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            NumberMark(size = 54)
            Spacer(Modifier.height(10.dp))
            Text(
                text = stringResource(R.string.onboarding_title),
                style = MaterialTheme.typography.headlineMedium,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = stringResource(R.string.onboarding_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.fillMaxWidth(),
            )
        }
        Column(
            modifier = Modifier.weight(1.6f),
            verticalArrangement = Arrangement.Center,
        ) {
            CompactRuleRow("1", stringResource(R.string.onboarding_rule_one))
            CompactRuleRow("2", stringResource(R.string.onboarding_rule_two))
            CompactRuleRow("3", stringResource(R.string.onboarding_rule_three))
            Spacer(Modifier.height(10.dp))
            Button(
                onClick = onStart,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Filled.PlayArrow, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.start_game))
            }
        }
    }
}

@Composable
private fun HomeScreen(
    state: AppUiState,
    onContinue: () -> Unit,
    onLevels: () -> Unit,
    onSettings: () -> Unit,
    onAbout: () -> Unit,
) {
    ScreenColumn {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = stringResource(R.string.app_name),
                    style = MaterialTheme.typography.headlineLarge,
                )
                Text(
                    text = stringResource(R.string.home_daily),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            IconButton(onClick = onSettings) {
                Icon(
                    imageVector = Icons.Filled.Settings,
                    contentDescription = stringResource(R.string.settings),
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        HomeRoutePanel(
            completed = state.completedCount,
            total = state.totalLevelCount,
        )
        Spacer(Modifier.height(16.dp))
        Text(
            text = stringResource(R.string.home_body),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(18.dp))
        ProgressPanel(
            completed = state.completedCount,
            total = state.totalLevelCount,
        )
        Spacer(Modifier.height(22.dp))
        Button(
            onClick = onContinue,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(Icons.Filled.PlayArrow, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text(
                text = if (state.shouldShowContinueAction) {
                    stringResource(R.string.continue_game)
                } else {
                    stringResource(R.string.start_game)
                },
            )
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onLevels,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(Icons.Filled.GridView, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text(stringResource(R.string.levels))
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(
            onClick = onAbout,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Icon(Icons.Filled.Info, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text(stringResource(R.string.about))
        }
    }
}

@Composable
private fun LevelsScreen(
    state: AppUiState,
    onBack: () -> Unit,
    onLevel: (Int) -> Unit,
) {
    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val columns = if (maxWidth < 360.dp) 4 else 6
        ScreenColumn {
            Header(
                title = stringResource(R.string.choose_level),
                onBack = onBack,
            )
            Spacer(Modifier.height(16.dp))
            LevelMapPanel(
                levels = state.displayLevels,
                completedLevelIds = state.progress.completedLevelIds,
                columns = columns,
                onLevel = onLevel,
            )
        }
    }
}

@Composable
private fun HomeRoutePanel(
    completed: Int,
    total: Int,
) {
    val boundedTotal = total.coerceAtLeast(0)
    val boundedCompleted = completed.coerceIn(0, boundedTotal)
    val progressValue = if (boundedTotal == 0) {
        0f
    } else {
        boundedCompleted / boundedTotal.toFloat()
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.primary,
        shadowElevation = 4.dp,
    ) {
        Box {
            RoutePanelBackdrop(
                progress = progressValue,
                modifier = Modifier.matchParentSize(),
            )
            Row(
                modifier = Modifier.padding(14.dp),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                MiniRoutePreview(
                    modifier = Modifier
                        .size(136.dp)
                        .weight(0.92f, fill = false),
                )
                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(
                        text = TARGET_SUM.toString(),
                        style = MaterialTheme.typography.headlineLarge.copy(fontSize = 38.sp),
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                    Text(
                        text = stringResource(R.string.target_sum),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.88f),
                    )
                    Spacer(Modifier.height(12.dp))
                    HomeMilestoneStrip(
                        progress = progressValue,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = stringResource(R.string.home_daily),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.84f),
                    )
                }
            }
        }
    }
}

@Composable
private fun RoutePanelBackdrop(
    progress: Float,
    modifier: Modifier = Modifier,
) {
    val boundedProgress = progress.coerceIn(0f, 1f)
    val gridColor = Color.White.copy(alpha = 0.08f)
    Canvas(modifier = modifier) {
        val step = 24.dp.toPx()
        var x = -step * 2f
        while (x < size.width + step * 2f) {
            drawLine(
                color = gridColor,
                start = Offset(x, 0f),
                end = Offset(x + size.height * 0.38f, size.height),
                strokeWidth = 1.dp.toPx(),
            )
            x += step
        }
        val railStart = Offset(size.width * 0.58f, size.height * 0.22f)
        val railEnd = Offset(size.width * 0.94f, size.height * 0.22f)
        drawLine(
            color = Color.White.copy(alpha = 0.20f),
            start = railStart,
            end = railEnd,
            strokeWidth = 5.dp.toPx(),
            cap = StrokeCap.Round,
        )
        if (boundedProgress > 0f) {
            drawLine(
                color = WarmGold.copy(alpha = 0.74f),
                start = railStart,
                end = Offset(
                    x = railStart.x + (railEnd.x - railStart.x) * boundedProgress,
                    y = railStart.y,
                ),
                strokeWidth = 5.dp.toPx(),
                cap = StrokeCap.Round,
            )
        }
        drawCircle(
            color = WarmGold.copy(alpha = 0.30f),
            radius = 42.dp.toPx(),
            center = Offset(size.width * 0.98f, size.height * 0.78f),
            style = Stroke(width = 2.dp.toPx()),
        )
    }
}

@Composable
private fun HomeMilestoneStrip(
    progress: Float,
    modifier: Modifier = Modifier,
) {
    val boundedProgress = progress.coerceIn(0f, 1f)
    Canvas(
        modifier = modifier.height(26.dp),
    ) {
        val y = size.height / 2f
        val start = 4.dp.toPx()
        val end = size.width - 4.dp.toPx()
        val activeEnd = start + (end - start) * boundedProgress
        drawLine(
            color = Color.White.copy(alpha = 0.24f),
            start = Offset(start, y),
            end = Offset(end, y),
            strokeWidth = 4.dp.toPx(),
            cap = StrokeCap.Round,
        )
        if (boundedProgress > 0f) {
            drawLine(
                color = WarmGold,
                start = Offset(start, y),
                end = Offset(activeEnd, y),
                strokeWidth = 4.dp.toPx(),
                cap = StrokeCap.Round,
            )
        }
        repeat(6) { index ->
            val x = start + (end - start) * (index / 5f)
            val filled = boundedProgress > 0f && x <= activeEnd + 0.5f
            drawCircle(
                color = if (filled) WarmGold else Color.White.copy(alpha = 0.42f),
                radius = if (filled) 4.5.dp.toPx() else 3.5.dp.toPx(),
                center = Offset(x, y),
            )
        }
    }
}

@Composable
private fun LevelMapPanel(
    levels: List<LevelDefinition>,
    completedLevelIds: Set<Int>,
    columns: Int,
    onLevel: (Int) -> Unit,
) {
    val rows = levels.chunked(columns).mapIndexed { index, row ->
        if (index % 2 == 0) row else row.reversed()
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.94f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)),
        tonalElevation = 1.dp,
        shadowElevation = 2.dp,
    ) {
        Box(Modifier.padding(10.dp)) {
            LevelMapConnectors(
                rows = rows,
                completedLevelIds = completedLevelIds,
                modifier = Modifier.matchParentSize(),
            )
            Column {
                rows.forEachIndexed { rowIndex, row ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        row.forEach { level ->
                            LevelTile(
                                level = level,
                                completed = level.id in completedLevelIds,
                                onClick = { onLevel(level.id) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                        repeat(columns - row.size) {
                            Spacer(Modifier.weight(1f))
                        }
                    }
                    if (rowIndex != rows.lastIndex) {
                        Spacer(Modifier.height(7.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun LevelMapConnectors(
    rows: List<List<LevelDefinition>>,
    completedLevelIds: Set<Int>,
    modifier: Modifier = Modifier,
) {
    val connectorColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)
    val activeConnectorColor = WarmGold.copy(alpha = 0.62f)
    Canvas(modifier = modifier) {
        if (rows.isEmpty()) return@Canvas
        val maxColumns = rows.maxOf { it.size }.coerceAtLeast(1)
        val cellWidth = size.width / maxColumns
        val cellHeight = size.height / rows.size
        val centers = rows.flatMapIndexed { rowIndex, row ->
            row.mapIndexed { colIndex, level ->
                level.id to Offset(
                    x = colIndex * cellWidth + cellWidth / 2f,
                    y = rowIndex * cellHeight + cellHeight / 2f,
                )
            }
        }
        centers.zipWithNext().forEach { (start, end) ->
            val bothCompleted = start.first in completedLevelIds && end.first in completedLevelIds
            drawLine(
                color = if (bothCompleted) activeConnectorColor else connectorColor,
                start = start.second,
                end = end.second,
                strokeWidth = if (bothCompleted) 4.dp.toPx() else 2.dp.toPx(),
                cap = StrokeCap.Round,
            )
        }
    }
}

@Composable
private fun MiniRoutePreview(
    modifier: Modifier = Modifier,
) {
    val cells = listOf(
        9, 12, 7, 5,
        4, 11, 15, 6,
        8, 10, 3, 14,
        2, 13, 1, 16,
    )
    val route = listOf(1, 5, 6, 10, 11, 14)
    val lineColor = MaterialTheme.colorScheme.secondary
    val selectedColor = MaterialTheme.colorScheme.surface
    val selectedContentColor = MaterialTheme.colorScheme.primary
    val idleColor = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.14f)
    val idleContentColor = MaterialTheme.colorScheme.onPrimary
    Box(modifier = modifier.aspectRatio(1f)) {
        Canvas(modifier = Modifier.matchParentSize()) {
            val step = size.width / 4f
            val centers = route.map { index ->
                Offset(
                    x = (index % 4) * step + step / 2f,
                    y = (index / 4) * step + step / 2f,
                )
            }
            centers.zipWithNext().forEach { (start, end) ->
                drawLine(
                    color = lineColor.copy(alpha = 0.86f),
                    start = start,
                    end = end,
                    strokeWidth = 8.dp.toPx(),
                    cap = StrokeCap.Round,
                )
            }
        }
        Column(Modifier.fillMaxSize()) {
            repeat(4) { row ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                ) {
                    repeat(4) { col ->
                        val index = row * 4 + col
                        val selected = index in route
                        Surface(
                            modifier = Modifier
                                .weight(1f)
                                .aspectRatio(1f),
                            shape = MaterialTheme.shapes.medium,
                            color = if (selected) selectedColor else idleColor,
                            border = if (selected) {
                                BorderStroke(1.dp, lineColor.copy(alpha = 0.72f))
                            } else {
                                null
                            },
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Text(
                                    text = cells[index].toString(),
                                    style = MaterialTheme.typography.labelLarge,
                                    color = if (selected) selectedContentColor else idleContentColor,
                                )
                            }
                        }
                    }
                }
                if (row != 3) Spacer(Modifier.height(5.dp))
            }
        }
    }
}

@Composable
private fun GameScreen(
    state: AppUiState,
    onBack: () -> Unit,
    onLevels: () -> Unit,
    onCell: (CellPosition) -> Unit,
    onUndo: () -> Unit,
    onReset: () -> Unit,
    onHint: () -> Unit,
    onNext: () -> Unit,
    onReplay: () -> Unit,
) {
    val game = state.gameState ?: return LoadingScreen()
    val haptic = LocalHapticFeedback.current
    val selectedCount = game.selection.positions.size
    val hapticsEnabled = state.progress.settings.hapticsEnabled
    val previousSelectedCount = remember(game.level.id) { mutableIntStateOf(selectedCount) }
    val previousStatus = remember(game.level.id) { mutableStateOf(game.status) }

    LaunchedEffect(game.level.id, game.status, selectedCount, hapticsEnabled) {
        if (hapticsEnabled && game.status == GameStatus.WON && previousStatus.value != GameStatus.WON) {
            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
        }
        if (hapticsEnabled && game.status != GameStatus.WON && selectedCount > previousSelectedCount.intValue) {
            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
        }
        previousSelectedCount.intValue = selectedCount
        previousStatus.value = game.status
    }
    val handleCell: (CellPosition) -> Unit = onCell

    BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
        val landscapeCompact = maxWidth > maxHeight && maxHeight < 600.dp
        if (landscapeCompact) {
            LandscapeGameScreen(
                state = state,
                game = game,
                onBack = onBack,
                onLevels = onLevels,
                onCell = handleCell,
                onUndo = onUndo,
                onHint = onHint,
                onReset = onReset,
                onNext = onNext,
                onReplay = onReplay,
                boardSize = (maxHeight - 28.dp).coerceAtMost(430.dp),
            )
            return@BoxWithConstraints
        }

        ScreenColumn {
            val title = levelTitle(game.level)
            Header(
                title = title,
                subtitle = difficultyTitle(game.level.difficulty),
                onBack = onBack,
            )
            Spacer(Modifier.height(14.dp))
            RouteDashboardPanel(game, state.progress.settings)
            Spacer(Modifier.height(10.dp))
            RouteTraceStrip(game, state.progress.settings)
            Spacer(Modifier.height(14.dp))
            CenteredGameBoard(
                game = game,
                settings = state.progress.settings,
                onCell = handleCell,
            )
            Spacer(Modifier.height(14.dp))
            GameMessageText(game)
            Spacer(Modifier.height(14.dp))
            ActionBar(
                onUndo = onUndo,
                onHint = onHint,
                onReset = onReset,
                undoEnabled = game.selection.positions.isNotEmpty() && game.status != GameStatus.WON,
                hintEnabled = game.status == GameStatus.PLAYING,
                resetEnabled = game.selection.positions.isNotEmpty() && game.status != GameStatus.WON,
            )
            if (game.status == GameStatus.WON) {
                Spacer(Modifier.height(16.dp))
                ResultPanel(
                    hasNextLevel = state.currentGameHasNumberedNextLevel,
                    allLevelsComplete = state.currentGameCompletesAllLevels,
                    onNext = onNext,
                    onLevels = onLevels,
                    onReplay = onReplay,
                )
            }
        }
    }
}

@Composable
private fun LandscapeGameScreen(
    state: AppUiState,
    game: GameState,
    onBack: () -> Unit,
    onLevels: () -> Unit,
    onCell: (CellPosition) -> Unit,
    onUndo: () -> Unit,
    onHint: () -> Unit,
    onReset: () -> Unit,
    onNext: () -> Unit,
    onReplay: () -> Unit,
    boardSize: Dp,
) {
    Row(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .padding(horizontal = 20.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.spacedBy(18.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(
            modifier = Modifier
                .weight(1f)
                .fillMaxHeight()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.Center,
        ) {
            val title = levelTitle(game.level)
            Header(
                title = title,
                subtitle = difficultyTitle(game.level.difficulty),
                onBack = onBack,
            )
            Spacer(Modifier.height(10.dp))
            RouteDashboardPanel(game, state.progress.settings)
            Spacer(Modifier.height(8.dp))
            RouteTraceStrip(game, state.progress.settings)
            Spacer(Modifier.height(10.dp))
            GameMessageText(game)
            Spacer(Modifier.height(10.dp))
            ActionBar(
                onUndo = onUndo,
                onHint = onHint,
                onReset = onReset,
                undoEnabled = game.selection.positions.isNotEmpty() && game.status != GameStatus.WON,
                hintEnabled = game.status == GameStatus.PLAYING,
                resetEnabled = game.selection.positions.isNotEmpty() && game.status != GameStatus.WON,
            )
            if (game.status == GameStatus.WON) {
                Spacer(Modifier.height(10.dp))
                ResultPanel(
                    hasNextLevel = state.currentGameHasNumberedNextLevel,
                    allLevelsComplete = state.currentGameCompletesAllLevels,
                    onNext = onNext,
                    onLevels = onLevels,
                    onReplay = onReplay,
                )
            }
        }
        GameBoard(
            game = game,
            settings = state.progress.settings,
            onCell = onCell,
            modifier = Modifier.size(boardSize),
        )
    }
}

@Composable
private fun SettingsScreen(
    settings: SettingsState,
    onBack: () -> Unit,
    onHaptics: (Boolean) -> Unit,
    onHighContrast: (Boolean) -> Unit,
    onReduceMotion: (Boolean) -> Unit,
) {
    ScreenColumn {
        Header(
            title = stringResource(R.string.settings),
            onBack = onBack,
        )
        Spacer(Modifier.height(20.dp))
        SettingsRow(
            title = stringResource(R.string.haptics),
            description = stringResource(R.string.haptics_description),
            checked = settings.hapticsEnabled,
            onCheckedChange = onHaptics,
        )
        SettingsRow(
            title = stringResource(R.string.high_contrast),
            description = stringResource(R.string.high_contrast_description),
            checked = settings.highContrast,
            onCheckedChange = onHighContrast,
        )
        SettingsRow(
            title = stringResource(R.string.reduce_motion),
            description = stringResource(R.string.reduce_motion_description),
            checked = settings.reduceMotion,
            onCheckedChange = onReduceMotion,
        )
    }
}

@Composable
private fun AboutScreen(
    onBack: () -> Unit,
) {
    ScreenColumn {
        Header(
            title = stringResource(R.string.about),
            onBack = onBack,
        )
        Spacer(Modifier.height(20.dp))
        Text(
            text = stringResource(R.string.about_body),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(24.dp))
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = MaterialTheme.shapes.large,
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 1.dp,
            shadowElevation = 1.dp,
        ) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    text = stringResource(R.string.privacy_title),
                    style = MaterialTheme.typography.titleLarge,
                )
                Spacer(Modifier.height(8.dp))
                Text(
                    text = stringResource(R.string.privacy_body),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(Modifier.height(12.dp))
                PrivacyPoint(text = stringResource(R.string.privacy_data_local))
                PrivacyPoint(text = stringResource(R.string.privacy_no_services))
                PrivacyPoint(text = stringResource(R.string.privacy_no_backup))
                PrivacyPoint(text = stringResource(R.string.privacy_delete))
            }
        }
    }
}

@Composable
private fun PrivacyPoint(
    text: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Text(
            text = "•",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text = text,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ScreenColumn(
    verticalArrangement: Arrangement.Vertical = Arrangement.Top,
    content: @Composable ColumnScope.() -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.72f),
                    ),
                ),
            ),
    ) {
        CoordinateBackdrop(Modifier.matchParentSize())
        Column(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.safeDrawing)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = verticalArrangement,
            content = content,
        )
    }
}

@Composable
private fun CoordinateBackdrop(
    modifier: Modifier = Modifier,
) {
    val gridColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.052f)
    val accentColor = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.09f)
    val guideColor = WarmGold.copy(alpha = 0.11f)
    Canvas(modifier = modifier) {
        val step = 36.dp.toPx()
        val dash = PathEffect.dashPathEffect(floatArrayOf(8.dp.toPx(), 12.dp.toPx()))
        var x = -step
        while (x < size.width + step) {
            drawLine(
                color = gridColor,
                start = Offset(x, 0f),
                end = Offset(x + size.height * 0.22f, size.height),
                strokeWidth = 1.dp.toPx(),
                pathEffect = dash,
            )
            x += step
        }
        var y = step * 0.5f
        while (y < size.height) {
            drawLine(
                color = gridColor,
                start = Offset(0f, y),
                end = Offset(size.width, y),
                strokeWidth = 1.dp.toPx(),
                pathEffect = dash,
            )
            y += step
        }
        drawLine(
            color = guideColor,
            start = Offset(size.width * 0.10f, size.height * 0.20f),
            end = Offset(size.width * 0.78f, size.height * 0.06f),
            strokeWidth = 3.dp.toPx(),
            cap = StrokeCap.Round,
        )
        drawLine(
            color = guideColor.copy(alpha = 0.72f),
            start = Offset(size.width * 0.42f, size.height * 0.98f),
            end = Offset(size.width * 0.94f, size.height * 0.74f),
            strokeWidth = 3.dp.toPx(),
            cap = StrokeCap.Round,
        )
        drawRoundRect(
            color = accentColor,
            topLeft = Offset(size.width * 0.06f, size.height * 0.08f),
            size = Size(size.width * 0.42f, 64.dp.toPx()),
            cornerRadius = CornerRadius(8.dp.toPx(), 8.dp.toPx()),
            style = Stroke(width = 1.dp.toPx()),
        )
    }
}

@Composable
private fun Header(
    title: String,
    onBack: () -> Unit,
    subtitle: String? = null,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = onBack) {
            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                contentDescription = stringResource(R.string.back),
            )
        }
        Spacer(Modifier.width(8.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleLarge,
            )
            if (subtitle != null) {
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun NumberMark(
    modifier: Modifier = Modifier,
    size: Int = 88,
) {
    Image(
        painter = painterResource(R.drawable.ic_launcher_imagegen),
        contentDescription = null,
        modifier = modifier.size(size.dp),
    )
}

@Composable
private fun RuleRow(
    number: String,
    text: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Surface(
            modifier = Modifier.size(30.dp),
            shape = MaterialTheme.shapes.medium,
            color = MaterialTheme.colorScheme.secondary,
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    text = number,
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSecondary,
                )
            }
        }
        Spacer(Modifier.width(12.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun CompactRuleRow(
    number: String,
    text: String,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            modifier = Modifier.size(28.dp),
            shape = MaterialTheme.shapes.medium,
            color = MaterialTheme.colorScheme.secondary,
        ) {
            Box(contentAlignment = Alignment.Center) {
                Text(
                    text = number,
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.onSecondary,
                )
            }
        }
        Spacer(Modifier.width(10.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun ProgressPanel(
    completed: Int,
    total: Int,
) {
    val boundedTotal = total.coerceAtLeast(0)
    val boundedCompleted = completed.coerceIn(0, boundedTotal)
    val progressValue = if (boundedTotal == 0) {
        0f
    } else {
        boundedCompleted / boundedTotal.toFloat()
    }
    val progressDescription = stringResource(
        R.string.progress_description,
        boundedCompleted,
        boundedTotal,
    )
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.14f)),
        tonalElevation = 1.dp,
        shadowElevation = 2.dp,
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.home_progress),
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text = "$completed / $total",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            Spacer(Modifier.height(10.dp))
            HomeProgressRail(
                progress = progressValue,
                progressDescription = progressDescription,
                modifier = Modifier
                    .fillMaxWidth(),
            )
        }
    }
}

@Composable
private fun HomeProgressRail(
    progress: Float,
    progressDescription: String,
    modifier: Modifier = Modifier,
) {
    val progressValue = progress.coerceIn(0f, 1f)
    val trackColor = MaterialTheme.colorScheme.surfaceVariant
    val activeColor = MaterialTheme.colorScheme.primary
    Canvas(
        modifier = modifier
            .height(30.dp)
            .semantics {
                contentDescription = progressDescription
                progressBarRangeInfo = ProgressBarRangeInfo(progressValue, 0f..1f)
            },
    ) {
        val y = size.height / 2f
        val start = 2.dp.toPx()
        val end = size.width - 2.dp.toPx()
        val activeEnd = start + (end - start) * progressValue
        drawLine(
            color = trackColor,
            start = Offset(start, y),
            end = Offset(end, y),
            strokeWidth = 8.dp.toPx(),
            cap = StrokeCap.Round,
        )
        if (progressValue > 0f) {
            drawLine(
                color = activeColor,
                start = Offset(start, y),
                end = Offset(activeEnd, y),
                strokeWidth = 8.dp.toPx(),
                cap = StrokeCap.Round,
            )
        }
        repeat(6) { index ->
            val x = start + (end - start) * (index / 5f)
            val filled = progressValue > 0f && x <= activeEnd + 0.5f
            drawCircle(
                color = if (filled) WarmGold else Color.White,
                radius = if (filled) 5.dp.toPx() else 4.dp.toPx(),
                center = Offset(x, y),
            )
            drawCircle(
                color = activeColor.copy(alpha = if (filled) 0.34f else 0.22f),
                radius = 7.dp.toPx(),
                center = Offset(x, y),
                style = Stroke(width = 1.dp.toPx()),
            )
        }
    }
}

@Composable
private fun LevelTile(
    level: LevelDefinition,
    completed: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val title = levelTitle(level)
    val status = if (completed) stringResource(R.string.completed) else stringResource(R.string.available)
    val description = stringResource(R.string.level_tile_description, title, status)
    val accentColor = difficultyAccent(level.difficulty)
    Surface(
        modifier = modifier
            .aspectRatio(1f)
            .semantics { contentDescription = description }
            .clickable(
                role = Role.Button,
                onClick = onClick,
            ),
        shape = MaterialTheme.shapes.medium,
        color = if (completed) {
            MaterialTheme.colorScheme.primary
        } else {
            MaterialTheme.colorScheme.surface.copy(alpha = 0.96f)
        },
        border = BorderStroke(
            width = 1.dp,
            color = if (completed) {
                WarmGold.copy(alpha = 0.86f)
            } else {
                accentColor.copy(alpha = 0.34f)
            },
        ),
        tonalElevation = if (completed) 3.dp else 1.dp,
        shadowElevation = if (completed) 2.dp else 1.dp,
    ) {
        Box(contentAlignment = Alignment.Center) {
            Canvas(modifier = Modifier.matchParentSize()) {
                drawLine(
                    color = accentColor.copy(alpha = if (completed) 0.42f else 0.24f),
                    start = Offset(size.width * 0.18f, size.height * 0.80f),
                    end = Offset(size.width * 0.82f, size.height * 0.20f),
                    strokeWidth = 3.dp.toPx(),
                    cap = StrokeCap.Round,
                )
                drawCircle(
                    color = if (completed) WarmGold else accentColor.copy(alpha = 0.36f),
                    radius = 5.dp.toPx(),
                    center = Offset(12.dp.toPx(), size.height - 12.dp.toPx()),
                )
            }
            if (completed) {
                Icon(
                    imageVector = Icons.Filled.Check,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(6.dp)
                        .size(16.dp),
                )
            }
            Text(
                text = level.id.toString(),
                style = MaterialTheme.typography.titleLarge,
                color = if (completed) {
                    MaterialTheme.colorScheme.onPrimary
                } else {
                    MaterialTheme.colorScheme.onSurface
                },
            )
        }
    }
}

@Composable
private fun difficultyAccent(difficulty: Difficulty): Color {
    return when (difficulty) {
        Difficulty.EASY -> MaterialTheme.colorScheme.primary
        Difficulty.MEDIUM -> MaterialTheme.colorScheme.secondary
        Difficulty.HARD -> MaterialTheme.colorScheme.tertiary
    }
}

@Composable
private fun levelTitle(level: LevelDefinition): String = stringResource(
    R.string.level_title_format,
    level.id,
)

@Composable
private fun difficultyTitle(difficulty: Difficulty): String = stringResource(
    when (difficulty) {
        Difficulty.EASY -> R.string.difficulty_easy
        Difficulty.MEDIUM -> R.string.difficulty_medium
        Difficulty.HARD -> R.string.difficulty_hard
    },
)

@Composable
private fun RouteDashboardPanel(
    game: GameState,
    settings: SettingsState,
) {
    val progressValue = (game.currentSum / TARGET_SUM.toFloat()).coerceIn(0f, 1f)
    val animatedProgress = animateFloatAsState(
        targetValue = progressValue,
        animationSpec = tween(durationMillis = if (settings.reduceMotion) 0 else 180),
        label = "sumProgress",
    )
    val railColor = if (game.status == GameStatus.EXCEEDED) {
        MaterialTheme.colorScheme.error
    } else {
        WarmGold
    }
    val isExceeded = game.status == GameStatus.EXCEEDED
    val panelColor = if (isExceeded) {
        MaterialTheme.colorScheme.error.copy(alpha = 0.10f)
    } else {
        MaterialTheme.colorScheme.primary
    }
    val primaryContentColor = if (isExceeded) {
        MaterialTheme.colorScheme.error
    } else {
        MaterialTheme.colorScheme.onPrimary
    }
    val secondaryContentColor = if (isExceeded) {
        MaterialTheme.colorScheme.error.copy(alpha = 0.76f)
    } else {
        MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.78f)
    }
    val panelDescription = stringResource(
        R.string.sum_panel_description,
        game.currentSum,
        TARGET_SUM,
        game.remaining.coerceAtLeast(0),
    )
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .semantics { contentDescription = panelDescription },
        shape = MaterialTheme.shapes.large,
        color = panelColor,
        border = BorderStroke(1.dp, railColor.copy(alpha = 0.34f)),
        tonalElevation = 1.dp,
        shadowElevation = 4.dp,
    ) {
        Box {
            DashboardBackdrop(
                progress = animatedProgress.value,
                exceeded = isExceeded,
                modifier = Modifier.matchParentSize(),
            )
            Column(Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1.18f)) {
                        Text(
                            text = stringResource(R.string.current_sum),
                            style = MaterialTheme.typography.bodyMedium,
                            color = secondaryContentColor,
                            maxLines = 1,
                        )
                        Text(
                            text = game.currentSum.toString(),
                            style = MaterialTheme.typography.headlineLarge.copy(fontSize = 44.sp),
                            color = primaryContentColor,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                        )
                    }
                    ConsoleReadout(
                        label = stringResource(R.string.target_sum),
                        value = TARGET_SUM.toString(),
                        contentColor = primaryContentColor,
                        mutedColor = secondaryContentColor,
                        modifier = Modifier.weight(0.72f),
                    )
                    ConsoleReadout(
                        label = stringResource(R.string.remaining_sum),
                        value = game.remaining.coerceAtLeast(0).toString(),
                        contentColor = primaryContentColor,
                        mutedColor = secondaryContentColor,
                        modifier = Modifier.weight(0.82f),
                    )
                }
                Spacer(Modifier.height(8.dp))
                RouteProgressRail(
                    progress = animatedProgress.value,
                    exceeded = isExceeded,
                    onDark = !isExceeded,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun DashboardBackdrop(
    progress: Float,
    exceeded: Boolean,
    modifier: Modifier = Modifier,
) {
    val boundedProgress = progress.coerceIn(0f, 1f)
    val guideColor = if (exceeded) {
        MaterialTheme.colorScheme.error.copy(alpha = 0.14f)
    } else {
        Color.White.copy(alpha = 0.12f)
    }
    val pulseColor = if (exceeded) {
        MaterialTheme.colorScheme.error.copy(alpha = 0.10f)
    } else {
        WarmGold.copy(alpha = 0.16f)
    }
    Canvas(modifier = modifier) {
        val step = 22.dp.toPx()
        val dash = PathEffect.dashPathEffect(floatArrayOf(7.dp.toPx(), 10.dp.toPx()))
        var x = -step
        while (x < size.width + step) {
            drawLine(
                color = guideColor,
                start = Offset(x, 0f),
                end = Offset(x + size.height * 0.34f, size.height),
                strokeWidth = 1.dp.toPx(),
                pathEffect = dash,
            )
            x += step
        }
        drawCircle(
            color = pulseColor,
            radius = (44.dp.toPx() + 34.dp.toPx() * boundedProgress),
            center = Offset(size.width * 0.86f, size.height * 0.36f),
            style = Stroke(width = 2.dp.toPx()),
        )
        drawCircle(
            color = pulseColor.copy(alpha = pulseColor.alpha * 0.62f),
            radius = 24.dp.toPx(),
            center = Offset(size.width * 0.10f, size.height * 0.88f),
            style = Stroke(width = 2.dp.toPx()),
        )
    }
}

@Composable
private fun ConsoleReadout(
    label: String,
    value: String,
    contentColor: Color,
    mutedColor: Color,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.End,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = mutedColor,
            maxLines = 1,
            textAlign = TextAlign.End,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.headlineMedium,
            color = contentColor,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            textAlign = TextAlign.End,
        )
    }
}

@Composable
private fun RouteProgressRail(
    progress: Float,
    exceeded: Boolean,
    onDark: Boolean,
    modifier: Modifier = Modifier,
) {
    val boundedProgress = progress.coerceIn(0f, 1f)
    val trackColor = if (onDark) {
        Color.White.copy(alpha = 0.24f)
    } else {
        MaterialTheme.colorScheme.surfaceVariant
    }
    val activeColor = if (exceeded) MaterialTheme.colorScheme.error else WarmGold
    val markerColor = if (onDark) Color.White else MaterialTheme.colorScheme.primary
    Canvas(
        modifier = modifier
            .height(34.dp)
            .semantics {
                progressBarRangeInfo = ProgressBarRangeInfo(boundedProgress, 0f..1f)
            },
    ) {
        val railHeight = 10.dp.toPx()
        val railTop = size.height / 2f - railHeight / 2f
        val corner = CornerRadius(railHeight / 2f, railHeight / 2f)
        drawRoundRect(
            color = trackColor,
            topLeft = Offset(0f, railTop),
            size = Size(size.width, railHeight),
            cornerRadius = corner,
        )
        if (boundedProgress > 0f) {
            drawRoundRect(
                color = activeColor,
                topLeft = Offset(0f, railTop),
                size = Size(size.width * boundedProgress, railHeight),
                cornerRadius = corner,
            )
        }
        repeat(7) { index ->
            val x = size.width * (index / 6f)
            drawLine(
                color = if (onDark) {
                    Color.White.copy(alpha = 0.62f)
                } else {
                    Color.White.copy(alpha = 0.78f)
                },
                start = Offset(x, railTop - 4.dp.toPx()),
                end = Offset(x, railTop + railHeight + 4.dp.toPx()),
                strokeWidth = 1.dp.toPx(),
            )
        }
        drawCircle(
            color = markerColor,
            radius = 5.dp.toPx(),
            center = Offset(size.width, size.height / 2f),
        )
        drawCircle(
            color = Color.White,
            radius = 2.dp.toPx(),
            center = Offset(size.width, size.height / 2f),
        )
    }
}

@Composable
private fun RouteTraceStrip(
    game: GameState,
    settings: SettingsState,
    modifier: Modifier = Modifier,
) {
    val values = game.selection.positions.map { game.level.board.cellAt(it).value }
    val visibleValues = values.takeLast(7)
    val hiddenCount = values.size - visibleValues.size
    val traceDescription = if (values.isEmpty()) {
        stringResource(R.string.route_trace_empty, TARGET_SUM)
    } else {
        stringResource(
            R.string.route_trace_description,
            values.joinToString(separator = " + "),
            game.currentSum,
            TARGET_SUM,
        )
    }
    val accentColor = when {
        game.status == GameStatus.EXCEEDED -> MaterialTheme.colorScheme.error
        settings.highContrast -> HighContrastGold
        else -> WarmGold
    }
    val primaryGuideColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f)
    val tertiaryGuideColor = MaterialTheme.colorScheme.tertiary.copy(alpha = 0.08f)
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .semantics { contentDescription = traceDescription },
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.96f),
        border = BorderStroke(1.dp, accentColor.copy(alpha = 0.32f)),
        shadowElevation = 1.dp,
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
        ) {
            Canvas(Modifier.matchParentSize()) {
                val y = size.height / 2f
                drawLine(
                    color = accentColor.copy(alpha = 0.30f),
                    start = Offset(18.dp.toPx(), y),
                    end = Offset(size.width - 18.dp.toPx(), y),
                    strokeWidth = 3.dp.toPx(),
                    cap = StrokeCap.Round,
                )
                drawLine(
                    color = primaryGuideColor,
                    start = Offset(size.width * 0.12f, 0f),
                    end = Offset(size.width * 0.28f, size.height),
                    strokeWidth = 1.dp.toPx(),
                )
                drawLine(
                    color = tertiaryGuideColor,
                    start = Offset(size.width * 0.70f, 0f),
                    end = Offset(size.width * 0.54f, size.height),
                    strokeWidth = 1.dp.toPx(),
                )
            }
            Row(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(5.dp, Alignment.CenterHorizontally),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (values.isEmpty()) {
                    repeat(4) {
                        RouteTraceNode(
                            text = "",
                            active = false,
                            target = false,
                            exceeded = false,
                        )
                    }
                } else {
                    if (hiddenCount > 0) {
                        RouteTraceNode(
                            text = "+$hiddenCount",
                            active = false,
                            target = false,
                            exceeded = false,
                        )
                    }
                    visibleValues.forEachIndexed { index, value ->
                        RouteTraceNode(
                            text = value.toString(),
                            active = true,
                            target = false,
                            exceeded = game.status == GameStatus.EXCEEDED &&
                                index == visibleValues.lastIndex,
                        )
                    }
                }
                RouteTraceNode(
                    text = TARGET_SUM.toString(),
                    active = game.status == GameStatus.WON,
                    target = true,
                    exceeded = false,
                )
            }
        }
    }
}

@Composable
private fun RouteTraceNode(
    text: String,
    active: Boolean,
    target: Boolean,
    exceeded: Boolean,
    modifier: Modifier = Modifier,
) {
    val colorScheme = MaterialTheme.colorScheme
    val nodeColor = when {
        exceeded -> colorScheme.error
        target && active -> colorScheme.primary
        target -> colorScheme.surfaceVariant
        active -> WarmGold
        else -> colorScheme.surface
    }
    val strokeColor = when {
        exceeded -> colorScheme.error
        active || target -> colorScheme.primary
        else -> colorScheme.onSurface.copy(alpha = 0.12f)
    }
    val contentColor = when {
        exceeded -> colorScheme.onError
        target && active -> colorScheme.onPrimary
        active -> colorScheme.onSurface
        else -> colorScheme.onSurfaceVariant
    }
    Box(
        modifier = modifier.size(30.dp),
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.matchParentSize()) {
            val corner = CornerRadius(8.dp.toPx(), 8.dp.toPx())
            drawRoundRect(
                color = nodeColor,
                cornerRadius = corner,
            )
            drawRoundRect(
                color = strokeColor.copy(alpha = if (active || target) 0.54f else 0.32f),
                cornerRadius = corner,
                style = Stroke(width = 1.dp.toPx()),
            )
            if (!active && !target && !exceeded) {
                drawCircle(
                    color = strokeColor.copy(alpha = 0.18f),
                    radius = 3.dp.toPx(),
                    center = Offset(size.width / 2f, size.height / 2f),
                )
            }
        }
        if (text.isNotEmpty()) {
            Text(
                text = text,
                style = MaterialTheme.typography.labelLarge.copy(fontSize = if (text.length > 2) 10.sp else 12.sp),
                color = contentColor,
                textAlign = TextAlign.Center,
                maxLines = 1,
            )
        }
    }
}

@Composable
private fun GameMessageText(game: GameState) {
    val accentColor = if (game.status == GameStatus.EXCEEDED) {
        MaterialTheme.colorScheme.error
    } else {
        MaterialTheme.colorScheme.primary
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        color = accentColor.copy(alpha = if (game.status == GameStatus.EXCEEDED) 0.08f else 0.06f),
        border = BorderStroke(1.dp, accentColor.copy(alpha = 0.20f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Canvas(Modifier.size(12.dp)) {
                drawCircle(
                    color = accentColor,
                    radius = size.minDimension / 2f,
                    center = Offset(size.width / 2f, size.height / 2f),
                )
                drawCircle(
                    color = Color.White.copy(alpha = 0.78f),
                    radius = size.minDimension / 5f,
                    center = Offset(size.width / 2f, size.height / 2f),
                )
            }
            Spacer(Modifier.width(8.dp))
            Text(
                text = messageText(game.message),
                style = MaterialTheme.typography.bodyMedium,
                color = if (game.status == GameStatus.EXCEEDED) {
                    MaterialTheme.colorScheme.error
                } else {
                    MaterialTheme.colorScheme.onSurfaceVariant
                },
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun CenteredGameBoard(
    game: GameState,
    settings: SettingsState,
    onCell: (CellPosition) -> Unit,
) {
    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = Alignment.Center,
    ) {
        GameBoard(
            game = game,
            settings = settings,
            onCell = onCell,
            modifier = Modifier
                .fillMaxWidth()
                .widthIn(max = 460.dp),
        )
    }
}

@Composable
private fun GameBoard(
    game: GameState,
    settings: SettingsState,
    onCell: (CellPosition) -> Unit,
    modifier: Modifier = Modifier,
) {
    val lineColor = if (settings.highContrast) HighContrastGold else WarmGold
    val routeShadowColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.20f)
    val boardFrameColor = MaterialTheme.colorScheme.primary
    Surface(
        modifier = modifier
            .aspectRatio(1f),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.98f),
        border = BorderStroke(1.dp, lineColor.copy(alpha = 0.44f)),
        shadowElevation = 4.dp,
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(9.dp),
        ) {
            val board = game.level.board
            Canvas(modifier = Modifier.matchParentSize()) {
                val cellSize = size.width / board.size
                val gridColor = boardFrameColor.copy(alpha = if (settings.highContrast) 0.28f else 0.10f)
                val diagonalColor = boardFrameColor.copy(alpha = if (settings.highContrast) 0.18f else 0.055f)
                val dash = PathEffect.dashPathEffect(floatArrayOf(7.dp.toPx(), 9.dp.toPx()))
                var guide = -size.height
                while (guide < size.width + size.height) {
                    drawLine(
                        color = diagonalColor,
                        start = Offset(guide, size.height),
                        end = Offset(guide + size.height, 0f),
                        strokeWidth = 1.dp.toPx(),
                        pathEffect = dash,
                    )
                    guide += 28.dp.toPx()
                }
                for (index in 1 until board.size) {
                    val offset = index * cellSize
                    drawLine(
                        color = gridColor,
                        start = Offset(offset, 0f),
                        end = Offset(offset, size.height),
                        strokeWidth = 1.dp.toPx(),
                    )
                    drawLine(
                        color = gridColor,
                        start = Offset(0f, offset),
                        end = Offset(size.width, offset),
                        strokeWidth = 1.dp.toPx(),
                    )
                }
                val centers = game.selection.positions.map {
                    Offset(
                        x = it.col * cellSize + cellSize / 2,
                        y = it.row * cellSize + cellSize / 2,
                    )
                }
                centers.zipWithNext().forEach { (start, end) ->
                    drawLine(
                        color = routeShadowColor,
                        start = start,
                        end = end,
                        strokeWidth = 17.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                    drawLine(
                        color = lineColor,
                        start = start,
                        end = end,
                        strokeWidth = 10.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                }
                centers.forEach { center ->
                    drawCircle(
                        color = lineColor.copy(alpha = 0.18f),
                        radius = cellSize * 0.38f,
                        center = center,
                    )
                }
            }
            Column(Modifier.fillMaxSize()) {
                for (row in 0 until board.size) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f),
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        for (col in 0 until board.size) {
                            val position = CellPosition(row, col)
                            val cell = board.cellAt(position)
                            CellTile(
                                cell = cell,
                                selected = game.selection.contains(position),
                                selectionIndex = game.selection.positions.indexOf(position)
                                    .takeIf { it >= 0 }
                                    ?.plus(1),
                                hinted = game.hintedPosition == position,
                                exceeded = game.status == GameStatus.EXCEEDED &&
                                    game.selection.last == position,
                                enabled = game.status == GameStatus.PLAYING,
                                settings = settings,
                                onClick = { onCell(position) },
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                    if (row != board.size - 1) Spacer(Modifier.height(7.dp))
                }
            }
        }
    }
}

@Composable
private fun CellTile(
    cell: Cell,
    selected: Boolean,
    selectionIndex: Int?,
    hinted: Boolean,
    exceeded: Boolean,
    enabled: Boolean,
    settings: SettingsState,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colorScheme = MaterialTheme.colorScheme
    val valueAccent = when (cell.value % 3) {
        0 -> colorScheme.primary
        1 -> colorScheme.tertiary
        else -> colorScheme.secondary
    }
    val containerColor = when {
        exceeded -> colorScheme.error
        selected -> colorScheme.primary
        hinted -> if (settings.highContrast) HighContrastGold else WarmGold
        else -> valueAccent.copy(alpha = if (settings.highContrast) 0.12f else 0.085f)
    }
    val contentColor = when {
        exceeded -> colorScheme.onError
        selected -> colorScheme.onPrimary
        hinted -> colorScheme.onSurface
        else -> colorScheme.onSurface
    }
    val animationDuration = if (settings.reduceMotion) 0 else 140
    val animatedContainerColor = animateColorAsState(
        targetValue = containerColor,
        animationSpec = tween(durationMillis = animationDuration),
        label = "cellContainerColor",
    )
    val animatedContentColor = animateColorAsState(
        targetValue = contentColor,
        animationSpec = tween(durationMillis = animationDuration),
        label = "cellContentColor",
    )
    val animatedTonalElevation = animateDpAsState(
        targetValue = if (selected || hinted) 4.dp else 1.dp,
        animationSpec = tween(durationMillis = animationDuration),
        label = "cellTonalElevation",
    )
    val animatedShadowElevation = animateDpAsState(
        targetValue = if (selected || hinted) 3.dp else 1.dp,
        animationSpec = tween(durationMillis = animationDuration),
        label = "cellShadowElevation",
    )
    val stateDescription = when {
        exceeded -> stringResource(R.string.cell_state_exceeded)
        selected -> stringResource(R.string.cell_state_selected)
        hinted -> stringResource(R.string.cell_state_hinted)
        else -> ""
    }
    val description = stringResource(
        R.string.cell_description,
        cell.position.row + 1,
        cell.position.col + 1,
        cell.value,
        stateDescription,
    )
    Surface(
        modifier = modifier
            .aspectRatio(1f)
            .semantics {
                contentDescription = description
            }
            .clickable(
                enabled = enabled,
                role = Role.Button,
                onClick = onClick,
        ),
        shape = MaterialTheme.shapes.medium,
        color = animatedContainerColor.value,
        border = BorderStroke(
            width = if (hinted || exceeded) 2.dp else 1.dp,
            color = when {
                exceeded -> colorScheme.error
                hinted -> if (settings.highContrast) HighContrastGold else WarmGold
                selected -> if (settings.highContrast) HighContrastGold else colorScheme.secondary
                else -> valueAccent.copy(alpha = if (settings.highContrast) 0.44f else 0.24f)
            },
        ),
        tonalElevation = animatedTonalElevation.value,
        shadowElevation = animatedShadowElevation.value,
    ) {
        Box(contentAlignment = Alignment.Center) {
            Canvas(Modifier.matchParentSize()) {
                val stripeColor = when {
                    exceeded -> Color.White.copy(alpha = 0.28f)
                    selected -> if (settings.highContrast) HighContrastGold else WarmGold
                    hinted -> colorScheme.primary
                    else -> valueAccent.copy(alpha = if (settings.highContrast) 0.24f else 0.14f)
                }
                val valueWeight = (cell.value.coerceIn(1, 18) / 18f).coerceIn(0.18f, 1f)
                drawLine(
                    color = stripeColor,
                    start = Offset(size.width * 0.18f, size.height * 0.82f),
                    end = Offset(size.width * 0.82f, size.height * 0.18f),
                    strokeWidth = if (selected || hinted || exceeded) 3.dp.toPx() else 1.dp.toPx(),
                    cap = StrokeCap.Round,
                )
                if (!selected && !hinted && !exceeded) {
                    drawRoundRect(
                        color = valueAccent.copy(alpha = if (settings.highContrast) 0.36f else 0.22f),
                        topLeft = Offset(size.width * 0.16f, size.height * 0.76f),
                        size = Size(
                            width = size.width * 0.68f * valueWeight,
                            height = 3.dp.toPx(),
                        ),
                        cornerRadius = CornerRadius(3.dp.toPx(), 3.dp.toPx()),
                    )
                    drawLine(
                        color = Color.White.copy(alpha = 0.58f),
                        start = Offset(size.width * 0.18f, size.height * 0.18f),
                        end = Offset(size.width * 0.32f, size.height * 0.18f),
                        strokeWidth = 1.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                    drawLine(
                        color = Color.White.copy(alpha = 0.58f),
                        start = Offset(size.width * 0.18f, size.height * 0.18f),
                        end = Offset(size.width * 0.18f, size.height * 0.32f),
                        strokeWidth = 1.dp.toPx(),
                        cap = StrokeCap.Round,
                    )
                }
            }
            if (selected && !exceeded) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(5.dp)
                        .size(9.dp),
                    shape = MaterialTheme.shapes.small,
                    color = if (settings.highContrast) HighContrastGold else WarmGold,
                ) {}
            }
            if (selectionIndex != null && !exceeded) {
                Surface(
                    modifier = Modifier
                        .align(Alignment.TopStart)
                        .padding(4.dp)
                        .size(18.dp),
                    shape = MaterialTheme.shapes.small,
                    color = if (settings.highContrast) HighContrastGold else WarmGold,
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = selectionIndex.toString(),
                            style = MaterialTheme.typography.labelLarge.copy(fontSize = 10.sp),
                            color = colorScheme.onSurface,
                            textAlign = TextAlign.Center,
                            maxLines = 1,
                        )
                    }
                }
            }
            Text(
                text = cell.value.toString(),
                style = MaterialTheme.typography.titleLarge.copy(
                    fontSize = if (cell.value >= 10) 19.sp else 21.sp,
                ),
                color = animatedContentColor.value,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Composable
private fun ActionBar(
    onUndo: () -> Unit,
    onHint: () -> Unit,
    onReset: () -> Unit,
    undoEnabled: Boolean,
    hintEnabled: Boolean,
    resetEnabled: Boolean,
) {
    BoxWithConstraints(modifier = Modifier.fillMaxWidth()) {
        val useStackedLayout = maxWidth < 390.dp
        if (useStackedLayout) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    ActionButton(
                        label = stringResource(R.string.undo),
                        icon = Icons.AutoMirrored.Filled.Undo,
                        onClick = onUndo,
                        enabled = undoEnabled,
                        modifier = Modifier.weight(1f),
                    )
                    ActionButton(
                        label = stringResource(R.string.hint),
                        icon = Icons.Filled.Lightbulb,
                        onClick = onHint,
                        enabled = hintEnabled,
                        modifier = Modifier.weight(1f),
                    )
                }
                ActionButton(
                    label = stringResource(R.string.reset),
                    icon = Icons.Filled.Refresh,
                    onClick = onReset,
                    enabled = resetEnabled,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        } else {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                ActionButton(
                    label = stringResource(R.string.undo),
                    icon = Icons.AutoMirrored.Filled.Undo,
                    onClick = onUndo,
                    enabled = undoEnabled,
                    modifier = Modifier.weight(1f),
                )
                ActionButton(
                    label = stringResource(R.string.hint),
                    icon = Icons.Filled.Lightbulb,
                    onClick = onHint,
                    enabled = hintEnabled,
                    modifier = Modifier.weight(1f),
                )
                ActionButton(
                    label = stringResource(R.string.reset),
                    icon = Icons.Filled.Refresh,
                    onClick = onReset,
                    enabled = resetEnabled,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun ActionButton(
    label: String,
    icon: ImageVector,
    onClick: () -> Unit,
    enabled: Boolean,
    modifier: Modifier = Modifier,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier,
        contentPadding = ButtonDefaults.ButtonWithIconContentPadding,
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(18.dp),
        )
        Spacer(Modifier.width(6.dp))
        Text(
            text = label,
            maxLines = 1,
            fontSize = 13.sp,
        )
    }
}

@Composable
private fun ResultPanel(
    hasNextLevel: Boolean,
    allLevelsComplete: Boolean,
    onNext: () -> Unit,
    onLevels: () -> Unit,
    onReplay: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.primary,
        shadowElevation = 2.dp,
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = stringResource(R.string.level_complete),
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onPrimary,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                text = if (allLevelsComplete) {
                    stringResource(R.string.all_levels_complete)
                } else {
                    stringResource(R.string.level_complete_body)
                },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onPrimary,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(12.dp))
            Button(
                onClick = if (hasNextLevel) onNext else onLevels,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    contentColor = MaterialTheme.colorScheme.primary,
                ),
            ) {
                if (hasNextLevel) {
                    Icon(Icons.Filled.PlayArrow, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.next_level))
                } else {
                    Icon(Icons.Filled.GridView, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.back_to_levels))
                }
            }
            Spacer(Modifier.height(8.dp))
            OutlinedButton(
                onClick = onReplay,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            ) {
                Icon(Icons.Filled.Refresh, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text(stringResource(R.string.replay_level))
            }
        }
    }
}

@Composable
private fun SettingsRow(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .toggleable(
                value = checked,
                role = Role.Switch,
                onValueChange = onCheckedChange,
            )
            .padding(vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = description,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Spacer(Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = null,
        )
    }
}

@Composable
private fun messageText(message: GameMessage): String {
    return when (message) {
        GameMessage.EMPTY_LINE -> stringResource(R.string.empty_line)
        GameMessage.CONTINUE -> stringResource(R.string.continue_line)
        GameMessage.NOT_ON_BOARD -> stringResource(R.string.not_on_board)
        GameMessage.NOT_ADJACENT -> stringResource(R.string.not_adjacent)
        GameMessage.ALREADY_USED -> stringResource(R.string.already_used)
        GameMessage.SUM_EXCEEDED -> stringResource(R.string.sum_exceeded)
        GameMessage.HINT_START -> stringResource(R.string.hint_start)
        GameMessage.HINT_NEXT -> stringResource(R.string.hint_next)
        GameMessage.HINT_REPAIR -> stringResource(R.string.hint_repair)
        GameMessage.WON -> stringResource(R.string.level_complete_body)
    }
}
