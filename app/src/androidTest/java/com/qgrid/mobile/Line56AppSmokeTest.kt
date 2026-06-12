package com.qgrid.mobile

import android.content.Intent
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.junit4.v2.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onFirst
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.platform.app.InstrumentationRegistry
import com.qgrid.mobile.data.ProgressRepository
import com.qgrid.mobile.game.CellPosition
import com.qgrid.mobile.game.LevelDefinition
import com.qgrid.mobile.game.LevelFactory
import com.qgrid.mobile.game.ProgressState
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import org.junit.Before
import org.junit.Rule
import org.junit.Test

class Line56AppSmokeTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Before
    fun resetLocalStateBeforeEachTest() {
        bringAppToFront()
        runBlocking {
            val repository = ProgressRepository(composeRule.activity.applicationContext)
            repository.clearLocalState()
            repository.setOnboardingSeen()
        }
        bringAppToFront()
        composeRule.waitForIdle()
        composeRule.waitUntil(timeoutMillis = 10_000) {
            currentProgress().completedLevelIds.isEmpty()
        }
        ensureHome()
    }

    @Test
    fun appShowsRussianProductName() {
        composeRule
            .onNodeWithText("Линия 56", substring = true)
            .assertIsDisplayed()
        composeRule
            .onNodeWithContentDescription("Прогресс: 0 из 36 уровней.")
            .assertIsDisplayed()
    }

    @Test
    fun gameScreenExposesAccessibleBoardAndControls() {
        val level = nextPlayableLevel()
        enterGame()

        composeRule.onNodeWithText("Сумма").assertIsDisplayed()
        composeRule.onNodeWithText("Цель").assertIsDisplayed()
        composeRule.onNodeWithText("Осталось").assertIsDisplayed()
        composeRule.onNodeWithText("Отмена").assertIsDisplayed()
        composeRule.onNodeWithText("Подсказка").assertIsDisplayed()
        composeRule.onNodeWithText("Сброс").assertIsDisplayed()
        composeRule
            .onAllNodesWithContentDescription("Клетка", substring = true)
            .assertCountEquals(level.size * level.size)
        composeRule
            .onAllNodesWithContentDescription("Клетка 1-1", substring = true)
            .onFirst()
            .assertIsDisplayed()
        composeRule.onNodeWithText("Подсказка").performClick()
        composeRule
            .onAllNodesWithContentDescription("подсказка", substring = true)
            .onFirst()
            .assertIsDisplayed()
    }

    @Test
    fun hintRepairMessageAppearsForDeadEndLine() {
        val level = LevelFactory.createLevels().first()
        val deadEndLine = listOf(
            CellPosition(row = 0, col = 0),
            CellPosition(row = 0, col = 1),
            CellPosition(row = 0, col = 2),
            CellPosition(row = 1, col = 3),
            CellPosition(row = 0, col = 4),
        )

        startLevel(level)
        deadEndLine.forEach(::tapCell)
        composeRule.onNodeWithText("Подсказка").performClick()

        composeRule
            .onNodeWithText("нельзя довести до 56", substring = true)
            .performScrollTo()
            .assertIsDisplayed()
        composeRule
            .onAllNodesWithContentDescription("подсказка", substring = true)
            .assertCountEquals(0)
    }

    @Test
    fun completedLevelPersistsAfterActivityRecreation() {
        val level = LevelFactory.createLevels().first()

        startLevel(level)
        completeLevel(level)

        composeRule.activityRule.scenario.recreate()
        composeRule.waitUntil(timeoutMillis = 5_000) {
            currentProgress().completedLevelIds.contains(level.id) &&
                (hasText("56 собрано") || hasText("Прогресс"))
        }
        if (hasText("56 собрано")) {
            composeRule.onNodeWithText("Следующий уровень").performScrollTo().assertIsDisplayed()
        } else {
            composeRule.onNodeWithText("${currentProgress().completedLevelIds.size} / 36").assertIsDisplayed()
        }
    }

    @Test
    fun completingSeveralLevelsAdvancesProgress() {
        val levels = LevelFactory.createLevels().take(3)

        startLevel(levels.first())
        levels.forEachIndexed { index, level ->
            completeLevel(level)
            if (index < levels.lastIndex) {
                composeRule
                    .onNodeWithText("Следующий уровень")
                    .performScrollTo()
                    .performClick()
                waitForLevelBoard(levels[index + 1])
            }
        }

        composeRule.waitUntil(timeoutMillis = 5_000) {
            currentProgress().completedLevelIds.containsAll(levels.map { it.id })
        }
    }

    @Test
    fun highestLevelResultOffersLevelsFallbackAction() {
        val level = LevelFactory.createLevels().last()

        startLevel(level)
        completeLevel(level)

        composeRule
            .onNodeWithText("К уровням")
            .performScrollTo()
            .assertIsDisplayed()
        composeRule
            .onAllNodesWithText("Следующий уровень")
            .assertCountEquals(0)
        composeRule
            .onNodeWithText("К уровням")
            .performScrollTo()
            .performClick()

        composeRule.onNodeWithText("Выберите уровень").assertIsDisplayed()
        composeRule
            .onNodeWithContentDescription(levelTileDescription(level))
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun completedResultCanReplayCurrentLevel() {
        val level = LevelFactory.createLevels().first()

        startLevel(level)
        completeLevel(level)

        composeRule
            .onNodeWithText("Повторить")
            .performScrollTo()
            .assertIsDisplayed()
            .performClick()

        waitForLevelBoard(level)
        composeRule.onNodeWithText("Линия пока пустая.").assertIsDisplayed()
        composeRule
            .onAllNodesWithContentDescription("выбрана", substring = true)
            .assertCountEquals(0)
        composeRule
            .onAllNodesWithText("56 собрано")
            .assertCountEquals(0)
    }

    @Test
    fun gameBackReturnsToEntryScreen() {
        ensureHome()

        val homeLevel = nextPlayableLevel()
        composeRule
            .onAllNodesWithText(if (hasText("Продолжить")) "Продолжить" else "Начать")
            .onFirst()
            .performClick()
        waitForLevelBoard(homeLevel)
        composeRule
            .onAllNodesWithContentDescription("Назад")
            .onFirst()
            .performClick()
        composeRule.onNodeWithText("Прогресс").assertIsDisplayed()

        val listLevel = nextPlayableLevel()
        composeRule.onNodeWithText("Уровни").performClick()
        composeRule
            .onNodeWithContentDescription(levelTileDescription(listLevel))
            .performScrollTo()
            .performClick()
        waitForLevelBoard(listLevel)
        composeRule
            .onAllNodesWithContentDescription("Назад")
            .onFirst()
            .performClick()
        composeRule.onNodeWithText("Выберите уровень").assertIsDisplayed()
    }

    @Test
    fun settingsScreenExposesAccessibleOptions() {
        ensureHome()

        composeRule
            .onNodeWithContentDescription("Настройки")
            .assertIsEnabled()
            .performClick()

        composeRule.onNodeWithText("Тактильный отклик").assertIsDisplayed()
        composeRule.onNodeWithText("Повышенный контраст").assertIsDisplayed()
        composeRule.onNodeWithText("Меньше движения").assertIsDisplayed()
    }

    @Test
    fun aboutScreenExposesPrivacyPolicyText() {
        ensureHome()

        composeRule
            .onNodeWithText("О проекте")
            .assertIsEnabled()
            .performClick()

        composeRule.onNodeWithText("Приватность").assertIsDisplayed()
        composeRule
            .onNodeWithText("не собирает персональные данные", substring = true)
            .assertIsDisplayed()
        composeRule
            .onNodeWithText("прогресс уровней и настройки интерфейса", substring = true)
            .assertIsDisplayed()
        composeRule
            .onNodeWithText("Android backup отключён", substring = true)
            .performScrollTo()
            .assertIsDisplayed()
        composeRule
            .onNodeWithText("очистите данные приложения", substring = true)
            .performScrollTo()
            .assertIsDisplayed()
    }

    private fun enterGame() {
        ensureHome()
        composeRule
            .onAllNodesWithText(if (hasText("Продолжить")) "Продолжить" else "Начать")
            .onFirst()
            .performClick()
        val expectedCells = nextPlayableLevel().size * nextPlayableLevel().size
        composeRule.waitUntil(timeoutMillis = 5_000) {
            cellNodeCount() == expectedCells
        }
    }

    private fun startLevel(level: LevelDefinition) {
        ensureHome()
        composeRule.onNodeWithText("Уровни").performClick()
        val description = levelTileDescription(level)
        composeRule
            .onNodeWithContentDescription(description)
            .performScrollTo()
            .performClick()
        waitForLevelBoard(level)
    }

    private fun completeLevel(level: LevelDefinition) {
        level.solutionPath.forEach { position ->
            tapCell(position)
        }

        composeRule.waitUntil(timeoutMillis = 5_000) {
            hasText("56 собрано")
        }
        composeRule.onNodeWithText("56 собрано").performScrollTo().assertIsDisplayed()
        composeRule.waitUntil(timeoutMillis = 5_000) {
            currentProgress().completedLevelIds.contains(level.id)
        }
    }

    private fun tapCell(position: CellPosition) {
        composeRule
            .onAllNodesWithContentDescription(
                "Клетка ${position.row + 1}-${position.col + 1}",
                substring = true,
            )
            .onFirst()
            .performScrollTo()
            .performClick()
    }

    private fun waitForLevelBoard(level: LevelDefinition) {
        composeRule.waitUntil(timeoutMillis = 5_000) {
            cellNodeCount() == level.size * level.size
        }
    }

    private fun cellNodeCount(): Int = try {
        composeRule
            .onAllNodesWithContentDescription("Клетка", substring = true)
            .fetchSemanticsNodes()
            .size
    } catch (_: IllegalStateException) {
        0
    }

    private fun levelTileDescription(level: LevelDefinition): String {
        val title = "Уровень ${level.id}"
        val completed = "$title, Пройден"
        return if (hasContentDescription(completed)) {
            completed
        } else {
            "$title, Доступен"
        }
    }

    private fun ensureHome() {
        bringAppToFront()
        composeRule.waitUntil(timeoutMillis = 10_000) {
            !hasText("Загрузка")
        }
        repeat(6) {
            when {
                hasText("Прогресс") -> return
                hasText("Соединяйте соседние клетки", substring = true) ||
                    hasText("Можно двигаться", substring = true) -> {
                    composeRule
                        .onAllNodesWithText("Начать")
                        .onFirst()
                        .performClick()
                    composeRule.waitForIdle()
                }
                hasText("Выберите уровень") ||
                    hasText("56 собрано") ||
                    hasText("Настройки") ||
                    hasText("Приватность") ||
                    hasContentDescription("Назад", substring = true) -> {
                    pressBack()
                    composeRule.waitForIdle()
                }
                else -> {
                    bringAppToFront()
                    composeRule.waitForIdle()
                }
            }
        }
        composeRule.waitUntil(timeoutMillis = 10_000) {
            hasText("Прогресс")
        }
    }

    private fun bringAppToFront() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val launchIntent = checkNotNull(context.packageManager.getLaunchIntentForPackage(context.packageName)) {
            "Missing launcher intent for ${context.packageName}"
        }
        launchIntent.addFlags(
            Intent.FLAG_ACTIVITY_NEW_TASK or
                Intent.FLAG_ACTIVITY_CLEAR_TOP or
                Intent.FLAG_ACTIVITY_SINGLE_TOP,
        )
        context.startActivity(launchIntent)
        composeRule.waitForIdle()
    }

    private fun pressBack() {
        composeRule.activityRule.scenario.onActivity { activity ->
            activity.onBackPressedDispatcher.onBackPressed()
        }
    }

    private fun nextPlayableLevel(): LevelDefinition {
        val completed = currentProgress().completedLevelIds
        val levels = LevelFactory.createLevels()
        return levels.firstOrNull { it.id !in completed } ?: levels.last()
    }

    private fun currentProgress(): ProgressState = runBlocking {
        ProgressRepository(composeRule.activity.applicationContext)
            .progressFlow
            .first()
    }

    private fun hasText(
        text: String,
        substring: Boolean = false,
    ): Boolean = try {
        composeRule
            .onAllNodesWithText(text, substring = substring)
            .fetchSemanticsNodes()
            .isNotEmpty()
    } catch (_: IllegalStateException) {
        false
    }

    private fun hasContentDescription(
        description: String,
        substring: Boolean = false,
    ): Boolean = try {
        composeRule
            .onAllNodesWithContentDescription(description, substring = substring)
            .fetchSemanticsNodes()
            .isNotEmpty()
    } catch (_: IllegalStateException) {
        false
    }
}
