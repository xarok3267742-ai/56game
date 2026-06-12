# Линия 56

Нативная Android-first числовая головоломка для коротких offline-сессий. Игрок соединяет соседние клетки так, чтобы сумма выбранной линии стала ровно 56.

## Почему эта идея

«Линия 56» выбрана как небольшой, понятный и безопасный MVP для Google Play: без backend, аккаунтов, платежей, рекламы, персональных данных, `INTERNET` permission и спорных категорий. Механика быстро объясняется, хорошо работает на слабых устройствах и не требует дорогих ассетов.

## Стек

- Kotlin
- Jetpack Compose + Material 3
- Android Gradle Plugin 8.11.1
- Gradle wrapper 8.14.5
- DataStore Preferences для локального прогресса
- Unit tests + Compose instrumentation tests for product name, accessible board/controls, settings semantics, multi-level completion and progress persistence

`applicationId`: `com.qgrid.mobile`

## Команды

```bash
./gradlew test
./gradlew assembleDebug
./gradlew assembleRelease
./gradlew lint
./gradlew connectedDebugAndroidTest
./gradlew bundleRelease
./tools/run_final_local_gate.py
./tools/run_final_local_gate.py --include-hosted-privacy
./tools/run_final_local_gate.py --include-connected --connected-serial <serial>
./tools/run_final_local_gate.py --include-connected --connected-serial <serial> --include-hosted-privacy
./tools/run_api36_connected_gate.py
./tools/run_api36_connected_gate.py --include-hosted-privacy
./tools/verify_release.py
./tools/print_upload_packet.py
./tools/print_post_upload_evidence_packet.py
./tools/print_privacy_contact_evidence_packet.py
./tools/print_play_console_forms_evidence_packet.py
./tools/print_pre_launch_review_evidence_packet.py
./tools/print_store_listing_review_evidence_packet.py
./tools/create_store_asset_review_sheet.py --dry-run
./tools/create_store_asset_review_sheet.py --write
./tools/prepare_play_upload_archive.py --dry-run
./tools/prepare_play_upload_archive.py --verify-existing
./tools/prepare_play_upload_archive.py --write
./tools/print_play_console_packet.py
./tools/print_publication_readiness.py
./tools/verify_play_generated_apk.py --dry-run
./tools/check_privacy_policy_url.py --local
./tools/check_signing_backup_inputs.py
./tools/print_signing_backup_evidence_packet.py
./tools/verify_remote_release.py
ANDROID_SERIAL=<serial> ./tools/capture_store_screenshots.py --serial <serial>
```

Если проект открыт на новой машине, создайте локальный `local.properties`:

```properties
sdk.dir=/path/to/Android/sdk
```

## Структура

- `app/src/main/java/com/qgrid/mobile/game` - чистая игровая логика, генератор уровней, reducer.
- `app/src/main/java/com/qgrid/mobile/data` - локальный DataStore progress/settings.
- `app/src/main/java/com/qgrid/mobile/ui` - Compose screens, ViewModel, theme.
- `app/src/test` - unit tests для core logic.
- `app/src/androidTest` - emulator smoke and persistence tests.
- `docs` - продуктовая, техническая, QA и release документация.
- `play_store` - listing copy, privacy/data-safety notes, upload manifest and real phone/large-tablet screenshots.
- `docs/requirements_traceability.md` - матрица покрытия исходных RTF-фаз, локальных доказательств и внешних manual gates.

## Release status

Debug APK собран: `app/build/outputs/apk/debug/app-debug.apk`.

Release AAB собран: `app/build/outputs/bundle/release/app-release.aab`.

Production package остаётся нейтральным: `com.qgrid.mobile`; debug package: `com.qgrid.mobile.debug`.

Version identity for this upload candidate: `versionCode = 1`, `versionName = 1.0.0`.

Текущий release AAB: `2,930,928` bytes, SHA-256 `3affd5cc6de7735d7cb9cc4f381e114caa0b20d6bfa933621d596d24dc2e3043`.

For Google Play, the signed AAB is the only binary upload artifact. Generated release APK outputs under `app/build/outputs/apk/release` are install/testing artifacts only and must not be uploaded to Play.

Последняя локальная проверка на 6 июня 2026: `./tools/verify_release.py` прошёл с gates для Google Play sources, product decision, performance notes, assets, privacy/safety handoff, signing report, metadata, release cleanliness, fresh debug/release artifact evidence and mandatory fresh connected XML evidence. `./gradlew test lint assembleDebug assembleRelease bundleRelease` прошёл. Последний connected run выполнил 10/10 тестов на `Medium_Phone_API_36(AVD) - 16`, включая fallback `К уровням` после победы на последнем уровне, replay результата через `Повторить`, возврат из игры к исходному экрану and hint repair feedback for a dead-end line; TalkBack exploratory pass выполнен отдельно на API 36 Play Store AVD, artifacts сохранены в `docs/qa_artifacts`.

Offline release smoke passed on API 35 with airplane mode enabled and Wi-Fi disabled: onboarding, home and the level-1 game board were reached without network access, with visual evidence in `docs/qa_artifacts/offline_release_smoke_onboarding.png` and `docs/qa_artifacts/offline_release_smoke_game.png`.

Последняя навигационная правка: действие `Следующий уровень` после победы берёт следующий id из выигранного `gameState.level` через `currentGameNextLevelId`, поэтому результат не зависит от устаревшего `currentLevel`.

Последняя asset-правка на 6 июня 2026: Google Play/app launcher icon заменён на встроенно сгенерированный ImageGen raster icon без текста; `play_store/icon/play_icon_512.png` и `app/src/main/res/drawable-nodpi/ic_launcher_imagegen.png` синхронизированы как full-square PNG с непрозрачной альфой, splash и onboarding brand mark используют тот же raster asset, Play screenshots пересняты с release app, phone screenshots нормализованы до Play-compliant 1080x2064, tablet screenshots нормализованы до 1600x2336, системные полосы убраны из upload images, и `play_store/upload_checksums.md` обновлён.

Подписанный release AAB использует локальный upload keystore из ignored `private/signing/qgrid-upload.p12`; credentials лежат в ignored `keystore.properties`. Public certificate fingerprints documented in `play_store/signing_certificate_report.md`. Перед публикацией обязательно запустить `./tools/check_signing_backup_inputs.py`, сделать безопасный backup signing files and record only safe owner evidence in `play_store/signing_backup_evidence_ru.md`.

Google Play store icon лежит в `play_store/icon/play_icon_512.png`, feature graphic - в `play_store/feature_graphic.png`, реальные phone screenshots - в `play_store/screenshots/phone`, реальные large/tablet screenshots - в `play_store/screenshots/tablet`. Store asset review sheet лежит в `play_store/store_asset_review_sheet.png` and is internal review evidence only, not a Play upload asset. Upload manifest лежит в `play_store/upload_manifest.md`, upload runbook - в `play_store/upload_runbook_ru.md`, post-upload evidence template - в `play_store/play_console_post_upload_evidence_ru.md`, signing backup evidence and owner template - в `play_store/signing_backup_evidence_ru.md`, upload checksums - в `play_store/upload_checksums.md`, Play Console field handoff - в `play_store/play_console_submission_ru.md`, closed-testing handoff - в `play_store/closed_testing_handoff_ru.md`, production-access answer worksheet - в `play_store/production_access_answers_ru.md`, privacy/contact handoff - в `play_store/privacy_contact_handoff_ru.md`, owner-controlled release inputs - в `play_store/owner_release_inputs.md`, owner-action breakdown - в `play_store/publication_readiness_owner_actions_ru.md`, signing certificate report - в `play_store/signing_certificate_report.md`, alt text - в `play_store/asset_alt_text_ru.md`. `./tools/run_final_local_gate.py` runs the complete final local gate and prints `final_local_gate_ok` only after build/test/verifier/handoff helpers pass. Add `--include-hosted-privacy` for a networked pre-upload run that also revalidates the recorded hosted privacy policy URL. It builds `assembleRelease` only as a local install/testing APK sanity artifact, while Google Play upload still uses the signed AAB. Before optional connected execution it cleans generated connected-test outputs, force-stops/kills the current production package `com.qgrid.mobile` plus known stale local package processes, and uninstalls known stale local debug/test packages on the selected serial, including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`, so stale local artifacts or old instrumentation packages cannot pollute verifier evidence or steal focus. When an API 36 emulator/device is available, `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` refreshes `connectedDebugAndroidTest` evidence before the verifier. `./tools/run_api36_connected_gate.py` boots the project-owned `Medium_Phone_API_36` AVD on `emulator-5560` with `-wipe-data`, retries the cleaned AVD once without `-wipe-data` if the emulator exits after the wipe reset before boot, runs that connected final gate, can pass through `--include-hosted-privacy` for the networked upload-day preflight, and stops only the emulator it started; `--preserve-avd-data` is for diagnostics only when stale installed packages must be retained intentionally. `./tools/print_upload_packet.py` prints and verifies the exact ordered upload packet from the current checksum manifest, including the required AAB, icon, feature graphic, five phone screenshots and five large/tablet screenshots. `./tools/print_post_upload_evidence_packet.py` prints safe upload artifact and internal-testing evidence lines for `play_store/play_console_post_upload_evidence_ru.md`; after the real Play Console upload, rerun it with `--upload-date <date/time>` for a concrete upload-date line. `./tools/print_privacy_contact_evidence_packet.py` prints safe privacy URL and support/contact evidence lines for `play_store/play_console_post_upload_evidence_ru.md`; use it only after the Play Console support/contact field is actually populated and the hosted privacy URL validates, and do not record the actual support email or support website URL. `./tools/print_play_console_forms_evidence_packet.py` prints safe Play Console policy-form evidence lines for `play_store/play_console_post_upload_evidence_ru.md`; use it only after the App access, ads, Data Safety, content rating, target audience and AI disclosure forms are actually completed. `./tools/create_store_asset_review_sheet.py --write` regenerates the internal visual review sheet so icon, feature graphic and phone/tablet screenshots can be inspected together for damaging crops before Play Console preview. `./tools/print_store_listing_review_evidence_packet.py` prints the safe store-listing preview crop evidence line after the Play Console preview and current review sheet are actually checked. `./tools/prepare_play_upload_archive.py --write` creates a generated owner handoff ZIP under `build/play_upload` with only the verified AAB/assets plus safe handoff notes; `./tools/prepare_play_upload_archive.py --verify-existing` verifies that ZIP against current upload assets and handoff notes. Please unpack it for upload day and do not upload the ZIP itself to Play Console. `./tools/print_play_console_packet.py` prints and verifies the copy-ready Play Console listing/App content packet and manual owner gates. `./tools/print_publication_readiness.py` prints `publication_readiness_local_ready_external_pending` while external Play Console URL-entry, support contact, signing backup, testing-track evidence and production-access evidence if required are unresolved, and groups unresolved owner actions by evidence file and required command. `./tools/verify_play_generated_apk.py --dry-run` documents the Play-generated APK review posture; after Play creates an APK artifact, run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` before rollout. `./tools/check_signing_backup_inputs.py` verifies the active ignored signing inputs without printing password values. `./tools/print_signing_backup_evidence_packet.py` prints safe signing-backup evidence lines for `play_store/signing_backup_evidence_ru.md` and matching backup lines for `play_store/play_console_post_upload_evidence_ru.md`; after the real owner-controlled backup, rerun it with `--backup-date <date/time>` for a concrete backup-date line. After pushing, `./tools/verify_remote_release.py --tag <release-tag>` verifies `origin/main`, the annotated remote release tag, every remote upload asset checksum from `play_store/upload_checksums.md`, rejects extra remote `.aab` files outside `app/build/outputs/bundle/release/app-release.aab`, checks case-insensitive remote signing/install artifact hygiene, verifies `origin/gh-pages` privacy-policy presence and validates the recorded hosted privacy URL. `play_store/icon/play_icon_preview_masked.png` is a local mask preview only; upload the full-square `play_store/icon/play_icon_512.png` because Google Play applies its own mask. Старый слабый feature graphic concept оставлен только в `play_store/archive/feature_graphic_concept.png`; отклонённые launcher/store icon variants сохранены только как `play_store/archive/icon_imagegen_20260605_rejected.png` and `play_store/archive/icon_imagegen_20260606_rejected_owner_review.png`.

`./tools/print_pre_launch_review_evidence_packet.py` prints safe Play pre-launch/policy review evidence lines for `play_store/play_console_post_upload_evidence_ru.md`; use it only after the Play Console pre-launch report and policy warnings are actually reviewed.

Store screenshots are reproducible through `tools/capture_store_screenshots.py`; run it against a booted API 35 emulator after visible UI changes. The script refreshes phone/tablet screenshots, crops phone captures to Play-compliant 1080x2064 PNGs, crops tablet captures to 1600x2336, rebuilds the feature graphic, updates `play_store/upload_checksums.md`, prints the current checksum rows and then `./tools/verify_release.py` should pass.

Локально подготовленный release candidate не равен опубликованному Google Play продукту. Перед публикацией ещё нужно ввести проверенный hosted privacy URL `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` в Play Console, заполнить рабочий Play Console support contact, при необходимости повторно проверить URL командой `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`, сделать backup keystore/credentials after `./tools/check_signing_backup_inputs.py` returns `signing_backup_input_ok`, заполнить Play Console forms, run required testing tracks for the publisher account type and receive Play Console production access if required.
