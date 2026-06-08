package com.qgrid.mobile.ui

import com.qgrid.mobile.game.LEVEL_COUNT
import com.qgrid.mobile.game.LevelFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LevelNavigationTest {
    private val levels = LevelFactory.createLevels()

    @Test
    fun levelForIdClampsLowRequestedIdsToFirstLevel() {
        val level = LevelNavigation.levelForId(levels, -20)

        assertEquals(1, level?.id)
    }

    @Test
    fun levelForIdClampsHighRequestedIdsToLastLevel() {
        val level = LevelNavigation.levelForId(levels, LEVEL_COUNT + 20)

        assertEquals(LEVEL_COUNT, level?.id)
    }

    @Test
    fun levelForIdReturnsNullWhenNoLevelsExist() {
        assertNull(LevelNavigation.levelForId(emptyList(), 1))
    }

    @Test
    fun levelForIdUsesAvailableLevelIdsWhenListIsSparseOrReordered() {
        val sparseLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
        )

        assertEquals(1, LevelNavigation.levelForId(sparseLevels, -20)?.id)
        assertEquals(3, LevelNavigation.levelForId(sparseLevels, 2)?.id)
        assertEquals(5, LevelNavigation.levelForId(sparseLevels, LEVEL_COUNT + 20)?.id)
    }

    @Test
    fun levelForIdUsesDistinctAvailableIdsWhenListContainsDuplicates() {
        val duplicateLevels = listOf(
            levels[2],
            levels[0],
            levels[2],
            levels[4],
        )

        assertEquals(3, LevelNavigation.levelForId(duplicateLevels, 2)?.id)
        assertEquals(5, LevelNavigation.levelForId(duplicateLevels, 4)?.id)
    }

    @Test
    fun nextLevelIdAdvancesUntilLastLevel() {
        assertEquals(2, LevelNavigation.nextLevelId(levels, 1))
        assertEquals(LEVEL_COUNT, LevelNavigation.nextLevelId(levels, LEVEL_COUNT))
        assertEquals(1, LevelNavigation.nextLevelId(emptyList(), 1))
    }

    @Test
    fun nextLevelIdUsesAvailableLevelIdsWhenListIsSparseOrReordered() {
        val sparseLevels = listOf(
            levels[4],
            levels[0],
            levels[2],
        )

        assertEquals(3, LevelNavigation.nextLevelId(sparseLevels, 1))
        assertEquals(5, LevelNavigation.nextLevelId(sparseLevels, 3))
        assertEquals(5, LevelNavigation.nextLevelId(sparseLevels, 5))
        assertEquals(1, LevelNavigation.nextLevelId(sparseLevels, null))
    }

    @Test
    fun nextLevelIdUsesDistinctAvailableIdsWhenListContainsDuplicates() {
        val duplicateLevels = listOf(
            levels[2],
            levels[0],
            levels[2],
            levels[4],
        )

        assertEquals(1, LevelNavigation.nextLevelId(duplicateLevels, null))
        assertEquals(3, LevelNavigation.nextLevelId(duplicateLevels, 1))
        assertEquals(5, LevelNavigation.nextLevelId(duplicateLevels, 3))
    }
}
