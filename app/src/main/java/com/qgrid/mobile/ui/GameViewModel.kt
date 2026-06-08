package com.qgrid.mobile.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.qgrid.mobile.data.ProgressRepository
import com.qgrid.mobile.game.CellPosition
import com.qgrid.mobile.game.GameReducer
import com.qgrid.mobile.game.GameStatus
import com.qgrid.mobile.game.LevelFactory
import com.qgrid.mobile.game.ProgressRules
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class GameViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val repository = ProgressRepository(application)
    private val levels = LevelFactory.createLevels()

    private val _state = MutableStateFlow(
        AppUiState(
            levels = levels,
            currentLevel = levels.firstOrNull(),
        ),
    )
    val state: StateFlow<AppUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            repository.progressFlow.collect { progress ->
                _state.update { current ->
                    val screen = if (current.screen == AppScreen.LOADING) {
                        if (progress.onboardingSeen) AppScreen.HOME else AppScreen.ONBOARDING
                    } else {
                        current.screen
                    }
                    current.copy(
                        screen = screen,
                        progress = progress,
                    )
                }
            }
        }
    }

    fun finishOnboarding() {
        _state.update { it.copy(screen = AppScreen.HOME) }
        viewModelScope.launch {
            repository.setOnboardingSeen()
        }
    }

    fun openHome() {
        _state.update { it.copy(screen = AppScreen.HOME) }
    }

    fun openLevels() {
        _state.update { it.copy(screen = AppScreen.LEVELS) }
    }

    fun openGameReturnScreen() {
        _state.update { it.copy(screen = it.gameReturnScreen.safeGameReturnScreen()) }
    }

    fun openSettings() {
        _state.update { it.copy(screen = AppScreen.SETTINGS) }
    }

    fun openAbout() {
        _state.update { it.copy(screen = AppScreen.ABOUT) }
    }

    fun startLevelFromLevels(levelId: Int) {
        startLevel(levelId, AppScreen.LEVELS)
    }

    private fun startLevel(levelId: Int, returnScreen: AppScreen) {
        val level = LevelNavigation.levelForId(levels, levelId) ?: return
        _state.update {
            it.copy(
                screen = AppScreen.GAME,
                currentLevel = level,
                gameState = GameReducer.newGame(level),
                gameReturnScreen = returnScreen.safeGameReturnScreen(),
            )
        }
        viewModelScope.launch {
            repository.setLastLevel(level.id)
        }
    }

    fun continueGame() {
        startLevel(_state.value.nextLevelId, AppScreen.HOME)
    }

    fun selectCell(position: CellPosition) {
        val currentGame = _state.value.gameState ?: return
        val nextGame = GameReducer.selectCell(currentGame, position)
        val levelWasJustCompleted = currentGame.status != GameStatus.WON && nextGame.status == GameStatus.WON
        _state.update { current ->
            current.copy(
                gameState = nextGame,
                progress = if (levelWasJustCompleted) {
                    ProgressRules.withCompletedLevel(current.progress, nextGame.level.id)
                } else {
                    current.progress
                },
            )
        }
        if (levelWasJustCompleted) {
            viewModelScope.launch {
                repository.markLevelCompleted(nextGame.level.id)
            }
        }
    }

    fun undo() {
        val currentGame = _state.value.gameState ?: return
        _state.update { it.copy(gameState = GameReducer.undo(currentGame)) }
    }

    fun reset() {
        val currentGame = _state.value.gameState ?: return
        _state.update { it.copy(gameState = GameReducer.reset(currentGame)) }
    }

    fun hint() {
        val currentGame = _state.value.gameState ?: return
        _state.update { it.copy(gameState = GameReducer.hint(currentGame)) }
    }

    fun nextLevel() {
        val current = _state.value
        startLevel(current.currentGameNextLevelId, current.gameReturnScreen)
    }

    fun replayCurrentLevel() {
        val current = _state.value
        val level = current.gameState?.level ?: current.currentLevel ?: return
        _state.update {
            it.copy(
                screen = AppScreen.GAME,
                currentLevel = level,
                gameState = GameReducer.newGame(level),
            )
        }
        viewModelScope.launch {
            repository.setLastLevel(level.id)
        }
    }

    fun setHapticsEnabled(enabled: Boolean) {
        _state.update {
            it.copy(progress = it.progress.copy(settings = it.progress.settings.copy(hapticsEnabled = enabled)))
        }
        viewModelScope.launch {
            repository.setHapticsEnabled(enabled)
        }
    }

    fun setHighContrast(enabled: Boolean) {
        _state.update {
            it.copy(progress = it.progress.copy(settings = it.progress.settings.copy(highContrast = enabled)))
        }
        viewModelScope.launch {
            repository.setHighContrast(enabled)
        }
    }

    fun setReduceMotion(enabled: Boolean) {
        _state.update {
            it.copy(progress = it.progress.copy(settings = it.progress.settings.copy(reduceMotion = enabled)))
        }
        viewModelScope.launch {
            repository.setReduceMotion(enabled)
        }
    }

    private fun AppScreen.safeGameReturnScreen(): AppScreen {
        return if (this == AppScreen.LEVELS) AppScreen.LEVELS else AppScreen.HOME
    }
}
