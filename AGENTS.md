# AGENTS.md

## Project

«Линия 56» is an offline-first Android numeric puzzle. The player connects neighboring numbered cells until the selected path sums exactly to 56.

## Stack

- Kotlin + Jetpack Compose + Material 3.
- Android Gradle Plugin 8.11.1.
- Gradle wrapper 8.14.5.
- `compileSdk = 36`, `targetSdk = 36`, `minSdk = 24`.
- Production `applicationId = com.qgrid.mobile`.
- Debug package suffix: `.debug`.
- DataStore Preferences for local onboarding/progress/settings.
- No backend, no accounts, no ads, no analytics, no IAP, no `INTERNET` permission.

## Local Setup

Create `local.properties` on each machine:

```properties
sdk.dir=/path/to/Android/sdk
```

Release signing can use ignored `keystore.properties`:

```properties
storeFile=/absolute/path/upload-keystore.p12
storePassword=...
keyAlias=...
keyPassword=...
```

Or environment variables:

```bash
QGRID_STORE_FILE=/absolute/path/upload-keystore.p12
QGRID_STORE_PASSWORD=...
QGRID_KEY_ALIAS=...
QGRID_KEY_PASSWORD=...
```

Never commit signing files, passwords, private keys, `local.properties`, APKs, AABs or generated build outputs.

## Commands

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
./tools/verify_remote_release.py
```

Useful install commands:

```bash
./gradlew installDebug
./gradlew installRelease
```

Final local gate before handoff:

```bash
./tools/run_final_local_gate.py
```

The runner executes `./gradlew test lint assembleDebug assembleRelease bundleRelease`, `./tools/verify_release.py`, `./tools/print_upload_packet.py`, `./tools/create_store_asset_review_sheet.py --dry-run`, `./tools/prepare_play_upload_archive.py --dry-run`, `./tools/prepare_play_upload_archive.py --verify-existing`, `./tools/print_play_console_packet.py`, `./tools/print_publication_readiness.py`, `./tools/verify_play_generated_apk.py --dry-run`, `./tools/check_privacy_policy_url.py --local` and `./tools/check_signing_backup_inputs.py` in order. Add `--include-hosted-privacy` for a networked pre-upload run that replaces the publication-readiness step with `./tools/print_publication_readiness.py --check-recorded-privacy-url`.

Run `connectedDebugAndroidTest` when an emulator/device is available. For a one-command owner preflight on an available API 36 device, use `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` so connected evidence is refreshed before `./tools/verify_release.py`. To let the project start and stop its own API 36 AVD safely, use `./tools/run_api36_connected_gate.py`; add `--include-hosted-privacy` for the networked upload-day version. It targets `Medium_Phone_API_36` on `emulator-5560`, wipes that project-owned AVD data on managed start to avoid stale debug/test APK interference, and refuses to touch a different AVD on that serial.

## Directory Structure

- `app/src/main/java/com/qgrid/mobile/game`: pure Kotlin models, level generation, solver and reducer. No Android dependencies here.
- `app/src/main/java/com/qgrid/mobile/data`: DataStore progress/settings persistence.
- `app/src/main/java/com/qgrid/mobile/ui`: Compose screens, app state and ViewModel.
- `app/src/main/res`: Russian strings, themes, vector/adaptive icons.
- `app/src/test`: core unit tests.
- `app/src/androidTest`: Compose/emulator smoke tests.
- `docs`: product, technical, QA, accessibility, performance, privacy, asset and release docs.
- `play_store`: store listing, screenshots, privacy/data-safety notes, upload manifest and Play Console handoff files.
- `tools`: project-local release verifier.

## Architecture Rules

- Keep game logic deterministic and testable in pure Kotlin.
- Keep `solutionPath` for canonical level validation, but runtime hints must be current-selection aware through `LevelSolver`.
- Do not add backend, network calls, accounts, ads, analytics, crash SDKs, IAP, UGC or dangerous permissions without a new documented product decision.
- Do not introduce `INTERNET` or `ACCESS_NETWORK_STATE`; offline-first is a release invariant.
- Do not add heavy dependencies for simple UI/state tasks.
- Do not put user-visible Russian text in Kotlin code; use `app/src/main/res/values/strings.xml`.
- Do not add debug-only behavior to release. Release AAB must not contain project `.debug`, androidTest, JUnit, Espresso or Compose UI-test leakage.
- Preserve neutral identifiers: no personal names in `applicationId`, namespace, signing aliases or store-facing docs.

## UI/UX Rules

- Mobile-first, clear hierarchy, readable numbers and tap targets at least 48dp.
- Use restrained, workmanlike puzzle UI: no decorative noise, fake 3D, mascots or random illustrations.
- Cards are allowed for actual panels/tiles, not nested decoration.
- Use icons for familiar actions where available.
- Keep action labels short enough for small screens.
- Important states must not rely only on color; text/status/semantics must also explain them.
- Support small, tall and landscape layouts without clipped controls.
- Keep high contrast and reduced motion settings functional.

## Asset Rules

- Store icon, adaptive icon, feature graphic and screenshots must remain consistent with the connected-path visual identity.
- Do not upload rejected/source assets to Play Console.
- Keep generated/source-only assets documented in `docs/asset_manifest.md` and `play_store/upload_manifest.md`.
- Do not copy competitor UI, brands, characters, copyrighted content or living-artist styles.
- Verify Play asset dimensions/alpha through `tools/verify_release.py`.

## Documentation Rules

Required docs must stay present and current:

- `README.md`
- `AGENTS.md`
- `docs/product_decision.md`
- `docs/product_spec.md`
- `docs/tech_stack_decision.md`
- `docs/requirements_traceability.md`
- `docs/release_plan.md`
- `docs/release_report.md`
- `docs/google_play_sources.md`
- `docs/google_play_checklist.md`
- `docs/ui_audit.md`
- `docs/qa_test_plan.md`
- `docs/performance_notes.md`
- `docs/privacy_and_permissions.md`
- `docs/art_direction.md`
- `docs/asset_manifest.md`
- `docs/asset_prompts.md`
- `docs/content_audit.md`
- `docs/accessibility_notes.md`
- `docs/completion_audit.md`
- `docs/rejected_assets.md`

`docs/story_bible.md` is not required for this project because story/campaign content is explicitly out of scope for v1.

Release-facing Play files must stay present:

- `play_store/listing_ru.md`
- `play_store/data_safety_ru.md`
- `play_store/content_rating_notes.md`
- `play_store/app_content_answers_ru.md`
- `play_store/privacy_policy_ru.md`
- `play_store/privacy_policy_ru.html`
- `play_store/privacy_policy_hosting_checklist.md`
- `play_store/upload_manifest.md`
- `play_store/upload_runbook_ru.md`
- `play_store/play_console_post_upload_evidence_ru.md`
- `play_store/signing_backup_evidence_ru.md`
- `play_store/upload_checksums.md`
- `play_store/play_console_submission_ru.md`
- `play_store/owner_release_inputs.md`
- `play_store/publication_readiness_owner_actions_ru.md`
- `play_store/signing_certificate_report.md`
- `play_store/asset_alt_text_ru.md`
- `play_store/screenshots/manifest.md`

## Release Verifier

`./tools/verify_release.py` is the project-local release gate. It checks build config, signing-file hygiene, no committed API keys/tokens/private-key blocks/dev URLs, backup/privacy manifest state, APK permissions, AAB signature, AAB native `.so` 16 KB page-size alignment, AAB debug/test cleanliness, artifact/asset size budgets, store assets, upload manifest paths, upload checksums, alt text, privacy HTML, signing report, listing length, forbidden identifiers, Russian Kotlin literals and required documentation.

`./tools/run_final_local_gate.py` is the owner-facing final local gate runner. It runs the local build/test/release verifier and read-only handoff helpers in the required order, supports optional `--include-hosted-privacy` recorded hosted privacy URL validation, supports optional `--include-connected --connected-serial <serial>` connected evidence refresh, cleans generated connected-test outputs, force-stops/kills the current production package `com.qgrid.mobile` plus known stale local package processes, uninstalls known stale local debug/test packages on the selected serial, including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`, before that optional connected run, and prints `final_local_gate_ok` only after every command succeeds.

`./tools/run_api36_connected_gate.py` is the managed API 36 connected gate helper. It boots a clean `Medium_Phone_API_36` on `emulator-5560` with `-wipe-data`, retries the cleaned AVD once without `-wipe-data` if the emulator exits after the wipe reset before boot, runs `./tools/run_final_local_gate.py --include-connected --connected-serial emulator-5560`, can pass through `--include-hosted-privacy` for the networked upload-day preflight, then stops only the emulator it started. If that serial is already occupied by another AVD, it fails instead of stopping or reusing it. Use `--preserve-avd-data` only for diagnostics where stale installed packages are intentionally being preserved.

`./tools/print_upload_packet.py` is the read-only owner helper for upload day. It verifies `play_store/upload_checksums.md` against the current AAB/assets, requires the exact ordered upload path set and prints the Google Play upload packet plus the Do Not Upload list.

`./tools/create_store_asset_review_sheet.py` is the local visual asset review helper. In `--dry-run` mode it validates icon, feature graphic and phone/tablet screenshot dimensions; in `--write` mode it creates `play_store/store_asset_review_sheet.png` for owner crop review. The sheet is internal evidence only and must not be uploaded to Play Console.

`./tools/prepare_play_upload_archive.py` is the generated owner handoff archive helper. In `--dry-run` mode it verifies the archive contents without writing; in `--write` mode it creates `build/play_upload/line56_v1_google_play_upload_packet.zip` with only the verified AAB/assets plus safe handoff notes. The ZIP is not a Play Console upload artifact; unpack it and upload the individual files.

In `--verify-existing` mode it verifies the generated ZIP exactly matches current upload assets and handoff notes.

`./tools/print_play_console_packet.py` is the read-only owner helper for Play Console forms. It verifies listing/App content handoff consistency and prints the copy-ready store listing, policy posture and manual owner gates.

`./tools/print_publication_readiness.py` is the read-only owner helper for publication status. It prints the difference between a locally verifier-approved release candidate and a production-ready Google Play release, can validate the recorded hosted privacy policy URL with `--check-recorded-privacy-url`, lists unresolved owner-controlled gates, groups unresolved owner actions by evidence file and required command, and returns `publication_readiness_local_ready_external_pending` until external evidence is recorded.

`./tools/verify_play_generated_apk.py` is the owner helper for Play-generated APK review after upload. In `--dry-run` mode it prints expected package/version/permission posture; with `--apk <path>` it verifies the APK package, version, label, SDK levels, no forbidden permissions, no debug/test leakage, a 512x512 icon candidate whose pixels match `play_store/icon/play_icon_512.png`, an application icon reference linked to that matching PNG and a round icon reference linked to that same PNG.

`./tools/check_privacy_policy_url.py --local` validates the local ready-to-host privacy HTML. After the owner hosts it publicly, run `./tools/check_privacy_policy_url.py --url <https-url>` before entering the URL in Play Console.

`./tools/check_signing_backup_inputs.py` validates the ignored local signing inputs before backup without printing password values. Use `play_store/signing_backup_evidence_ru.md` to record only safe owner-side backup evidence.

`./tools/verify_remote_release.py` is the networked post-push GitHub release helper. It fetches `origin/main` and `origin/gh-pages`, requires the remote release branch to match local `HEAD`, can verify an explicit `--tag <release-tag>` is an annotated tag and peels to local `HEAD`, verifies the remote signed AAB bytes/SHA-256 from `play_store/upload_checksums.md`, rejects any extra remote `.aab` files outside `app/build/outputs/bundle/release/app-release.aab`, scans remote trees case-insensitively for signing/install artifacts including `.p12`, `.jks`, `.keystore`, `.pem`, `.pk8`, `.key`, APK/APKS/IDSIG and private directories, and validates the recorded hosted privacy policy URL.

When changing release-facing behavior, update the verifier if the new invariant can be checked locally.

## Done Criteria

The project is locally ready when:

- Core loop works and all 36 levels are independently solver-verified.
- UI looks like a finished mobile product, not a prototype.
- No placeholder user-facing content remains.
- Store assets are present and verifier-approved.
- `./tools/run_final_local_gate.py` passes and prints `final_local_gate_ok`; this covers `./gradlew test`, `./gradlew lint`, `./gradlew assembleDebug`, `./gradlew assembleRelease`, `./gradlew bundleRelease`, `./tools/verify_release.py`, `./tools/print_upload_packet.py`, `./tools/create_store_asset_review_sheet.py --dry-run`, `./tools/prepare_play_upload_archive.py --dry-run`, `./tools/prepare_play_upload_archive.py --verify-existing`, `./tools/print_play_console_packet.py`, `./tools/print_publication_readiness.py`, `./tools/verify_play_generated_apk.py --dry-run`, `./tools/check_privacy_policy_url.py --local` and `./tools/check_signing_backup_inputs.py`.
- `./gradlew connectedDebugAndroidTest` passes on an available emulator/device, preferably through `./tools/run_api36_connected_gate.py` or `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` on an API 36 device, or an exact environment reason is documented.
- Google Play checklist, release report and upload handoff are current.

The full publication goal is not complete until manual external gates are done: populated Play Console support/contact fields for privacy inquiries, public HTTPS privacy-policy URL, secure keystore backup, Play Console forms and required testing tracks.
