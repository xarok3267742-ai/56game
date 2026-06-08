package com.qgrid.mobile.game

object LevelSolver {
    fun findPath(
        board: Board,
        target: Int = TARGET_SUM,
    ): List<CellPosition>? {
        require(target > 0) { "Target must be positive." }
        require(board.size * board.size <= Long.SIZE_BITS) {
            "Solver uses a Long visited mask and supports boards up to 64 cells."
        }

        val values = board.cells.map { it.value }
        val neighbors = List(values.size) { index ->
            neighborIndices(index, board.size)
        }
        val failedStates = HashSet<SearchState>()

        values.indices.forEach { start ->
            val startValue = values[start]
            if (startValue > target) return@forEach

            val path = mutableListOf(start)
            val solved = search(
                current = start,
                sum = startValue,
                usedMask = 1L shl start,
                target = target,
                values = values,
                neighbors = neighbors,
                failedStates = failedStates,
                path = path,
            )
            if (solved != null) {
                return solved.map { index ->
                    CellPosition(
                        row = index / board.size,
                        col = index % board.size,
                    )
                }
            }
        }

        return null
    }

    fun findPathFromSelection(
        board: Board,
        selected: List<CellPosition>,
        target: Int = TARGET_SUM,
    ): List<CellPosition>? {
        if (selected.isEmpty()) return findPath(board, target)
        require(target > 0) { "Target must be positive." }
        require(board.size * board.size <= Long.SIZE_BITS) {
            "Solver uses a Long visited mask and supports boards up to 64 cells."
        }
        require(selected.all(board::contains)) {
            "Selected path must stay inside the board."
        }
        require(selected.size == selected.toSet().size) {
            "Selected path must not repeat cells."
        }
        require(selected.zipWithNext().all { (current, next) -> current.isAdjacentTo(next) }) {
            "Selected path must use adjacent cells only."
        }

        val selectedSum = selected.sumOf { board.cellAt(it).value }
        if (selectedSum > target) return null
        if (selectedSum == target) return selected

        val values = board.cells.map { it.value }
        val neighbors = List(values.size) { index ->
            neighborIndices(index, board.size)
        }
        val selectedIndices = selected.map { position ->
            position.row * board.size + position.col
        }
        val usedMask = selectedIndices.fold(0L) { mask, index ->
            mask or (1L shl index)
        }
        val solved = search(
            current = selectedIndices.last(),
            sum = selectedSum,
            usedMask = usedMask,
            target = target,
            values = values,
            neighbors = neighbors,
            failedStates = HashSet(),
            path = selectedIndices.toMutableList(),
        )

        return solved?.map { index ->
            CellPosition(
                row = index / board.size,
                col = index % board.size,
            )
        }
    }

    private fun search(
        current: Int,
        sum: Int,
        usedMask: Long,
        target: Int,
        values: List<Int>,
        neighbors: List<List<Int>>,
        failedStates: MutableSet<SearchState>,
        path: MutableList<Int>,
    ): List<Int>? {
        if (sum == target) return path.toList()

        val state = SearchState(current, sum, usedMask)
        if (state in failedStates) return null

        neighbors[current].forEach { next ->
            val bit = 1L shl next
            if (usedMask and bit != 0L) return@forEach

            val nextSum = sum + values[next]
            if (nextSum > target) return@forEach

            path += next
            val solved = search(
                current = next,
                sum = nextSum,
                usedMask = usedMask or bit,
                target = target,
                values = values,
                neighbors = neighbors,
                failedStates = failedStates,
                path = path,
            )
            if (solved != null) return solved
            path.removeAt(path.lastIndex)
        }

        failedStates += state
        return null
    }

    private fun neighborIndices(index: Int, size: Int): List<Int> {
        val row = index / size
        val col = index % size
        val result = mutableListOf<Int>()
        for (rowDelta in -1..1) {
            for (colDelta in -1..1) {
                if (rowDelta == 0 && colDelta == 0) continue
                val nextRow = row + rowDelta
                val nextCol = col + colDelta
                if (nextRow in 0 until size && nextCol in 0 until size) {
                    result += nextRow * size + nextCol
                }
            }
        }
        return result
    }

    private data class SearchState(
        val current: Int,
        val sum: Int,
        val usedMask: Long,
    )
}
