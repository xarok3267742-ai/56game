# Google Play Upload Runbook - RU

Этот runbook описывает порядок ручной загрузки локального release candidate в Google Play Console. Он не заменяет Play Console review и не закрывает внешние owner-controlled gates.

## 1. Локальный Preflight Перед Загрузкой

Запускать из корня проекта:

```bash
./tools/run_final_local_gate.py
```

Если сеть доступна перед загрузкой и нужно повторно проверить уже записанный hosted privacy URL:

```bash
./tools/run_final_local_gate.py --include-hosted-privacy
```

Если доступен стабильный API 36 эмулятор или устройство, используйте connected-вариант одной командой:

```bash
./tools/run_final_local_gate.py --include-connected --connected-serial <serial>
```

Если нужно безопасно запустить project-owned API 36 AVD автоматически:

```bash
./tools/run_api36_connected_gate.py
./tools/run_api36_connected_gate.py --include-hosted-privacy
```

Equivalent expanded sequence:

```bash
./gradlew test
./gradlew assembleDebug
./gradlew lint
./gradlew assembleRelease
./gradlew bundleRelease
./tools/verify_release.py
./tools/print_upload_packet.py
./tools/create_store_asset_review_sheet.py --dry-run
./tools/prepare_play_upload_archive.py --dry-run
./tools/prepare_play_upload_archive.py --verify-existing
./tools/print_play_console_packet.py
./tools/print_publication_readiness.py
./tools/verify_play_generated_apk.py --dry-run
./tools/check_privacy_policy_url.py --local
./tools/check_signing_backup_inputs.py
```

Connected-вариант добавляет перед verifier:

```bash
ANDROID_SERIAL=<serial> ./gradlew connectedDebugAndroidTest
```

Перед upload убедиться:

- `./tools/run_final_local_gate.py` возвращает `final_local_gate_ok`.
- `./tools/run_final_local_gate.py --include-hosted-privacy` возвращает `final_local_gate_ok` when network access is available and the recorded hosted privacy URL still passes `privacy_policy_url_ok`.
- При доступном API 36 устройстве `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` тоже возвращает `final_local_gate_ok`, очищает generated connected outputs, force-stops `com.qgrid.mobile`, удаляет stale local debug/test packages including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`, и обновляет connected evidence перед verifier.
- `./tools/run_api36_connected_gate.py` возвращает `api36_connected_gate_ok`, если helper сам поднимает `Medium_Phone_API_36`, прогоняет connected final gate и безопасно останавливает только свой эмулятор; добавьте `--include-hosted-privacy`, когда сеть доступна и нужно включить recorded hosted privacy URL check в тот же managed run.
- `./tools/verify_release.py` возвращает `release_verification_ok`.
- `./tools/print_upload_packet.py` возвращает `upload_packet_ok`.
- `./tools/create_store_asset_review_sheet.py --dry-run` возвращает `store_asset_review_sheet_dry_run_ok`; visually review `play_store/store_asset_review_sheet.png` before upload and do not upload that sheet to Play Console.
- `./tools/prepare_play_upload_archive.py --dry-run` возвращает `play_upload_archive_dry_run_ok`; `./tools/prepare_play_upload_archive.py --verify-existing` возвращает `play_upload_archive_existing_ok`; optional `./tools/prepare_play_upload_archive.py --write` создаёт generated owner handoff ZIP under `build/play_upload`, который нужно распаковать, а не загружать целиком в Play Console.
- `./tools/print_play_console_packet.py` возвращает `play_console_packet_ok`.
- `./tools/print_publication_readiness.py` возвращает `publication_readiness_local_ready_external_pending` до закрытия внешних owner gates and groups unresolved owner actions by evidence file and required command; сверить действия с `play_store/publication_readiness_owner_actions_ru.md`. Production rollout не начинать, пока `--require-production-ready` не проходит после записи внешних evidence.
- `./tools/verify_play_generated_apk.py --dry-run` возвращает `play_generated_apk_verify_dry_run_ok`; после Play-generated artifact download запустить `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` and require `play_generated_apk_verify_ok` plus the `signer certificate SHA-256: ...`, `store icon pixel matches: ...`, `application icon linked store icon: ...`, `round icon linked store icon: ...`, `allowBackup: false` and `debuggable: absent` or `debuggable: false` lines.
- `./tools/verify_release.py` проверяет 16 KB page-size posture для native `.so` в signed AAB; post-upload APK helper проверяет тот же `PT_LOAD` alignment на Play-generated APK plus uncompressed native-library packaging, 16 KB ZIP data alignment and `extractNativeLibs=false`.
- `./tools/check_privacy_policy_url.py --local` возвращает `privacy_policy_local_ok` and prints the canonical privacy text SHA-256 for owner comparison.
- `./tools/check_signing_backup_inputs.py` возвращает `signing_backup_input_ok`.
- После push в GitHub `./tools/verify_remote_release.py --tag <release-tag>` возвращает `remote_release_ok`, подтверждая `origin/main`, annotated remote release tag, every remote upload asset checksum from `play_store/upload_checksums.md`, отсутствие extra remote `.aab` outside `app/build/outputs/bundle/release/app-release.aab`, case-insensitive отсутствие signing/install artifacts в remote tree, наличие privacy HTML на `origin/gh-pages` and recorded hosted privacy URL validity.
- Signed AAB существует: `app/build/outputs/bundle/release/app-release.aab`.
- AAB SHA-256 совпадает с `play_store/upload_checksums.md`.
- Store icon, feature graphic, phone screenshots and large/tablet screenshots совпадают с `play_store/upload_manifest.md`.
- `keystore.properties`, `local.properties`, `private/signing/*.p12`, common signing-key extensions (`*.jks`, `*.keystore`, `*.pem`, `*.pk8`, `*.key`) and APK/AAB/APKS/IDSIG files case-insensitively игнорируются `.gitignore`, проверяются через `git check-ignore` in `tools/verify_release.py`, fail release verification if tracked in Git and не добавляются в публичные материалы.

## 2. Owner Inputs До Создания Релиза

До upload владелец должен закрыть:

- Play Console support/contact fields: рабочий email или support URL.
- Public privacy policy URL: HTTPS, без логина, не PDF, без credentials/query/fragments, не placeholder/reserved host, DNS resolves only to public global IP addresses, не редактируемый читателями; hosted normalized text must match `play_store/privacy_policy_ru.html`.
- Signing backup: `private/signing/qgrid-upload.p12` and `keystore.properties` сохранены в secure owner-controlled storage after `./tools/check_signing_backup_inputs.py` returned `signing_backup_input_ok`.
- Testing path: internal testing first; closed testing with 12 opted-in testers for 14 continuous days if required by account type, then Play Console production access granted/approved if that path applies.
- Final generated-artifact review owner: человек, который проверит Play-generated APKs, policy warnings and pre-launch report.

Источник owner gates: `play_store/owner_release_inputs.md`. Safe signing-backup evidence template: `play_store/signing_backup_evidence_ru.md`.

Owner-action breakdown for upload day: `play_store/publication_readiness_owner_actions_ru.md`.

Production-access answer worksheet: `play_store/production_access_answers_ru.md`.

## 3. Create App / Identity

В Play Console создать app:

- App name: `Линия 56`.
- Default language: Russian (`ru-RU`).
- App or game: Game.
- Category: Puzzle.
- Free app.
- No ads.

Нельзя менять без rebuild/recheck:

- Package name: `com.qgrid.mobile`.
- Version code: `1`.
- Version name: `1.0.0`.
- Privacy/data-safety posture.
- Target audience posture.
- Store icon, feature graphic or screenshots.

## 4. App Content And Policy Forms

Заполнять из этих источников:

- App content field-by-field answers: `play_store/app_content_answers_ru.md`.
- Data Safety: `play_store/data_safety_ru.md`.
- Content Rating: `play_store/content_rating_notes.md`.
- Privacy policy HTML source: `play_store/privacy_policy_ru.html`.
- Privacy hosting checklist: `play_store/privacy_policy_hosting_checklist.md`.
- Before entering the URL in Play Console, run `./tools/check_privacy_policy_url.py --url <https-url>` and require `privacy_policy_url_ok`; the hosted page must be public HTTPS, no credentials/query/fragments, not a placeholder/reserved host, DNS-resolved only to public global IP addresses, non-PDF, valid UTF-8, free of script/tracker/widget markers and text-identical to the current local policy HTML after whitespace normalization.

Ключевые ответы:

- No restricted access, no login, no accounts.
- No ads, analytics, crash reporting, payments, device identifiers or user-generated content.
- No user data collected.
- No user data shared.
- No `INTERNET` or `ACCESS_NETWORK_STATE` permission in the app.
- Android backup disabled.
- Games / Puzzle content rating posture: no violence, fear, sexual content, language, drugs, gambling, purchases, UGC, online interaction or location sharing.
- Non-child-directed target audience recommendation: select `13-15`, `16-17`, and `18 and over` unless the publisher intentionally prepares a child-directed Families release path.

## 5. Store Listing Upload

Copy-ready text source:

- `play_store/play_console_submission_ru.md`.
- Command packet: run `./tools/print_play_console_packet.py` and require `play_console_packet_ok`.
- If production access is required, prepare answers from `play_store/production_access_answers_ru.md` using only aggregate closed-test facts and no tester personal data.

Upload only these assets:

- App bundle: `app/build/outputs/bundle/release/app-release.aab`.
- Store icon: `play_store/icon/play_icon_512.png`.
- Feature graphic: `play_store/feature_graphic.png`.
- Phone screenshots:
  - `play_store/screenshots/phone/01_onboarding.png`
  - `play_store/screenshots/phone/02_home.png`
  - `play_store/screenshots/phone/03_game_start.png`
  - `play_store/screenshots/phone/04_game_line.png`
  - `play_store/screenshots/phone/05_settings.png`
- Large/tablet screenshots:
  - `play_store/screenshots/tablet/01_onboarding.png`
  - `play_store/screenshots/tablet/02_home.png`
  - `play_store/screenshots/tablet/03_game_start.png`
  - `play_store/screenshots/tablet/04_game_line.png`
  - `play_store/screenshots/tablet/05_settings.png`

Use alt text from `play_store/asset_alt_text_ru.md` where Play Console asks for preview asset descriptions.

## 6. Do Not Upload

Do not upload these files to Play Console:

- `play_store/archive/feature_graphic_concept.png`.
- `play_store/source_assets/feature_background_imagegen.png`.
- `play_store/source_assets/icon_imagegen_20260606.png`.
- `play_store/archive/icon_imagegen_20260605_rejected.png`.
- `play_store/archive/icon_imagegen_20260606_rejected_owner_review.png`.
- `play_store/icon/play_icon_preview_masked.png`.
- `docs/qa_artifacts`.
- Any APK under `app/build/outputs/apk`.
- `app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk`.
- `keystore.properties`.
- `local.properties`.
- `private/signing/qgrid-upload.p12`.
- `private/signing/line56-upload.p12`.
- `play_store/signing_certificate_report.md`.

The only binary upload artifact for Google Play is the signed AAB.

## 7. Release Track Order

Recommended order:

1. Upload the signed AAB to internal testing.
2. Inspect Play-generated APKs for package, app name, version, APK signature, signer certificate SHA-256, store-icon pixel match, application/round icon linkage, permissions, `allowBackup=false`, no debuggable release manifest and native 16 KB page-size posture.
3. Run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` on a downloaded Play-generated APK artifact and require `play_generated_apk_verify_ok`.
4. Install generated APKs on at least one Android device or emulator.
5. Repeat first-launch, home, game, win, settings, restart and no-internet smoke flows.
6. Review Play pre-launch report and policy warnings.
7. Run closed testing if required by the publisher account type.
8. Apply for and receive Play Console production access if closed testing is required for the publisher account; use `play_store/production_access_answers_ru.md` to prepare safe answers.
9. Promote to production only after owner gates, testing tracks, production-access status and review warnings are complete.

## 8. Stop Conditions

Stop and return to local rebuild/recheck if any of these happen:

- Play Console package is not `com.qgrid.mobile`.
- Version code or version name differs from this runbook.
- Play shows privacy, data-safety, permissions, target-audience or content-rating warnings that contradict local docs.
- Play-generated APK has a wrong icon, label, package, invalid signature, Android Debug certificate, backup/debug manifest posture or debuggable release manifest.
- Pre-launch report shows a reproducible app crash.
- Store screenshots or feature graphic are rejected or visually cropped in a damaging way.
- Any owner wants to change package id, version, privacy posture, target audience, store copy claims, icon, feature graphic or screenshots.

After any local rebuild, rerun the full preflight and compare `play_store/upload_checksums.md` again before uploading.

## 9. Evidence To Record After Upload

After Play Console upload, record these owner-side facts in the release notes or owner tracker:

- Uploaded AAB version code and version name.
- Play Console track used first.
- Public privacy policy URL.
- Privacy policy URL check result from `./tools/check_privacy_policy_url.py --url <https-url>`.
- Signing backup input check result from `./tools/check_signing_backup_inputs.py`.
- Signing backup evidence recorded in `play_store/signing_backup_evidence_ru.md`.
- Support/contact field used for privacy inquiries.
- Whether closed testing is required for the account.
- Production access status if required for the account.
- Pre-launch report result.
- Any Play warnings and their resolution.

Use `play_store/play_console_post_upload_evidence_ru.md` as the safe evidence template. This evidence is external to the repository until the owner chooses to copy a safe summary back into `docs/release_report.md`.
