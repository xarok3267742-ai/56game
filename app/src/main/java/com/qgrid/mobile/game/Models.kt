package com.qgrid.mobile.game

const val TARGET_SUM = 56
const val LEVEL_COUNT = 36

enum class Difficulty {
    EASY,
    MEDIUM,
    HARD,
}

data class CellPosition(
    val row: Int,
    val col: Int,
) {
    fun isAdjacentTo(other: CellPosition): Boolean {
        val rowDelta = kotlin.math.abs(row - other.row)
        val colDelta = kotlin.math.abs(col - other.col)
        return rowDelta <= 1 && colDelta <= 1 && rowDelta + colDelta > 0
    }
}

data class Cell(
    val position: CellPosition,
    val value: Int,
)

data class Board(
    val size: Int,
    val cells: List<Cell>,
) {
    init {
        require(size in 4..6) { "Board size must stay readable on phones." }
        require(cells.size == size * size) { "Board must contain size * size cells." }
        cells.forEachIndexed { index, cell ->
            val expectedPosition = CellPosition(
                row = index / size,
                col = index % size,
            )
            require(cell.position == expectedPosition) {
                "Cell at index $index must have position $expectedPosition, got ${cell.position}."
            }
            require(cell.value > 0) { "Cell values must be positive." }
        }
    }

    fun cellAt(position: CellPosition): Cell {
        require(position.row in 0 until size && position.col in 0 until size) {
            "Cell position is outside the board: $position"
        }
        return cells[position.row * size + position.col]
    }

    fun contains(position: CellPosition): Boolean {
        return position.row in 0 until size && position.col in 0 until size
    }
}

data class LevelDefinition(
    val id: Int,
    val size: Int,
    val difficulty: Difficulty,
    val board: Board,
    val solutionPath: List<CellPosition>,
) {
    val target: Int = TARGET_SUM

    init {
        require(id in 1..LEVEL_COUNT) { "Level id must be within the released level set." }
        require(size == board.size) { "Level size must match board size." }
        require(solutionPath.isNotEmpty()) { "Level solution path must not be empty." }
        require(solutionPath.size == solutionPath.toSet().size) {
            "Level solution path must not repeat cells."
        }
        solutionPath.forEach(board::cellAt)
        solutionPath.zipWithNext().forEach { (current, next) ->
            require(current.isAdjacentTo(next)) {
                "Level solution path must use adjacent cells only."
            }
        }
        require(solutionPath.sumOf { board.cellAt(it).value } == target) {
            "Level solution path must sum to the target."
        }
    }
}

data class PathSelection(
    val positions: List<CellPosition> = emptyList(),
) {
    val last: CellPosition? = positions.lastOrNull()

    fun contains(position: CellPosition): Boolean = position in positions

    fun sum(board: Board): Int = positions.sumOf { board.cellAt(it).value }
}

enum class GameStatus {
    PLAYING,
    EXCEEDED,
    WON,
}

data class GameState(
    val level: LevelDefinition,
    val selection: PathSelection = PathSelection(),
    val status: GameStatus = GameStatus.PLAYING,
    val message: GameMessage = GameMessage.EMPTY_LINE,
    val hintedPosition: CellPosition? = null,
    val hintsUsed: Int = 0,
) {
    init {
        selection.positions.forEach(level.board::cellAt)
        require(selection.positions.size == selection.positions.toSet().size) {
            "Game selection must not repeat cells."
        }
        require(selection.positions.zipWithNext().all { (current, next) -> current.isAdjacentTo(next) }) {
            "Game selection must use adjacent cells only."
        }
        val selectedSum = selection.sum(level.board)
        require(
            when (status) {
                GameStatus.PLAYING -> selectedSum < TARGET_SUM
                GameStatus.EXCEEDED -> selectedSum > TARGET_SUM
                GameStatus.WON -> selectedSum == TARGET_SUM
            },
        ) {
            "Game status must match selected sum."
        }
        if (hintedPosition != null) {
            require(status == GameStatus.PLAYING) {
                "Hinted cell is only valid for active games."
            }
            require(level.board.contains(hintedPosition)) {
                "Hinted cell must stay inside the board."
            }
            require(!selection.contains(hintedPosition)) {
                "Hinted cell must not already be selected."
            }
            require(selection.last?.let { hintedPosition.isAdjacentTo(it) } != false) {
                "Hinted cell must stay adjacent to the current line."
            }
            require(selectedSum + level.board.cellAt(hintedPosition).value <= TARGET_SUM) {
                "Hinted cell must not overshoot the target."
            }
        }
        require(hintsUsed >= 0) { "Hints used must not be negative." }
    }

    val currentSum: Int = selection.sum(level.board)
    val remaining: Int = TARGET_SUM - currentSum
}

enum class GameMessage {
    EMPTY_LINE,
    CONTINUE,
    NOT_ON_BOARD,
    NOT_ADJACENT,
    ALREADY_USED,
    SUM_EXCEEDED,
    HINT_START,
    HINT_NEXT,
    HINT_REPAIR,
    WON,
}

data class SettingsState(
    val hapticsEnabled: Boolean = true,
    val highContrast: Boolean = false,
    val reduceMotion: Boolean = false,
)

data class ProgressState(
    val onboardingSeen: Boolean = false,
    val completedLevelIds: Set<Int> = emptySet(),
    val lastLevelId: Int = 1,
    val settings: SettingsState = SettingsState(),
)

object ProgressRules {
    fun parseCompletedLevelIds(raw: String?): Set<Int> {
        return raw
            ?.split(",")
            ?.mapNotNull { it.trim().toIntOrNull() }
            ?.let(::sanitizedCompletedLevelIds)
            ?: emptySet()
    }

    fun serializedCompletedLevelIds(levelIds: Iterable<Int>): String {
        return sanitizedCompletedLevelIds(levelIds)
            .sorted()
            .joinToString(separator = ",")
    }

    fun sanitizedCompletedLevelIds(levelIds: Iterable<Int>): Set<Int> {
        return levelIds
            .filter { it in 1..LEVEL_COUNT }
            .toSet()
    }

    fun sanitizedLastLevelId(levelId: Int): Int = levelId.coerceIn(1, LEVEL_COUNT)

    fun sanitized(progress: ProgressState): ProgressState {
        return progress.copy(
            completedLevelIds = sanitizedCompletedLevelIds(progress.completedLevelIds),
            lastLevelId = sanitizedLastLevelId(progress.lastLevelId),
        )
    }

    fun withCompletedLevel(
        progress: ProgressState,
        levelId: Int,
    ): ProgressState {
        val sanitizedProgress = sanitized(progress)
        if (levelId !in 1..LEVEL_COUNT) return sanitizedProgress

        val isNewCompletion = levelId !in sanitizedProgress.completedLevelIds
        return sanitizedProgress.copy(
            completedLevelIds = sanitizedProgress.completedLevelIds + levelId,
            lastLevelId = if (isNewCompletion) {
                levelId
            } else {
                sanitizedProgress.lastLevelId
            },
        )
    }
}
