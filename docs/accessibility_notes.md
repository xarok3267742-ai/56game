# Accessibility Notes

## Реализовано

- Крупные числовые клетки около 180dp на 5x5 поле в проверенном viewport.
- Tap targets для кнопок и клеток больше 48dp.
- Важные состояния не зависят только от цвета: сумма, остаток и текст состояния обновляются.
- У клеток есть content descriptions: ряд, колонка, число, состояние выбора, подсказка и превышение суммы.
- Есть high contrast setting.
- Undo disabled state видим и семантически disabled.
- Тексты на русском, без технических сообщений пользователю.
- Reduced motion setting is functional: cell state color/elevation transitions use zero-duration animation when `Меньше движения` is enabled.
- Haptics setting is precise: cell haptic feedback is emitted only after the selected path actually grows, and victory feedback is emitted only on transition into the won state.
- Compact landscape game layout keeps score, status text, action controls and the full 5x5 board in one viewport on wide/low-height screens.

## Проверено

ADB UI tree на API 35 показал onboarding, home, game field и controls без обрезки в основном viewport.
Manual compact pass on API 35: 720x1280 override, density 320, `font_scale=1.3`; onboarding button remained fully visible and readable.
Targeted compact About/privacy pass after the in-app privacy UI refactor reached home, exposed the `О проекте` action and captured top/bottom About screenshots at 720x1280, density 320, `font_scale=1.3`. The top capture shows `Приватность`, no-personal-data, local-progress/settings, no-services and Android backup copy; the scrolled bottom capture shows Android backup and local deletion copy. QA artifacts are `docs/qa_artifacts/compact_about_top.png` and `docs/qa_artifacts/compact_about_bottom.png`.
Large/wide exploratory pass on API 35: 2400x1080 landscape and 1600x2560 tall overrides kept onboarding readable and tappable.
Compose instrumentation now checks accessible cell descriptions, score labels, game controls, settings labels, About/privacy copy, hint repair feedback with no stale hinted cell, multi-level completion, highest-level result fallback, result-panel replay with `Повторить`, game-back return to the entry screen and completion/persistence flow; latest API 36 connected run passed 10 tests.
Manual game landscape pass on API 35: debug APK, 2400x1080, `font_scale=1.3`; all 25 cells and `Отмена`/`Подсказка`/`Сброс` were visible in the same viewport.
Force-stop/relaunch after completion showed home progress and continue action, so saved state remains understandable after restart.
Latest release relaunch smoke check used `tools/capture_release_relaunch_smoke.py` on `Medium_Phone_API_36` / API 36 with `expected_api=36` validation. The release app returned to home `Прогресс` after a HOME background return and after force-stop/relaunch, onboarding was not shown again, the home start action remained visible and the crash buffer had no matching app entries. Evidence: `docs/qa_artifacts/release_relaunch_state.txt` and `docs/qa_artifacts/release_relaunch_home.png`.
UIAutomator accessibility-tree audit on API 35 with `font_scale=1.3` captured onboarding, home, settings and game screens to neutral `/tmp/qgrid-a11y-*.xml` and `/tmp/qgrid-a11y-*.png` files. The game tree exposed 25 cell descriptions, score/action labels and a minimum checked cell size of 182px; onboarding, home and settings exposed the expected Russian labels and navigation descriptions.
TalkBack exploratory pass completed on `Medium_Phone_API_36`, a Play Store AVD with Android Accessibility Suite installed. `com.google.android.marvin.talkback/.TalkBackService` was enabled, `accessibility_enabled=1`, `touchExplorationEnabled=true`, and `dumpsys accessibility` showed bound service label `TalkBack`. With TalkBack active, the release app was driven through onboarding, home, game, settings and About/privacy using focus tap + double-tap activation. QA artifacts are `docs/qa_artifacts/talkback_state.txt`, `docs/qa_artifacts/talkback_onboarding.png`, `docs/qa_artifacts/talkback_home.png`, `docs/qa_artifacts/talkback_game.png`, `docs/qa_artifacts/talkback_settings.png` and `docs/qa_artifacts/talkback_about.png`.

## Оставшиеся проверки

- Optional physical-device TalkBack audio/speech review after Play-generated APK install; the local headless AVD pass verifies service activation, touch exploration and UI traversal but not speaker output quality.
