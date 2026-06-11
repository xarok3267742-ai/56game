# Google Play Checklist

## Listing

- App name: `Линия 56`
- Short description: `Соединяйте числа и соберите сумму ровно 56.`
- Full description source: `play_store/listing_ru.md`
- Release notes source: `play_store/listing_ru.md`
- Copy-ready Play Console fields: `play_store/play_console_submission_ru.md`
- Field-by-field App content answers: `play_store/app_content_answers_ru.md`
- Owner-controlled release inputs: `play_store/owner_release_inputs.md`
- Publication readiness owner actions: `play_store/publication_readiness_owner_actions_ru.md`
- Metadata gate: `tools/verify_release.py` enforces app name <= 30 chars, short description <= 80 chars, full description <= 4000 chars, release notes <= 500 chars, no placeholder markers and exact sync between `listing_ru.md` and `play_console_submission_ru.md`.
- Default language: Russian (`ru-RU`)
- Category: Games / Puzzle
- Monetization: free, no ads, no in-app purchases

## App Setup

- `applicationId`: `com.qgrid.mobile`
- Debug package: `com.qgrid.mobile.debug`
- App label: `Линия 56`
- `versionCode`: 1
- `versionName`: 1.0.0
- `minSdk`: 24
- `compileSdk`: 36
- `targetSdk`: 36, above the current Android 15/API 35 submission requirement documented in `docs/google_play_sources.md`
- Native 16 KB page-size posture: current signed AAB has 8 packaged `.so` files and `tools/verify_release.py` verifies every ELF `PT_LOAD` alignment is at least 16,384 bytes.
- Official source audit: rechecked on 11 June 2026 in `docs/google_play_sources.md`; no local product change was required.
- Format: Android App Bundle
- Signed AAB path: `app/build/outputs/bundle/release/app-release.aab`
- Upload manifest: `play_store/upload_manifest.md`
- Upload runbook: `play_store/upload_runbook_ru.md`
- Post-upload evidence template: `play_store/play_console_post_upload_evidence_ru.md`
- Signing backup evidence and owner template: `play_store/signing_backup_evidence_ru.md`
- Upload checksums: `play_store/upload_checksums.md`

## Build And Signing

- Release signing is configured through ignored `keystore.properties` or `QGRID_*` environment variables.
- Current local upload keystore: `private/signing/qgrid-upload.p12`
- Current local credentials file: `keystore.properties`
- Local `local.properties`, `keystore.properties`, `private/signing/*.p12`, common signing-key extensions (`*.jks`, `*.keystore`, `*.pem`, `*.pk8`, `*.key`) and Android upload/install artifact extensions (`*.apk`, `*.aab`, `*.apks`, `*.idsig`) are intentionally ignored case-insensitively; `tools/verify_release.py` verifies these `.gitignore` patterns with `git check-ignore`, fails if forbidden sensitive/install paths are tracked in Git, verifies owner-only filesystem permissions for the active local signing inputs and checks that local `keystore.properties`, when present, points to `private/signing/qgrid-upload.p12` and `keyAlias=qgrid_upload`.
- Release-facing text files are scanned by `tools/verify_release.py` for common API keys/tokens/private-key blocks/dev URLs; current gate passes with no committed secret values.
- Before Play upload, run `./tools/check_signing_backup_inputs.py` and require `signing_backup_input_ok`.
- Before Play upload, back up the keystore and credentials in secure owner-controlled storage, keep at least two owner-controlled secure copies, test recovery without exposing secrets and record only safe evidence in `play_store/signing_backup_evidence_ru.md`.
- Do not upload, commit, email or place the keystore in store assets.

## Required Verification Commands

Run immediately before upload:

```bash
./tools/run_final_local_gate.py
./tools/run_final_local_gate.py --include-hosted-privacy
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

Run with an available emulator/device:

```bash
./gradlew connectedDebugAndroidTest
```

Latest local status on 6 June 2026: `test lint assembleDebug assembleRelease bundleRelease`, `tools/verify_release.py`, `connectedDebugAndroidTest` and store screenshot recapture passed after the ImageGen icon replacement. Connected run finished 6 tests on API 35 earlier, then the latest connected run finished 10/10 tests on `Medium_Phone_API_36(AVD) - 16`, including the highest-level result fallback to `К уровням`, replay from the result panel with `Повторить`, game-back return to the entry screen and hint repair feedback for a dead-end line; `tools/verify_release.py` now requires the fresh API 36 connected XML evidence. TalkBack pass also completed on API 36.

## Store Assets

- Store icon: `play_store/icon/play_icon_512.png`, 512x512 32-bit PNG with alpha, under 1024KB, full-square with no transparent pixels.
- Adaptive icon: configured in Android resources and aligned with the store icon identity.
- Monochrome icon: configured for themed launcher support.
- Feature graphic: `play_store/feature_graphic.png`, 1024x500 24-bit PNG without alpha, no promotional text, no fake UI, no badge labels.
- Phone screenshots: `play_store/screenshots/phone`, 1080x2064 24-bit PNG without alpha, cropped from real release captures to remove system bars and satisfy Play's 2:1 screenshot side-ratio rule.
- Large/tablet screenshots: `play_store/screenshots/tablet`, 1600x2336 24-bit PNG without alpha, cropped from real release captures to remove system bars and satisfy Play's screenshot side-ratio rule.
- Store asset review sheet: `play_store/store_asset_review_sheet.png`, 1800x2050 24-bit PNG without alpha, internal owner crop-review evidence only; do not upload it to Play Console.
- Preview asset alt text: `play_store/asset_alt_text_ru.md`, each entry <= 140 characters.
- Rejected/source assets must not be uploaded: see `play_store/upload_manifest.md`.

## Screenshots Checklist

- Onboarding: `play_store/screenshots/phone/01_onboarding.png`
- Home/progress: `play_store/screenshots/phone/02_home.png`
- Game start: `play_store/screenshots/phone/03_game_start.png`
- Gameplay line: `play_store/screenshots/phone/04_game_line.png`
- Settings: `play_store/screenshots/phone/05_settings.png`
- Large/tablet onboarding: `play_store/screenshots/tablet/01_onboarding.png`
- Large/tablet home/progress: `play_store/screenshots/tablet/02_home.png`
- Large/tablet game start: `play_store/screenshots/tablet/03_game_start.png`
- Large/tablet gameplay line: `play_store/screenshots/tablet/04_game_line.png`
- Large/tablet settings: `play_store/screenshots/tablet/05_settings.png`
- Recapture screenshots if any visible UI changes before upload.

## Privacy Policy

- Source markdown: `play_store/privacy_policy_ru.md`
- Ready-to-host HTML: `play_store/privacy_policy_ru.html`
- Hosting checklist: `play_store/privacy_policy_hosting_checklist.md`
- Manual gate: populate the Play Console support/contact fields because the policy uses the Google Play listing support contact as its privacy inquiry mechanism.
- Hosted public HTTPS URL: `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.
- Manual gate: enter the hosted URL in Play Console and keep the Play Console support/contact fields populated with a real support contact.
- Current status: policy source text is hosted and verified, but publication is not complete until Play Console support/contact fields and the Play Console privacy-policy field are populated.

## Data Safety Notes

- Data collection: none.
- Data sharing: none.
- Analytics: none.
- Crash reporting: none.
- Local data: onboarding flag, completed levels, last level, haptics/high-contrast/reduce-motion settings.
- Android backup: disabled via `android:allowBackup="false"`.
- No analytics, ads, payments, accounts, crash reporting SDK, device identifiers or UGC.
- Form notes source: `play_store/data_safety_ru.md`
- Field-by-field App content source: `play_store/app_content_answers_ru.md`
- Handoff gate: `tools/verify_release.py` checks privacy/data-safety/content-rating statements across `docs/privacy_and_permissions.md`, `play_store/data_safety_ru.md`, `play_store/content_rating_notes.md` and `play_store/play_console_submission_ru.md`.

## Permissions Explanation

- No dangerous/platform runtime permissions are requested.
- No location, camera, microphone, contacts or storage permissions.
- No `INTERNET` or `ACCESS_NETWORK_STATE` permission.
- APK contains only the AndroidX-generated app-private dynamic receiver permission; it does not grant access to user data.
- `tools/verify_release.py` enforces this against source manifest, merged debug/release manifests and debug APK permissions.

## Content Rating Notes

- Expected category: Games / Puzzle.
- Violence: none.
- Fear/shock: none.
- Sexual content: none.
- Language: none.
- Drugs/alcohol/tobacco: none.
- Gambling/simulated gambling: none.
- Real-money purchases: none.
- User-generated content: none.
- Online interaction: none.
- Notes source: `play_store/content_rating_notes.md`
- Field-by-field App content source: `play_store/app_content_answers_ru.md`

## Target Audience Notes

- General casual puzzle audience.
- Store copy and screenshots are neutral and do not target children specifically.
- Recommended non-child-directed answer is documented in `play_store/app_content_answers_ru.md`: select 13-15, 16-17 and 18 and over; do not select 5 and under, 6-8 or 9-12 unless the publisher intentionally prepares a child-directed release path.
- Do not enter Google Play Families unless the publisher intentionally prepares for that policy path.

## Testing Instructions

- Upload the signed AAB to internal testing first.
- Inspect Play-generated APKs for package name, version, icon, label and generated size.
- Install generated APKs on at least one small/medium Android device or emulator.
- Re-run the first-launch, home, level selection, gameplay, win, settings, restart and no-internet smoke flows.
- For applicable personal developer accounts, run the required closed testing track before production.
- Review the completed TalkBack exploratory evidence in `docs/accessibility_notes.md`; repeat on a physical device after Play-generated APK install if the publisher wants an audio/speech-quality check.

## Known Limitations

- Privacy policy is not publication-complete until real Play Console support/contact fields and a public HTTPS URL are set.
- Play Console forms are not completed locally because account access is external.
- Closed testing cannot be completed locally because it depends on account type and testers.
- Owner release inputs are isolated in `play_store/owner_release_inputs.md`.
- TalkBack exploratory QA is complete on `Medium_Phone_API_36` Play Store AVD with Android Accessibility Suite; headless AVD audio/speech quality was not judged by ear.
- Dedicated large/tablet screenshots are captured in `play_store/screenshots/tablet`; Play Console generated APK review still remains manual after upload.

## Manual Play Console Actions

- Create app in Play Console.
- Confirm package name: `com.qgrid.mobile`.
- Confirm version code `1` and version name `1.0.0` in the uploaded artifact.
- Resolve owner inputs from `play_store/owner_release_inputs.md`.
- Enter listing copy from `play_store/play_console_submission_ru.md`.
- Upload AAB from `app/build/outputs/bundle/release/app-release.aab`.
- Do not upload generated release APK outputs from app/build/outputs/apk/release; the Play upload artifact for this project is the signed AAB.
- Upload store icon, feature graphic and phone/large-tablet screenshots from `play_store/upload_manifest.md`.
- Compare AAB and asset bytes/SHA-256 against `play_store/upload_checksums.md` after the final local build.
- Run `./tools/run_final_local_gate.py` and require `final_local_gate_ok` before starting the Play Console upload.
- When network is available before upload, run `./tools/run_final_local_gate.py --include-hosted-privacy` and require `final_local_gate_ok`; this keeps the default local gate offline-safe while revalidating the recorded hosted privacy policy URL for upload day.
- When an API 36 emulator/device is available, prefer `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` so connected evidence is refreshed before the verifier; this optional connected path also cleans generated connected outputs, force-stops/kills the current production package `com.qgrid.mobile` plus known stale local package processes, and uninstalls known stale local debug/test packages on the selected serial, including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`, before instrumentation starts.
- To have the project manage the API 36 emulator itself, run `./tools/run_api36_connected_gate.py` and require `api36_connected_gate_ok`; add `--include-hosted-privacy` when network is available before upload. It targets `Medium_Phone_API_36` on `emulator-5560`, starts it with `-wipe-data` so stale debug/test APKs from older local projects cannot steal focus, retries the cleaned AVD once without `-wipe-data` if the emulator exits after the wipe reset before boot, and refuses to touch a different AVD on that serial.
- Run `./tools/print_upload_packet.py` and require `upload_packet_ok` before uploading assets.
- Run `./tools/create_store_asset_review_sheet.py --dry-run` and review `play_store/store_asset_review_sheet.png` before upload to catch damaging crop or wrong-asset regressions locally.
- Optionally run `./tools/prepare_play_upload_archive.py --write` to create `build/play_upload/line56_v1_google_play_upload_packet.zip`, then run `./tools/prepare_play_upload_archive.py --verify-existing`; unpack the ZIP for upload day and do not upload it itself to Play Console.
- Run `./tools/print_play_console_packet.py` and require `play_console_packet_ok` before filling Play Console listing/App content forms.
- Run `./tools/print_publication_readiness.py` and require `publication_readiness_local_ready_external_pending` before upload; require `./tools/print_publication_readiness.py --require-production-ready` only after owner-controlled external evidence is recorded.
- Use `play_store/publication_readiness_owner_actions_ru.md` to resolve the external owner-action groups before production rollout.
- After Play Console creates downloadable APK artifacts from the uploaded AAB, run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` and require `play_generated_apk_verify_ok`.
- Run `./tools/check_signing_backup_inputs.py` and require `signing_backup_input_ok` before backing up signing files and uploading the AAB.
- After pushing the release handoff to GitHub, run `./tools/verify_remote_release.py --tag <release-tag>` and require `remote_release_ok`; it verifies `origin/main`, the annotated remote release tag, the remote signed AAB checksum, rejects extra remote `.aab` files outside `app/build/outputs/bundle/release/app-release.aab`, checks remote forbidden-path hygiene, verifies `origin/gh-pages` privacy-policy presence and validates the recorded hosted privacy URL.
- Record safe signing-backup evidence in `play_store/signing_backup_evidence_ru.md`.
- Add public privacy policy URL `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.
- Before entering the URL, run `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` and require `privacy_policy_url_ok`; the hosted policy must be public HTTPS, no credentials/query/fragments, non-PDF, valid UTF-8, free of script/tracker/widget markers and text-identical to the current local `play_store/privacy_policy_ru.html` after whitespace normalization.
- Complete Data Safety using `play_store/data_safety_ru.md`.
- Complete content rating using `play_store/content_rating_notes.md`.
- Complete target audience and app content declarations using `play_store/app_content_answers_ru.md`.
- Run internal/closed testing as required.
- Review generated APKs and pre-launch report.
- Record safe post-upload evidence in `play_store/play_console_post_upload_evidence_ru.md`.
- Promote to production only after manual gates are complete.

## Release Build Status

Signed release AAB exists and verifies locally. Store icon, feature graphic, phone screenshots, large/tablet screenshots, listing copy, data-safety notes, content-rating notes, hosted privacy-policy HTML, upload manifest, Play Console field handoff, signing-backup evidence and owner template, and release report are present. Publication is still gated by entering the privacy URL in Play Console, populated Play Console support/contact fields, signing-key backup and Play Console actions.
