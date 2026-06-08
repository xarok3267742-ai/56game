package com.qgrid.mobile.ui

import com.qgrid.mobile.game.LevelDefinition
import com.qgrid.mobile.game.ProgressRules

internal object LevelNavigation {
    fun levelForId(
        levels: List<LevelDefinition>,
        requestedLevelId: Int,
    ): LevelDefinition? {
        val orderedLevels = levels.distinctBy { it.id }.sortedBy { it.id }
        if (orderedLevels.isEmpty()) return null
        val levelId = ProgressRules.sanitizedLastLevelId(requestedLevelId)
        return orderedLevels.firstOrNull { it.id == levelId }
            ?: orderedLevels.firstOrNull { it.id > levelId }
            ?: orderedLevels.last()
    }

    fun nextLevelId(
        levels: List<LevelDefinition>,
        currentLevelId: Int?,
    ): Int {
        val orderedLevelIds = levels.map { it.id }.distinct().sorted()
        if (orderedLevelIds.isEmpty()) return 1
        if (currentLevelId == null) return orderedLevelIds.first()
        val currentId = ProgressRules.sanitizedLastLevelId(currentLevelId)
        return orderedLevelIds.firstOrNull { it > currentId } ?: orderedLevelIds.last()
    }
}
