package com.qgrid.mobile.ui

import androidx.activity.compose.BackHandler
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.material3.LinearProgressIndicator
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.StrokeCap
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
        Spacer(Modifier.height(20.dp))
        Text(
            text = stringResource(R.string.home_body),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(24.dp))
        ProgressPanel(
            completed = state.completedCount,
            total = state.totalLevelCount,
        )
        Spacer(Modifier.height(28.dp))
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
    ScreenColumn {
        Header(
            title = stringResource(R.string.choose_level),
            onBack = onBack,
        )
        Spacer(Modifier.height(16.dp))
        state.displayLevels.chunked(4).forEach { row ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                row.forEach { level ->
                    LevelTile(
                        level = level,
                        completed = level.id in state.progress.completedLevelIds,
                        onClick = { onLevel(level.id) },
                        modifier = Modifier.weight(1f),
                    )
                }
                repeat(4 - row.size) {
                    Spacer(Modifier.weight(1f))
                }
            }
            Spacer(Modifier.height(8.dp))
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
            SumPanel(game)
            Spacer(Modifier.height(16.dp))
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
            SumPanel(game)
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
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .windowInsetsPadding(WindowInsets.safeDrawing)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = verticalArrangement,
        content = content,
    )
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
        tonalElevation = 1.dp,
        shadowElevation = 1.dp,
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
            LinearProgressIndicator(
                progress = { progressValue },
                modifier = Modifier
                    .fillMaxWidth()
                    .semantics {
                        contentDescription = progressDescription
                        progressBarRangeInfo = ProgressBarRangeInfo(progressValue, 0f..1f)
                },
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant,
                drawStopIndicator = {},
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
    Surface(
        modifier = modifier
            .aspectRatio(1f)
            .semantics { contentDescription = description }
            .clickable(
                role = Role.Button,
                onClick = onClick,
            ),
        shape = MaterialTheme.shapes.medium,
        color = if (completed) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface,
        tonalElevation = if (completed) 2.dp else 1.dp,
        shadowElevation = 1.dp,
    ) {
        Box(contentAlignment = Alignment.Center) {
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
private fun SumPanel(game: GameState) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
        shadowElevation = 1.dp,
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SumMetric(
                label = stringResource(R.string.current_sum),
                value = game.currentSum.toString(),
                modifier = Modifier.weight(1f),
            )
            SumMetric(
                label = stringResource(R.string.target_sum),
                value = TARGET_SUM.toString(),
                modifier = Modifier.weight(1f),
            )
            SumMetric(
                label = stringResource(R.string.remaining_sum),
                value = game.remaining.coerceAtLeast(0).toString(),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun SumMetric(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
        )
        Text(
            text = value,
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.primary,
        )
    }
}

@Composable
private fun GameMessageText(game: GameState) {
    Text(
        text = messageText(game.message),
        style = MaterialTheme.typography.bodyMedium,
        color = if (game.status == GameStatus.EXCEEDED) {
            MaterialTheme.colorScheme.error
        } else {
            MaterialTheme.colorScheme.onSurfaceVariant
        },
        modifier = Modifier.fillMaxWidth(),
        textAlign = TextAlign.Center,
    )
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
    Box(
        modifier = modifier
            .aspectRatio(1f),
    ) {
        val board = game.level.board
        Canvas(modifier = Modifier.matchParentSize()) {
            val cellSize = size.width / board.size
            val centers = game.selection.positions.map {
                Offset(
                    x = it.col * cellSize + cellSize / 2,
                    y = it.row * cellSize + cellSize / 2,
                )
            }
            centers.zipWithNext().forEach { (start, end) ->
                drawLine(
                    color = lineColor,
                    start = start,
                    end = end,
                    strokeWidth = 10.dp.toPx(),
                    cap = StrokeCap.Round,
                )
            }
        }
        Column(Modifier.fillMaxSize()) {
            for (row in 0 until board.size) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    for (col in 0 until board.size) {
                        val position = CellPosition(row, col)
                        val cell = board.cellAt(position)
                        CellTile(
                            cell = cell,
                            selected = game.selection.contains(position),
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
                if (row != board.size - 1) Spacer(Modifier.height(6.dp))
            }
        }
    }
}

@Composable
private fun CellTile(
    cell: Cell,
    selected: Boolean,
    hinted: Boolean,
    exceeded: Boolean,
    enabled: Boolean,
    settings: SettingsState,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colorScheme = MaterialTheme.colorScheme
    val containerColor = when {
        exceeded -> colorScheme.error
        selected -> colorScheme.primary
        hinted -> if (settings.highContrast) HighContrastGold else WarmGold
        else -> colorScheme.surface
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
        targetValue = if (selected || hinted) 3.dp else 1.dp,
        animationSpec = tween(durationMillis = animationDuration),
        label = "cellTonalElevation",
    )
    val animatedShadowElevation = animateDpAsState(
        targetValue = if (selected || hinted) 2.dp else 1.dp,
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
        tonalElevation = animatedTonalElevation.value,
        shadowElevation = animatedShadowElevation.value,
    ) {
        Box(contentAlignment = Alignment.Center) {
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
        val useStackedLayout = maxWidth < 330.dp
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
