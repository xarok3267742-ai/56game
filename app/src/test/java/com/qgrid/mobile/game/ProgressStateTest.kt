package com.qgrid.mobile.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProgressStateTest {
    @Test
    fun defaultsDoNotCollectDataOrAssumeProgress() {
        val progress = ProgressState()

        assertFalse(progress.onboardingSeen)
        assertTrue(progress.completedLevelIds.isEmpty())
        assertEquals(1, progress.lastLevelId)
        assertTrue(progress.settings.hapticsEnabled)
        assertFalse(progress.settings.highContrast)
        assertFalse(progress.settings.reduceMotion)
    }

    @Test
    fun progressRulesDropInvalidCompletedLevelIds() {
        val sanitized = ProgressRules.sanitizedCompletedLevelIds(
            listOf(-1, 0, 1, 1, 2, LEVEL_COUNT, LEVEL_COUNT + 1),
        )

        assertEquals(setOf(1, 2, LEVEL_COUNT), sanitized)
    }

    @Test
    fun progressRulesClampLastLevelId() {
        assertEquals(1, ProgressRules.sanitizedLastLevelId(-10))
        assertEquals(1, ProgressRules.sanitizedLastLevelId(0))
        assertEquals(12, ProgressRules.sanitizedLastLevelId(12))
        assertEquals(LEVEL_COUNT, ProgressRules.sanitizedLastLevelId(LEVEL_COUNT + 10))
    }

    @Test
    fun progressRulesParseCorruptedCompletedLevelCsv() {
        val parsed = ProgressRules.parseCompletedLevelIds(" 2,not-a-level,1,2,0,37, 36 ,,")

        assertEquals(setOf(1, 2, LEVEL_COUNT), parsed)
    }

    @Test
    fun progressRulesSerializeCompletedLevelIdsInStableOrder() {
        val serialized = ProgressRules.serializedCompletedLevelIds(
            listOf(3, LEVEL_COUNT + 1, 1, 3, 2, 0),
        )

        assertEquals("1,2,3", serialized)
    }

    @Test
    fun progressRulesPreserveSettingsWhileSanitizingProgress() {
        val progress = ProgressState(
            onboardingSeen = true,
            completedLevelIds = setOf(1, 99),
            lastLevelId = 99,
            settings = SettingsState(
                hapticsEnabled = false,
                highContrast = true,
                reduceMotion = true,
            ),
        )

        val sanitized = ProgressRules.sanitized(progress)

        assertTrue(sanitized.onboardingSeen)
        assertEquals(setOf(1), sanitized.completedLevelIds)
        assertEquals(LEVEL_COUNT, sanitized.lastLevelId)
        assertFalse(sanitized.settings.hapticsEnabled)
        assertTrue(sanitized.settings.highContrast)
        assertTrue(sanitized.settings.reduceMotion)
    }

    @Test
    fun progressRulesAddCompletedLevelWithoutLosingSettings() {
        val progress = ProgressState(
            onboardingSeen = true,
            completedLevelIds = setOf(1, LEVEL_COUNT + 1),
            lastLevelId = 99,
            settings = SettingsState(
                hapticsEnabled = false,
                highContrast = true,
                reduceMotion = true,
            ),
        )

        val updated = ProgressRules.withCompletedLevel(progress, 2)

        assertTrue(updated.onboardingSeen)
        assertEquals(setOf(1, 2), updated.completedLevelIds)
        assertEquals(2, updated.lastLevelId)
        assertFalse(updated.settings.hapticsEnabled)
        assertTrue(updated.settings.highContrast)
        assertTrue(updated.settings.reduceMotion)
    }

    @Test
    fun progressRulesRecordNewCompletedLevelAsLastPlayed() {
        val progress = ProgressState(
            completedLevelIds = setOf(1, 2),
            lastLevelId = 1,
        )

        val updated = ProgressRules.withCompletedLevel(progress, 3)

        assertEquals(setOf(1, 2, 3), updated.completedLevelIds)
        assertEquals(3, updated.lastLevelId)
    }

    @Test
    fun progressRulesIgnoreInvalidCompletedLevelWhenAddingOptimistically() {
        val progress = ProgressState(
            completedLevelIds = setOf(1, 2),
            lastLevelId = 3,
        )

        val updated = ProgressRules.withCompletedLevel(progress, LEVEL_COUNT + 10)

        assertEquals(setOf(1, 2), updated.completedLevelIds)
        assertEquals(3, updated.lastLevelId)
    }

    @Test
    fun progressRulesTreatReplayedCompletedLevelAsIdempotent() {
        val progress = ProgressState(
            onboardingSeen = true,
            completedLevelIds = setOf(1, 2),
            lastLevelId = 2,
            settings = SettingsState(
                hapticsEnabled = false,
                highContrast = true,
                reduceMotion = true,
            ),
        )

        val updated = ProgressRules.withCompletedLevel(progress, 2)

        assertTrue(updated.onboardingSeen)
        assertEquals(setOf(1, 2), updated.completedLevelIds)
        assertEquals(2, updated.lastLevelId)
        assertFalse(updated.settings.hapticsEnabled)
        assertTrue(updated.settings.highContrast)
        assertTrue(updated.settings.reduceMotion)
    }
}
