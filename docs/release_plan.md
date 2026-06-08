# Release Plan

## Current RC Path

1. Keep code frozen except bug fixes.
2. Replace or approve release-ready launcher/store assets.
3. Back up the generated upload keystore and credentials.
4. Rebuild with the existing `keystore.properties` or equivalent env vars.
5. Re-run checks.
6. Upload AAB to internal testing.
7. Resolve `play_store/owner_release_inputs.md` and complete Play Console policy/listing forms.
8. Run closed testing if account type requires it.

Use `play_store/upload_manifest.md` as the exact Play Console upload checklist, `play_store/upload_runbook_ru.md` as the owner-facing upload-day sequence, `play_store/play_console_submission_ru.md` as the store-listing field handoff, `play_store/app_content_answers_ru.md` as the App content / policy answer sheet, `play_store/owner_release_inputs.md` as the owner-input checklist, `play_store/publication_readiness_owner_actions_ru.md` as the external owner-action breakdown, `play_store/signing_backup_evidence_ru.md` as the safe signing-backup evidence and owner template, and `play_store/play_console_post_upload_evidence_ru.md` as the safe external-evidence template after upload. Privacy policy source files are `play_store/privacy_policy_ru.md` and `play_store/privacy_policy_ru.html`; fill the Play Console support/contact fields used by the policy inquiry mechanism and host the HTML on a public HTTPS URL before entering it in Play Console.

## Signing Inputs

Current local signing files:

- Keystore: `private/signing/qgrid-upload.p12`
- Credentials: `keystore.properties`

Both are intentionally ignored by `.gitignore`. Back them up securely before any Play Console upload. Before making or refreshing the backup, run `./tools/check_signing_backup_inputs.py` and require `signing_backup_input_ok`; record only safe owner-side facts in `play_store/signing_backup_evidence_ru.md`.

Public upload-certificate metadata is documented in `play_store/signing_certificate_report.md`. Use it to compare Play Console upload-key fingerprints after enrollment. The report intentionally contains no signing secrets.

`keystore.properties` format:

```properties
storeFile=/absolute/path/upload-keystore.p12
storePassword=...
keyAlias=...
keyPassword=...
```

Env alternative:

```bash
QGRID_STORE_FILE=/absolute/path/upload-keystore.p12
QGRID_STORE_PASSWORD=...
QGRID_KEY_ALIAS=...
QGRID_KEY_PASSWORD=...
```

## Final Verification Commands

Preferred single command:

```bash
./tools/run_final_local_gate.py
```

Equivalent expanded sequence:

```bash
./gradlew clean
./gradlew test
./gradlew assembleDebug
./gradlew lint
./gradlew assembleRelease
./gradlew connectedDebugAndroidTest
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

After the owner hosts the privacy policy, run:

```bash
./tools/check_privacy_policy_url.py --url <https-url>
```

The URL check must return `privacy_policy_url_ok`; it rejects non-public/non-HTTPS URLs, URLs with credentials/query/fragments, PDF final paths, invalid UTF-8, script/tracker/widget markers and hosted text that does not match the current normalized text of `play_store/privacy_policy_ru.html`.
