package com.qgrid.mobile.ui

import com.qgrid.mobile.game.LEVEL_COUNT
import com.qgrid.mobile.game.GameReducer
import com.qgrid.mobile.game.GameState
import com.qgrid.mobile.game.GameStatus
import com.qgrid.mobile.game.LevelFactory
import com.qgrid.mobile.game.PathSelection
import com.qgrid.mobile.game.ProgressState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AppUiStateTest {
    private val levels = LevelFactory.createLevels()

    @Test
    fun completedCountIgnoresInvalidProgressIds() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 2, LEVEL_COUNT + 1, 999),
            ),
        )

        assertEquals(2, state.completedCount)
    }

    @Test
    fun nextLevelIgnoresInvalidCompletedIds() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = setOf(1, LEVEL_COUNT + 1),
            ),
        )

        assertEquals(2, state.nextLevelId)
    }

    @Test
    fun nextLevelUsesLastPlayedLevelWhenItIsStillIncomplete() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 2),
                lastLevelId = 7,
            ),
        )

        assertEquals(7, state.nextLevelId)
        assertTrue(state.shouldShowContinueAction)
    }

    @Test
    fun nextLevelFallsBackToFirstIncompleteWhenLastPlayedLevelIsComplete() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 2, 7),
                lastLevelId = 7,
            ),
        )

        assertEquals(3, state.nextLevelId)
        assertTrue(state.shouldShowContinueAction)
    }

    @Test
    fun startActionRemainsForFreshProgressOnFirstLevel() {
        val state = AppUiState(levels = levels)

        assertEquals(1, state.nextLevelId)
        assertFalse(state.shouldShowContinueAction)
    }

    @Test
    fun emptyLevelListDoesNotExposeContinueAction() {
        val state = AppUiState(
            levels = emptyList(),
            progress = ProgressState(
                completedLevelIds = setOf(1, 2, 99),
                lastLevelId = 5,
            ),
        )

        assertTrue(state.displayLevels.isEmpty())
        assertEquals(0, state.totalLevelCount)
        assertEquals(0, state.completedCount)
        assertEquals(1, state.nextLevelId)
        assertFalse(state.shouldShowContinueAction)
        assertFalse(state.currentGameHasNumberedNextLevel)
        assertFalse(state.currentGameCompletesAllLevels)
    }

    @Test
    fun continueActionShowsWhenFreshProgressStoppedOnLaterLevel() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(lastLevelId = 5),
        )

        assertEquals(5, state.nextLevelId)
        assertTrue(state.shouldShowContinueAction)
    }

    @Test
    fun completedCountUsesOnlyAvailableLevelIdsWhenListIsSparseOrReordered() {
        val sparseLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
        )
        val state = AppUiState(
            levels = sparseLevels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 2, 3, 99),
            ),
        )

        assertEquals(2, state.completedCount)
    }

    @Test
    fun totalLevelCountUsesDistinctAvailableLevelIdsWhenListIsSparseOrReordered() {
        val sparseLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
            levels[0],
        )
        val state = AppUiState(levels = sparseLevels)

        assertEquals(listOf(1, 3, 5), state.displayLevels.map { it.id })
        assertEquals(3, state.totalLevelCount)
    }

    @Test
    fun completedCountUsesDistinctAvailableLevelIdsWhenListContainsDuplicates() {
        val duplicateLevels = listOf(
            levels[2],
            levels[0],
            levels[2],
            levels[4],
        )
        val state = AppUiState(
            levels = duplicateLevels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 3, 5, 99),
            ),
        )

        assertEquals(listOf(1, 3, 5), state.displayLevels.map { it.id })
        assertEquals(3, state.completedCount)
        assertEquals(3, state.totalLevelCount)
    }

    @Test
    fun nextLevelUsesSortedAvailableIdsWhenListIsSparseOrReordered() {
        val sparseLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
        )
        val state = AppUiState(
            levels = sparseLevels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 2, 99),
            ),
        )

        assertEquals(3, state.nextLevelId)
    }

    @Test
    fun nextLevelUsesDistinctAvailableIdsWhenListContainsDuplicates() {
        val duplicateLevels = listOf(
            levels[2],
            levels[0],
            levels[2],
            levels[4],
        )
        val state = AppUiState(
            levels = duplicateLevels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 3),
                lastLevelId = 3,
            ),
        )

        assertEquals(5, state.nextLevelId)
        assertTrue(state.shouldShowContinueAction)
    }

    @Test
    fun currentGameLastLevelUsesHighestAvailableLevelIdWhenListIsSparseOrReordered() {
        val sparseLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
        )

        assertFalse(
            AppUiState(
                levels = sparseLevels,
                currentLevel = levels[2],
                gameState = GameReducer.newGame(levels[2]),
            ).currentGameIsLastLevel,
        )
        assertTrue(
            AppUiState(
                levels = sparseLevels,
                currentLevel = levels[2],
                gameState = GameReducer.newGame(levels[2]),
            ).currentGameHasNumberedNextLevel,
        )
        assertTrue(
            AppUiState(
                levels = sparseLevels,
                currentLevel = levels[4],
                gameState = GameReducer.newGame(levels[4]),
            ).currentGameIsLastLevel,
        )
        assertFalse(
            AppUiState(
                levels = sparseLevels,
                currentLevel = levels[4],
                gameState = GameReducer.newGame(levels[4]),
            ).currentGameHasNumberedNextLevel,
        )
    }

    @Test
    fun currentGameNextLevelUsesGameStateLevelWhenCurrentLevelIsStale() {
        val state = AppUiState(
            levels = levels,
            currentLevel = levels[0],
            gameState = wonGame(levels[4]),
        )

        assertEquals(6, state.currentGameNextLevelId)
        assertTrue(state.currentGameHasNumberedNextLevel)
    }

    @Test
    fun currentGameNextLevelFallsBackToContinueRouteWhenNoGameIsOpen() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(lastLevelId = 7),
        )

        assertEquals(7, state.nextLevelId)
        assertEquals(7, state.currentGameNextLevelId)
    }

    @Test
    fun currentGameDoesNotCompleteAllLevelsJustBecauseHighestLevelWasWon() {
        val lastLevel = levels.last()
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 2, 3),
            ),
            currentLevel = lastLevel,
            gameState = wonGame(lastLevel),
        )

        assertTrue(state.currentGameIsLastLevel)
        assertFalse(state.currentGameCompletesAllLevels)
    }

    @Test
    fun currentGameCompletesAllLevelsWhenLastMissingLevelIsWon() {
        val lastLevel = levels.last()
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = (1 until LEVEL_COUNT).toSet(),
            ),
            currentLevel = lastLevel,
            gameState = wonGame(lastLevel),
        )

        assertTrue(state.currentGameIsLastLevel)
        assertTrue(state.currentGameCompletesAllLevels)
    }

    @Test
    fun currentGameCompletesAllLevelsUsesDistinctAvailableLevelIds() {
        val duplicateLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
            levels[4],
        )
        val state = AppUiState(
            levels = duplicateLevels,
            progress = ProgressState(
                completedLevelIds = setOf(1, 3),
            ),
            currentLevel = levels[4],
            gameState = wonGame(levels[4]),
        )

        assertEquals(3, state.totalLevelCount)
        assertTrue(state.currentGameIsLastLevel)
        assertTrue(state.currentGameCompletesAllLevels)
    }

    @Test
    fun nextLevelStaysOnLastLevelWhenAllValidLevelsAreComplete() {
        val state = AppUiState(
            levels = levels,
            progress = ProgressState(
                completedLevelIds = (1..LEVEL_COUNT).toSet() + 999,
            ),
        )

        assertEquals(LEVEL_COUNT, state.completedCount)
        assertEquals(LEVEL_COUNT, state.nextLevelId)
        assertEquals(LEVEL_COUNT, state.totalLevelCount)
    }

    private fun wonGame(level: com.qgrid.mobile.game.LevelDefinition): GameState {
        return GameState(
            level = level,
            selection = PathSelection(level.solutionPath),
            status = GameStatus.WON,
        )
    }
}
