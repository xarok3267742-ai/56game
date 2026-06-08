package com.qgrid.mobile.game

import kotlin.random.Random

object LevelFactory {
    fun createLevels(): List<LevelDefinition> = (1..LEVEL_COUNT).map(::createLevel)

    private fun createLevel(id: Int): LevelDefinition {
        val difficulty = when {
            id <= 12 -> Difficulty.EASY
            id <= 24 -> Difficulty.MEDIUM
            else -> Difficulty.HARD
        }
        val size = when (difficulty) {
            Difficulty.EASY -> 5
            Difficulty.MEDIUM -> 5
            Difficulty.HARD -> 6
        }
        val pathLength = when (difficulty) {
            Difficulty.EASY -> 5 + (id % 2)
            Difficulty.MEDIUM -> 6 + (id % 2)
            Difficulty.HARD -> 7 + (id % 2)
        }
        val random = Random(5600 + id * 97)
        val solutionPath = createSelfAvoidingPath(size, pathLength, random)
        val solutionValues = splitTarget(pathLength, random)
        val cells = MutableList(size * size) { index ->
            val row = index / size
            val col = index % size
            Cell(CellPosition(row, col), random.nextInt(3, 15))
        }
        solutionPath.forEachIndexed { index, position ->
            cells[position.row * size + position.col] = Cell(position, solutionValues[index])
        }
        val board = Board(size = size, cells = cells)
        return LevelDefinition(
            id = id,
            size = size,
            difficulty = difficulty,
            board = board,
            solutionPath = solutionPath,
        )
    }

    private fun createSelfAvoidingPath(
        size: Int,
        length: Int,
        random: Random,
    ): List<CellPosition> {
        repeat(600) {
            val path = mutableListOf(
                CellPosition(
                    row = random.nextInt(size),
                    col = random.nextInt(size),
                ),
            )
            while (path.size < length) {
                val nextCandidates = neighbors(path.last(), size)
                    .filterNot(path::contains)
                    .shuffled(random)
                val next = nextCandidates.firstOrNull() ?: break
                path += next
            }
            if (path.size == length) return path
        }
        error("Could not create a path for board size=$size length=$length")
    }

    private fun neighbors(position: CellPosition, size: Int): List<CellPosition> {
        val result = mutableListOf<CellPosition>()
        for (rowDelta in -1..1) {
            for (colDelta in -1..1) {
                if (rowDelta == 0 && colDelta == 0) continue
                val row = position.row + rowDelta
                val col = position.col + colDelta
                if (row in 0 until size && col in 0 until size) {
                    result += CellPosition(row, col)
                }
            }
        }
        return result
    }

    private fun splitTarget(length: Int, random: Random): List<Int> {
        val values = MutableList(length) { 4 }
        var remaining = TARGET_SUM - values.sum()
        while (remaining > 0) {
            val index = random.nextInt(length)
            val canAdd = 14 - values[index]
            if (canAdd <= 0) continue
            val delta = random.nextInt(1, minOf(canAdd, remaining) + 1)
            values[index] += delta
            remaining -= delta
        }
        return values.shuffled(random)
    }
}
