package com.qgrid.mobile.game

object GameReducer {
    fun newGame(level: LevelDefinition): GameState = GameState(level = level)

    fun selectCell(
        state: GameState,
        position: CellPosition,
    ): GameState {
        if (state.status == GameStatus.WON) return state
        if (state.status == GameStatus.EXCEEDED) {
            return state.copy(
                message = GameMessage.SUM_EXCEEDED,
                hintedPosition = null,
            )
        }
        if (!state.level.board.contains(position)) {
            return state.copy(
                message = GameMessage.NOT_ON_BOARD,
                hintedPosition = null,
            )
        }
        val selection = state.selection
        if (selection.contains(position)) {
            return state.copy(
                message = GameMessage.ALREADY_USED,
                hintedPosition = null,
            )
        }
        val last = selection.last
        if (last != null && !position.isAdjacentTo(last)) {
            return state.copy(
                message = GameMessage.NOT_ADJACENT,
                hintedPosition = null,
            )
        }
        val nextSelection = PathSelection(selection.positions + position)
        val nextSum = nextSelection.sum(state.level.board)
        val nextStatus = when {
            nextSum == TARGET_SUM -> GameStatus.WON
            nextSum > TARGET_SUM -> GameStatus.EXCEEDED
            else -> GameStatus.PLAYING
        }
        val nextMessage = when (nextStatus) {
            GameStatus.WON -> GameMessage.WON
            GameStatus.EXCEEDED -> GameMessage.SUM_EXCEEDED
            GameStatus.PLAYING -> GameMessage.CONTINUE
        }
        return state.copy(
            selection = nextSelection,
            status = nextStatus,
            message = nextMessage,
            hintedPosition = null,
        )
    }

    fun undo(state: GameState): GameState {
        if (state.status == GameStatus.WON) return state
        if (state.selection.positions.isEmpty()) {
            return state.copy(
                status = GameStatus.PLAYING,
                message = GameMessage.EMPTY_LINE,
                hintedPosition = null,
            )
        }
        val nextSelection = PathSelection(state.selection.positions.dropLast(1))
        return state.copy(
            selection = nextSelection,
            status = GameStatus.PLAYING,
            message = if (nextSelection.positions.isEmpty()) {
                GameMessage.EMPTY_LINE
            } else {
                GameMessage.CONTINUE
            },
            hintedPosition = null,
        )
    }

    fun reset(state: GameState): GameState {
        if (state.status == GameStatus.WON) return state
        return GameState(level = state.level)
    }

    fun hint(state: GameState): GameState {
        if (state.status == GameStatus.WON) return state
        if (state.status == GameStatus.EXCEEDED) {
            return state.copy(
                message = GameMessage.SUM_EXCEEDED,
                hintedPosition = null,
            )
        }
        val selected = state.selection.positions
        val solvedPath = LevelSolver.findPathFromSelection(
            board = state.level.board,
            selected = selected,
        )
        val hintPosition = solvedPath?.getOrNull(selected.size)
        return state.copy(
            hintedPosition = hintPosition,
            hintsUsed = state.hintsUsed + 1,
            message = when {
                hintPosition == null -> GameMessage.HINT_REPAIR
                selected.isEmpty() -> GameMessage.HINT_START
                else -> GameMessage.HINT_NEXT
            },
        )
    }
}
