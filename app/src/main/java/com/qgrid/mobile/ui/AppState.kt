package com.qgrid.mobile.ui

import com.qgrid.mobile.game.GameState
import com.qgrid.mobile.game.GameStatus
import com.qgrid.mobile.game.LevelDefinition
import com.qgrid.mobile.game.ProgressState
import com.qgrid.mobile.game.ProgressRules

enum class AppScreen {
    LOADING,
    ONBOARDING,
    HOME,
    LEVELS,
    GAME,
    SETTINGS,
    ABOUT,
}

data class AppUiState(
    val screen: AppScreen = AppScreen.LOADING,
    val levels: List<LevelDefinition> = emptyList(),
    val progress: ProgressState = ProgressState(),
    val currentLevel: LevelDefinition? = null,
    val gameState: GameState? = null,
    val gameReturnScreen: AppScreen = AppScreen.LEVELS,
) {
    val displayLevels: List<LevelDefinition> = levels.distinctBy { it.id }.sortedBy { it.id }
    private val orderedLevelIds: List<Int> = displayLevels.map { it.id }
    private val availableLevelIds: Set<Int> = orderedLevelIds.toSet()
    private val sanitizedCompletedLevelIds: Set<Int> = ProgressRules.sanitizedCompletedLevelIds(
        progress.completedLevelIds,
    ).intersect(availableLevelIds)
    private val hasLevels: Boolean = orderedLevelIds.isNotEmpty()
    private val firstLevelId: Int? = orderedLevelIds.firstOrNull()
    private val lastPlayedLevelId: Int? = progress.lastLevelId.takeIf { it in availableLevelIds }
    val totalLevelCount: Int = orderedLevelIds.size
    val completedCount: Int = sanitizedCompletedLevelIds.size
    val nextLevelId: Int = lastPlayedLevelId?.takeIf { it !in sanitizedCompletedLevelIds }
        ?: orderedLevelIds.firstOrNull { it !in sanitizedCompletedLevelIds }
        ?: orderedLevelIds.lastOrNull()
        ?: 1
    val shouldShowContinueAction: Boolean = hasLevels &&
        (completedCount > 0 || nextLevelId != firstLevelId)
    val currentGameIsLastLevel: Boolean = gameState?.level?.id == orderedLevelIds.lastOrNull()
    val currentGameHasNumberedNextLevel: Boolean = gameState?.level?.id
        ?.let { currentLevelId -> orderedLevelIds.any { it > currentLevelId } }
        ?: false
    val currentGameNextLevelId: Int = gameState?.level?.id
        ?.let { currentLevelId -> LevelNavigation.nextLevelId(levels, currentLevelId) }
        ?: nextLevelId
    private val currentWonLevelId: Int? = gameState
        ?.takeIf { it.status == GameStatus.WON }
        ?.level
        ?.id
        ?.takeIf { it in availableLevelIds }
    private val projectedCompletedLevelIds: Set<Int> = currentWonLevelId
        ?.let { sanitizedCompletedLevelIds + it }
        ?: sanitizedCompletedLevelIds
    val currentGameCompletesAllLevels: Boolean = hasLevels &&
        projectedCompletedLevelIds.size == totalLevelCount
}
