package com.qgrid.mobile.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class LevelFactoryTest {
    @Test
    fun createsThirtySixPlayableLevels() {
        val levels = LevelFactory.createLevels()

        assertEquals(36, levels.size)
        assertEquals((1..36).toList(), levels.map { it.id })
    }

    @Test
    fun generatedLevelsUseDocumentedDifficultyBoardSizesAndPathLengths() {
        val levels = LevelFactory.createLevels()

        levels.forEach { level ->
            val expectedDifficulty = when (level.id) {
                in 1..12 -> Difficulty.EASY
                in 13..24 -> Difficulty.MEDIUM
                else -> Difficulty.HARD
            }
            val expectedSize = if (expectedDifficulty == Difficulty.HARD) 6 else 5
            val expectedPathLength = when (expectedDifficulty) {
                Difficulty.EASY -> 5 + (level.id % 2)
                Difficulty.MEDIUM -> 6 + (level.id % 2)
                Difficulty.HARD -> 7 + (level.id % 2)
            }

            assertEquals("Bad difficulty on level ${level.id}", expectedDifficulty, level.difficulty)
            assertEquals("Bad board size on level ${level.id}", expectedSize, level.size)
            assertEquals("Bad board model size on level ${level.id}", expectedSize, level.board.size)
            assertEquals(
                "Bad canonical path length on level ${level.id}",
                expectedPathLength,
                level.solutionPath.size,
            )
        }
    }

    @Test
    fun everyCanonicalSolutionSumsToTarget() {
        val levels = LevelFactory.createLevels()

        levels.forEach { level ->
            val solutionSum = level.solutionPath.sumOf { level.board.cellAt(it).value }

            assertEquals("Bad solution for level ${level.id}", TARGET_SUM, solutionSum)
            assertEquals(
                "Solution path repeats cells on level ${level.id}",
                level.solutionPath.size,
                level.solutionPath.toSet().size,
            )
        }
    }

    @Test
    fun solutionPathsUseAdjacentCellsOnly() {
        LevelFactory.createLevels().forEach { level ->
            level.solutionPath.zipWithNext().forEach { (current, next) ->
                assertTrue(
                    "Non-adjacent solution step on level ${level.id}: $current -> $next",
                    current.isAdjacentTo(next),
                )
            }
        }
    }

    @Test
    fun solverFindsReachableTargetOnEveryGeneratedBoard() {
        LevelFactory.createLevels().forEach { level ->
            val solvedPath = LevelSolver.findPath(level.board)

            assertTrue("No solver path for level ${level.id}", solvedPath != null)
            requireNotNull(solvedPath)
            assertEquals(
                "Solver path sum mismatch on level ${level.id}",
                TARGET_SUM,
                solvedPath.sumOf { level.board.cellAt(it).value },
            )
            assertEquals(
                "Solver path repeats cells on level ${level.id}",
                solvedPath.size,
                solvedPath.toSet().size,
            )
            solvedPath.zipWithNext().forEach { (current, next) ->
                assertTrue(
                    "Solver found non-adjacent step on level ${level.id}: $current -> $next",
                    current.isAdjacentTo(next),
                )
            }
        }
    }

    @Test
    fun solverReturnsNullWhenBoardCannotReachTarget() {
        val impossibleBoard = Board(
            size = 4,
            cells = (0 until 16).map { index ->
                Cell(
                    position = CellPosition(index / 4, index % 4),
                    value = 57,
                )
            },
        )

        assertEquals(null, LevelSolver.findPath(impossibleBoard))
    }

    @Test
    fun solverContinuesFromCurrentSelection() {
        val board = Board(
            size = 4,
            cells = listOf(
                14, 14, 14, 14,
                57, 57, 57, 57,
                57, 57, 57, 57,
                10, 20, 26, 57,
            ).mapIndexed { index, value ->
                Cell(
                    position = CellPosition(index / 4, index % 4),
                    value = value,
                )
            },
        )
        val selected = listOf(CellPosition(3, 0), CellPosition(3, 1))

        val solvedPath = LevelSolver.findPathFromSelection(board, selected)

        assertEquals(selected + CellPosition(3, 2), solvedPath)
    }

    @Test
    fun solverReturnsNullWhenCurrentSelectionCannotReachTarget() {
        val board = Board(
            size = 4,
            cells = listOf(
                14, 14, 14, 14,
                57, 57, 57, 57,
                2, 2, 57, 57,
                55, 2, 57, 57,
            ).mapIndexed { index, value ->
                Cell(
                    position = CellPosition(index / 4, index % 4),
                    value = value,
                )
            },
        )
        val selected = listOf(CellPosition(3, 0))

        assertNull(LevelSolver.findPathFromSelection(board, selected))
    }

    @Test
    fun solverReturnsSelectedPathWhenCurrentSelectionAlreadyReachesTarget() {
        val level = validFourByFourLevel()

        val solvedPath = LevelSolver.findPathFromSelection(level.board, level.solutionPath)

        assertEquals(level.solutionPath, solvedPath)
    }

    @Test
    fun solverRejectsCurrentSelectionOutsideBoard() {
        assertThrows(IllegalArgumentException::class.java) {
            LevelSolver.findPathFromSelection(
                board = validFourByFourLevel().board,
                selected = listOf(CellPosition(-1, 0)),
            )
        }
    }

    @Test
    fun solverRejectsRepeatedCurrentSelectionCells() {
        assertThrows(IllegalArgumentException::class.java) {
            LevelSolver.findPathFromSelection(
                board = validFourByFourLevel().board,
                selected = listOf(
                    CellPosition(0, 0),
                    CellPosition(0, 1),
                    CellPosition(0, 0),
                ),
            )
        }
    }

    @Test
    fun solverRejectsNonAdjacentCurrentSelectionCells() {
        assertThrows(IllegalArgumentException::class.java) {
            LevelSolver.findPathFromSelection(
                board = validFourByFourLevel().board,
                selected = listOf(
                    CellPosition(0, 0),
                    CellPosition(3, 3),
                ),
            )
        }
    }

    @Test
    fun boardRejectsCellsThatDoNotMatchTheirGridPosition() {
        val cells = (0 until 16).map { index ->
            Cell(
                position = CellPosition(index / 4, index % 4),
                value = 5,
            )
        }.toMutableList()
        cells[1] = cells[1].copy(position = CellPosition(3, 3))

        assertThrows(IllegalArgumentException::class.java) {
            Board(size = 4, cells = cells)
        }
    }

    @Test
    fun boardRejectsNonPositiveCellValues() {
        val cells = (0 until 16).map { index ->
            Cell(
                position = CellPosition(index / 4, index % 4),
                value = if (index == 5) 0 else 5,
            )
        }

        assertThrows(IllegalArgumentException::class.java) {
            Board(size = 4, cells = cells)
        }
    }

    @Test
    fun boardRejectsOversizedReleasedBoard() {
        assertThrows(IllegalArgumentException::class.java) {
            Board(
                size = 7,
                cells = (0 until 49).map { index ->
                    Cell(
                        position = CellPosition(index / 7, index % 7),
                        value = 5,
                    )
                },
            )
        }
    }

    @Test
    fun levelRejectsMismatchedBoardSize() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(size = 5)
        }
    }

    @Test
    fun levelRejectsIdsOutsideReleasedSet() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(id = 0)
        }
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(id = LEVEL_COUNT + 1)
        }
    }

    @Test
    fun levelRejectsEmptySolutionPath() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(solutionPath = emptyList())
        }
    }

    @Test
    fun levelRejectsRepeatedSolutionCells() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(
                solutionPath = listOf(
                    CellPosition(0, 0),
                    CellPosition(0, 1),
                    CellPosition(0, 0),
                ),
            )
        }
    }

    @Test
    fun levelRejectsNonAdjacentSolutionCells() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(
                solutionPath = listOf(
                    CellPosition(0, 0),
                    CellPosition(3, 3),
                ),
            )
        }
    }

    @Test
    fun levelRejectsSolutionCellsOutsideBoard() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(
                solutionPath = listOf(
                    CellPosition(0, 0),
                    CellPosition(0, 1),
                    CellPosition(0, 2),
                    CellPosition(0, 3),
                    CellPosition(1, 3),
                    CellPosition(1, 2),
                    CellPosition(4, 1),
                ),
            )
        }
    }

    @Test
    fun levelRejectsSolutionThatDoesNotReachTarget() {
        assertThrows(IllegalArgumentException::class.java) {
            validFourByFourLevel().copy(
                solutionPath = listOf(
                    CellPosition(0, 0),
                    CellPosition(0, 1),
                    CellPosition(0, 2),
                ),
            )
        }
    }

    private fun validFourByFourLevel(): LevelDefinition {
        return LevelDefinition(
            id = 1,
            size = 4,
            difficulty = Difficulty.EASY,
            board = Board(
                size = 4,
                cells = (0 until 16).map { index ->
                    Cell(
                        position = CellPosition(index / 4, index % 4),
                        value = 8,
                    )
                },
            ),
            solutionPath = listOf(
                CellPosition(0, 0),
                CellPosition(0, 1),
                CellPosition(0, 2),
                CellPosition(0, 3),
                CellPosition(1, 3),
                CellPosition(1, 2),
                CellPosition(1, 1),
            ),
        )
    }
}
