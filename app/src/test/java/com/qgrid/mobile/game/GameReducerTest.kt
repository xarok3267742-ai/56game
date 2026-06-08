package com.qgrid.mobile.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class GameReducerTest {
    private val level = LevelFactory.createLevels().first()

    @Test
    fun selectingCanonicalPathWinsAtFiftySix() {
        val finalState = level.solutionPath.fold(GameReducer.newGame(level)) { state, position ->
            GameReducer.selectCell(state, position)
        }

        assertEquals(GameStatus.WON, finalState.status)
        assertEquals(TARGET_SUM, finalState.currentSum)
    }

    @Test
    fun wonStateIgnoresFurtherSelectionUndoResetAndHint() {
        val won = level.solutionPath.fold(GameReducer.newGame(level)) { state, position ->
            GameReducer.selectCell(state, position)
        }

        val selected = GameReducer.selectCell(won, CellPosition(0, 0))
        val undone = GameReducer.undo(won)
        val reset = GameReducer.reset(won)
        val hinted = GameReducer.hint(won)

        assertEquals(won, selected)
        assertEquals(won, undone)
        assertEquals(won, reset)
        assertEquals(won, hinted)
    }

    @Test
    fun gameStateRejectsStatusThatDoesNotMatchCurrentSum() {
        assertThrows(IllegalArgumentException::class.java) {
            GameState(level = level, status = GameStatus.WON)
        }
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                selection = PathSelection(level.solutionPath),
                status = GameStatus.PLAYING,
            )
        }
    }

    @Test
    fun gameStateRejectsInvalidSelectionShapeAndHintMetadata() {
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                selection = PathSelection(
                    listOf(
                        CellPosition(0, 0),
                        CellPosition(0, 0),
                    ),
                ),
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                hintedPosition = CellPosition(level.board.size, 0),
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                hintsUsed = -1,
            )
        }
    }

    @Test
    fun gameStateRejectsHintsThatCannotBePlayedFromCurrentSelection() {
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                selection = PathSelection(level.solutionPath),
                status = GameStatus.WON,
                hintedPosition = level.solutionPath.first(),
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                selection = PathSelection(listOf(CellPosition(0, 0))),
                hintedPosition = CellPosition(0, 0),
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = level,
                selection = PathSelection(listOf(CellPosition(0, 0))),
                hintedPosition = CellPosition(level.board.size - 1, level.board.size - 1),
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            GameState(
                level = exceedingTestLevel(),
                selection = PathSelection(listOf(CellPosition(0, 0))),
                hintedPosition = CellPosition(0, 1),
            )
        }
    }

    @Test
    fun reducerRejectsRepeatedCells() {
        val first = level.solutionPath.first()
        val state = GameReducer.selectCell(GameReducer.newGame(level), first)
        val repeated = GameReducer.selectCell(state, first)

        assertEquals(GameMessage.ALREADY_USED, repeated.message)
        assertEquals(1, repeated.selection.positions.size)
    }

    @Test
    fun reducerRejectsNonAdjacentCell() {
        val start = CellPosition(0, 0)
        val farAway = CellPosition(level.board.size - 1, level.board.size - 1)
        val state = GameReducer.selectCell(GameReducer.newGame(level), start)
        val rejected = GameReducer.selectCell(state, farAway)

        assertEquals(GameMessage.NOT_ADJACENT, rejected.message)
        assertEquals(listOf(start), rejected.selection.positions)
    }

    @Test
    fun reducerRejectsCellOutsideBoardAtStart() {
        val rejected = GameReducer.selectCell(GameReducer.newGame(level), CellPosition(-1, 0))

        assertEquals(GameMessage.NOT_ON_BOARD, rejected.message)
        assertEquals(GameStatus.PLAYING, rejected.status)
        assertTrue(rejected.selection.positions.isEmpty())
    }

    @Test
    fun reducerRejectsCellOutsideBoardAfterSelection() {
        val start = level.solutionPath.first()
        val state = GameReducer.selectCell(GameReducer.newGame(level), start)
        val rejected = GameReducer.selectCell(state, CellPosition(level.board.size, 0))

        assertEquals(GameMessage.NOT_ON_BOARD, rejected.message)
        assertEquals(listOf(start), rejected.selection.positions)
        assertNull(rejected.hintedPosition)
    }

    @Test
    fun undoClearsExceededState() {
        val heavyLevel = exceedingTestLevel()
        val exceeded = listOf(CellPosition(0, 0), CellPosition(0, 1))
            .fold(GameReducer.newGame(heavyLevel)) { state, position ->
                GameReducer.selectCell(state, position)
            }

        assertEquals(GameStatus.EXCEEDED, exceeded.status)

        val undone = GameReducer.undo(exceeded)

        assertEquals(GameStatus.PLAYING, undone.status)
        assertEquals(30, undone.currentSum)
    }

    @Test
    fun exceededStateBlocksAdditionalSelectionUntilUndoOrReset() {
        val heavyLevel = exceedingTestLevel()
        val exceeded = listOf(CellPosition(0, 0), CellPosition(0, 1))
            .fold(GameReducer.newGame(heavyLevel)) { state, position ->
                GameReducer.selectCell(state, position)
            }

        val blocked = GameReducer.selectCell(exceeded, CellPosition(1, 1))

        assertEquals(GameStatus.EXCEEDED, blocked.status)
        assertEquals(GameMessage.SUM_EXCEEDED, blocked.message)
        assertEquals(exceeded.selection.positions, blocked.selection.positions)
    }

    @Test
    fun exceededStateDoesNotExposeNewHints() {
        val heavyLevel = exceedingTestLevel()
        val exceeded = listOf(CellPosition(0, 0), CellPosition(0, 1))
            .fold(GameReducer.newGame(heavyLevel)) { state, position ->
                GameReducer.selectCell(state, position)
            }

        val hinted = GameReducer.hint(exceeded)

        assertEquals(GameStatus.EXCEEDED, hinted.status)
        assertEquals(GameMessage.SUM_EXCEEDED, hinted.message)
        assertNull(hinted.hintedPosition)
        assertEquals(exceeded.hintsUsed, hinted.hintsUsed)
    }

    @Test
    fun hintPointsToReachableStart() {
        val hinted = GameReducer.hint(GameReducer.newGame(level))

        val hintedPosition = requireNotNull(hinted.hintedPosition)

        assertTrue(level.board.contains(hintedPosition))
        assertTrue(LevelSolver.findPathFromSelection(level.board, listOf(hintedPosition)) != null)
        assertEquals(GameMessage.HINT_START, hinted.message)
        assertTrue(hinted.hintsUsed == 1)
    }

    @Test
    fun hintFollowsCurrentPlayableSelectionWhenItIsNotCanonicalPrefix() {
        val hintLevel = hintContinuationTestLevel()
        val selectedPositions = listOf(CellPosition(3, 0), CellPosition(3, 1))
        val selected = selectedPositions.fold(GameReducer.newGame(hintLevel)) { state, position ->
            GameReducer.selectCell(state, position)
        }

        val hinted = GameReducer.hint(selected)

        assertEquals(GameMessage.HINT_NEXT, hinted.message)
        assertEquals(CellPosition(3, 2), hinted.hintedPosition)
        assertEquals(selectedPositions, hinted.selection.positions)
        assertEquals(1, hinted.hintsUsed)
    }

    @Test
    fun hintAsksForRepairWhenCurrentSelectionCannotReachTarget() {
        val repairLevel = hintRepairTestLevel()
        val selected = GameReducer.selectCell(
            state = GameReducer.newGame(repairLevel),
            position = CellPosition(3, 0),
        )

        val hinted = GameReducer.hint(selected)

        assertEquals(GameMessage.HINT_REPAIR, hinted.message)
        assertNull(hinted.hintedPosition)
        assertEquals(listOf(CellPosition(3, 0)), hinted.selection.positions)
        assertEquals(1, hinted.hintsUsed)
    }

    @Test
    fun resetReturnsEmptySelection() {
        val selected = GameReducer.selectCell(GameReducer.newGame(level), level.solutionPath.first())
        val reset = GameReducer.reset(selected)

        assertTrue(reset.selection.positions.isEmpty())
        assertEquals(GameStatus.PLAYING, reset.status)
        assertNull(reset.hintedPosition)
    }

    private fun exceedingTestLevel(): LevelDefinition {
        val solutionPath = listOf(
            CellPosition(1, 0),
            CellPosition(1, 1),
            CellPosition(1, 2),
            CellPosition(1, 3),
            CellPosition(2, 3),
            CellPosition(2, 2),
            CellPosition(2, 1),
        )
        val cells = MutableList(16) { index ->
            Cell(
                position = CellPosition(index / 4, index % 4),
                value = 8,
            )
        }
        cells[0] = Cell(CellPosition(0, 0), 30)
        cells[1] = Cell(CellPosition(0, 1), 30)

        return LevelDefinition(
            id = 1,
            size = 4,
            difficulty = Difficulty.EASY,
            board = Board(size = 4, cells = cells),
            solutionPath = solutionPath,
        )
    }

    private fun hintContinuationTestLevel(): LevelDefinition {
        return testLevel(
            values = listOf(
                14, 14, 14, 14,
                57, 57, 57, 57,
                57, 57, 57, 57,
                10, 20, 26, 57,
            ),
        )
    }

    private fun hintRepairTestLevel(): LevelDefinition {
        return testLevel(
            values = listOf(
                14, 14, 14, 14,
                57, 57, 57, 57,
                2, 2, 57, 57,
                55, 2, 57, 57,
            ),
        )
    }

    private fun testLevel(values: List<Int>): LevelDefinition {
        return LevelDefinition(
            id = 1,
            size = 4,
            difficulty = Difficulty.EASY,
            board = Board(
                size = 4,
                cells = values.mapIndexed { index, value ->
                    Cell(
                        position = CellPosition(index / 4, index % 4),
                        value = value,
                    )
                },
            ),
            solutionPath = listOf(
                CellPosition(0, 0),
                CellPosition(0, 1),
                CellPosition(0, 2),
                CellPosition(0, 3),
            ),
        )
    }
}
