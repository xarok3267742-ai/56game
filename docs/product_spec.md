# Product Spec

## Product Name

Линия 56

## Type And Genre

Native Android game. Casual numeric puzzle for short offline sessions.

## One-Sentence Pitch

Соединяйте соседние числа и соберите непрерывную линию ровно на 56.

## Elevator Pitch

«Линия 56» - спокойная offline-first головоломка на внимательность и счёт. Игрок выбирает соседние клетки на компактном поле, следит за текущей суммой и старается остановиться ровно на 56 без повторного использования клеток.

## Target Audience

- Русскоязычные Android-пользователи.
- Casual-аудитория, которой нужен быстрый понятный игровой опыт.
- Пользователи слабых и средних устройств.
- Люди, которые предпочитают игры без аккаунта, рекламы, платежей и обязательного интернета.

## User Need

Пользователю нужна короткая, понятная и спокойная игра на несколько минут: без длинного обучения, соревновательного давления, подписок или сложных правил.

## Core Value Proposition

Простая цель, ясная обратная связь и короткие уровни: игрок видит числа, строит линию и сразу понимает, насколько близко он к сумме 56.

## Core Loop

1. Игрок запускает приложение.
2. Если это первый запуск, видит короткий onboarding из трёх правил.
3. Игрок продолжает следующий уровень или открывает список уровней.
4. На игровом поле выбирает соседние клетки без повторов.
5. Приложение постоянно показывает текущую сумму, остаток до 56 и состояние линии.
6. Если сумма меньше 56, игрок продолжает линию.
7. Если ход невозможен или сумма превысила 56, игрок использует отмену, подсказку или сброс.
8. Если сумма ровно 56, уровень засчитывается и прогресс сохраняется.
9. Игрок переходит к следующему уровню или возвращается к списку уровней, если числового следующего уровня нет.

## Main Screens

- Onboarding: название, цель игры, три правила, старт.
- Home: прогресс, быстрый запуск, переход к уровням, настройки и about/privacy.
- Levels: список 36 уровней с состоянием прохождения и сложностью.
- Game: цель, текущая сумма, остаток, поле, линия выбора, сообщения, действия.
- Result panel: подтверждение победы, следующий уровень при наличии следующего числового уровня, иначе возврат к списку уровней.
- Settings: тактильный отклик, повышенный контраст, уменьшение движения.
- About/privacy: краткое описание и privacy posture.

## Main Features

- 36 deterministic уровней.
- Гарантированное решение каждого уровня на сумму 56.
- Независимый solver проверяет достижимость цели по самой доске, отдельно от stored canonical path, and powers current-line hint repair checks.
- Выбор соседних клеток по горизонтали, вертикали и диагонали.
- Запрет повторного использования клетки в одной линии.
- Постоянный счётчик суммы и остатка.
- Feedback для несоседней клетки, повтора, превышения суммы и победы.
- Подсказка стартовой или следующей клетки от текущей линии; если текущую линию уже нельзя довести до 56, сообщение предлагает отменить ход или сбросить линию.
- Отмена последнего хода.
- Сброс текущей линии.
- Сохранение onboarding/progress/settings через DataStore with range normalization for completed levels and last level.
- Русский UI, string resources.
- No ads, no analytics, no accounts, no payments, no backend, no dangerous permissions.

## Game Rules

- Цель каждого уровня: набрать ровно 56.
- Игрок может начать линию с любой клетки.
- Следующая клетка должна быть соседней с предыдущей.
- Соседство включает 8 направлений: горизонталь, вертикаль и диагональ.
- Клетку нельзя выбрать повторно в одной линии.
- При сумме больше 56 игра не заканчивается, но показывает error feedback.
- После превышения можно отменить ход или сбросить линию.
- Пока сумма превышена, новые клетки и подсказка недоступны; игрок должен сначала откатить или сбросить линию.
- Победа наступает сразу, когда сумма выбранных клеток равна 56.

## Progression

- Всего 36 уровней.
- Уровни 1-12: спокойная сложность, 5x5, короткие решения.
- Уровни 13-24: средняя сложность, 5x5, длиннее решения.
- Уровни 25-36: внимательная сложность, 6x6, более длинные решения.
- Все уровни доступны из списка; прогресс показывает, что уже пройдено.
- Replay остаётся доступным: игрок может переиграть любой уровень.

## Win, Loss And Final State

- Win: сумма стала ровно 56, уровень отмечается пройденным.
- Loss: отсутствует как жёсткое состояние; ошибка всегда обратима через undo/reset.
- Final MVP state: после прохождения всех 36 уровней home показывает полный прогресс, result panel пишет «Все уровни пройдены», а последний уровень остаётся доступным для повторного прохождения.
- Result replay: после победы result panel показывает `Повторить`, запускает новый чистый `GameState` для того же уровня и не удаляет сохранённый прогресс.
- Passing the highest-numbered level alone is not treated as full completion; the all-complete copy appears only after all available level ids are complete, including the just-won current level.
- Result action: after win the primary result action is «Следующий уровень» only when a higher available level id exists; otherwise it is «К уровням», so the result panel always leaves the player with an explicit next step.

## Rewards

- Основная награда: прогресс уровня и ощущение чистого решения.
- Дополнительных валют, очков, streak, leaderboard или daily rewards в MVP нет.

## Difficulty Design

- Сложность растёт через размер поля и длину solution path.
- Числа остаются небольшими и читаемыми.
- Подсказка снижает риск застревания без добавления сложной системы обучения: она продолжает текущую жизнеспособную линию, а для тупиковой линии явно предлагает undo/reset.

## Replay Value

- Игрок может проходить уровни повторно.
- На поле возможны альтернативные попытки и самостоятельный поиск другой линии.
- Offline-first формат поддерживает короткие возвраты без расписания или live events.

## First Launch Scenario

1. Приложение открывается на onboarding.
2. Игрок читает цель и три правила.
3. Нажимает «Начать».
4. Попадает на home.
5. Нажимает «Начать» и открывает первый уровень.

## Regular Session Scenario

1. Игрок открывает приложение.
2. Home показывает текущий прогресс.
3. Игрок нажимает «Продолжить»: если последний выбранный уровень ещё не пройден, игра возвращает его; иначе открывает первый непройденный уровень.
4. Проходит один или несколько коротких уровней.
5. Возвращается домой или закрывает приложение; прогресс сохранён.

## UI Style

- Чистый mobile-first puzzle UI.
- Контрастные числовые плитки.
- Спокойная палитра: зелёный основной, тёплый золотой акцент, синий tertiary, глиняный secondary, светлый mist background.
- 4-8dp radii без heavy pill style.
- Иконки Material/Lucide-like through Material Icons where available.
- Минимум декоративных элементов: визуальный фокус на числах, линии и состоянии суммы.

## Tone Of Voice

- Спокойный, понятный, короткий.
- Без технического жаргона.
- Ошибки формулируются как обратимые действия: «Отмените ход или сбросьте линию».
- Нет агрессивной соревновательной или рекламной лексики.

## Content Structure

- Onboarding rules.
- Home description.
- Level titles and difficulty labels.
- Game messages.
- Settings labels/descriptions.
- About/privacy copy, including in-app privacy policy text for local-only progress/settings, no data collection/sharing, no ads/analytics/accounts/payments/internet permissions, Android backup disabled and local deletion through Android app data clearing or uninstall.
- Google Play listing, release notes, data-safety notes and privacy policy draft.

## State Handling

- Loading: короткий экран «Загрузка» до чтения DataStore.
- Empty: пустая линия показывает понятное состояние «Линия пока пустая».
- Error: несоседняя клетка, повтор клетки и превышение суммы имеют отдельные сообщения.
- Exceeded lock: после превышения 56 поле не принимает дальнейший ввод до undo/reset.
- Success: победа показывает «56 собрано» и действие «Следующий уровень».
- Persistence: onboarding, completed levels, last level and settings survive restart.
- Continue routing: the primary home action resumes the last selected incomplete level, falls back to the first incomplete level, and after all levels are complete keeps the last level replayable.
- Corrupt local progress recovery: invalid completed level ids are ignored, and last level is clamped to the valid 1-36 range.
- Level navigation guard: direct start/continue navigation clamps invalid requested level ids into the valid 1-36 range.
- DataStore I/O fallback: if progress preferences cannot be read because of an I/O error, the app falls back to safe default progress/settings instead of crashing the UI flow.

## Privacy Impact

Privacy impact intentionally minimal:

- No personal data collection.
- No network dependency.
- No accounts.
- No ads or analytics SDK.
- No dangerous permissions.
- Local progress/settings only.
- Android backup disabled, so local progress/settings are not included in cloud backup/restore.

## Non-Goals

- Multiplayer.
- Backend.
- Real-time updates.
- Accounts.
- Ads, IAP or subscriptions.
- Analytics/crash reporting SDK.
- Daily online events.
- Leaderboard.
- User-generated content.
- Story campaign.
- Complex economy.
- 3D graphics or heavy assets.

## MVP Success Criteria

- Игрок понимает цель на первом запуске.
- Игрок может начать и пройти уровень без внешней инструкции.
- Все 36 уровней имеют гарантированное решение.
- Unit tests prove every generated board is independently solvable by `LevelSolver`.
- Сумма, остаток, ошибки и победа видны в UI.
- Подсказка, undo and reset work, including current-line continuation and repair feedback when the current selection cannot reach 56.
- Progress/settings persist after app recreation/restart.
- UI remains readable on checked small/large/wide screens.
- Product has no placeholder user-facing content.
- Debug, unit, lint, release bundle and connected smoke checks pass where environment allows.
- Google Play handoff docs and release report are present.
