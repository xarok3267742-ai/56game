# Google Play Upload Manifest

## Upload To Play Console

- App bundle: `app/build/outputs/bundle/release/app-release.aab`
  - Release package: com.qgrid.mobile
  - Version code: 1
  - Version name: 1.0.0
- Store icon: `play_store/icon/play_icon_512.png`
- Feature graphic: `play_store/feature_graphic.png`
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
- Listing copy: `play_store/listing_ru.md`
- Data Safety notes: `play_store/data_safety_ru.md`
- Content rating notes: `play_store/content_rating_notes.md`
- Play Console submission fields: `play_store/play_console_submission_ru.md`
- App content answers: `play_store/app_content_answers_ru.md`
- Closed testing handoff: `play_store/closed_testing_handoff_ru.md`
- Production access answers: `play_store/production_access_answers_ru.md`
- Privacy/contact handoff: `play_store/privacy_contact_handoff_ru.md`
- Owner release inputs: `play_store/owner_release_inputs.md`
- Publication readiness owner actions: `play_store/publication_readiness_owner_actions_ru.md`
- Upload runbook: `play_store/upload_runbook_ru.md`
- Post-upload evidence template: `play_store/play_console_post_upload_evidence_ru.md`
- Signing backup evidence and owner template: `play_store/signing_backup_evidence_ru.md`
- Preview asset alt text: `play_store/asset_alt_text_ru.md`
- Upload checksums: `play_store/upload_checksums.md`
- Final local gate runner: `tools/run_final_local_gate.py`
- Managed API 36 connected gate helper: `tools/run_api36_connected_gate.py`
- Upload packet helper: `tools/print_upload_packet.py`
- Post-upload evidence packet helper: `tools/print_post_upload_evidence_packet.py`
- Closed-testing evidence packet helper: `tools/print_closed_testing_evidence_packet.py`
- Privacy/contact evidence packet helper: `tools/print_privacy_contact_evidence_packet.py`
- Play Console forms evidence packet helper: `tools/print_play_console_forms_evidence_packet.py`
- Play pre-launch review evidence packet helper: `tools/print_pre_launch_review_evidence_packet.py`
- Store listing review evidence packet helper: `tools/print_store_listing_review_evidence_packet.py`
- Store asset review sheet helper: `tools/create_store_asset_review_sheet.py`
- Play upload archive helper: `tools/prepare_play_upload_archive.py`
  - Verify existing generated ZIP: run the helper with --verify-existing
- Play Console packet helper: `tools/print_play_console_packet.py`
- Publication readiness helper: `tools/print_publication_readiness.py`
- Play-generated APK verification helper: `tools/verify_play_generated_apk.py`
- Signing backup evidence packet helper: `tools/print_signing_backup_evidence_packet.py`
- Privacy policy URL: host `play_store/privacy_policy_ru.html` after filling the Play Console support/contact fields used by the policy inquiry mechanism.

## Release Handoff References

- Signing certificate report: `play_store/signing_certificate_report.md`
- Upload checksum manifest: `play_store/upload_checksums.md`
- Owner-controlled manual inputs: `play_store/owner_release_inputs.md`
- Closed testing handoff: `play_store/closed_testing_handoff_ru.md`
- Production access answers: `play_store/production_access_answers_ru.md`
- Privacy/contact handoff: `play_store/privacy_contact_handoff_ru.md`
- Publication readiness owner actions: `play_store/publication_readiness_owner_actions_ru.md`
- Upload runbook: `play_store/upload_runbook_ru.md`
- Post-upload evidence template: `play_store/play_console_post_upload_evidence_ru.md`
- Signing backup evidence and owner template: `play_store/signing_backup_evidence_ru.md`
- Final local gate runner: `tools/run_final_local_gate.py`
- Managed API 36 connected gate helper: `tools/run_api36_connected_gate.py`
- Post-upload evidence packet helper: `tools/print_post_upload_evidence_packet.py`
- Closed-testing evidence packet helper: `tools/print_closed_testing_evidence_packet.py`
- Privacy/contact evidence packet helper: `tools/print_privacy_contact_evidence_packet.py`
- Play Console forms evidence packet helper: `tools/print_play_console_forms_evidence_packet.py`
- Play pre-launch review evidence packet helper: `tools/print_pre_launch_review_evidence_packet.py`
- Store listing review evidence packet helper: `tools/print_store_listing_review_evidence_packet.py`
- Store asset review sheet: `play_store/store_asset_review_sheet.png`
- Store asset review sheet helper: `tools/create_store_asset_review_sheet.py`
- Play upload archive helper: `tools/prepare_play_upload_archive.py`
  - Existing archive verification: run the helper with --verify-existing
- Play Console packet helper: `tools/print_play_console_packet.py`
- Publication readiness helper: `tools/print_publication_readiness.py`
- Play-generated APK verification helper: `tools/verify_play_generated_apk.py`
- Signing backup evidence packet helper: `tools/print_signing_backup_evidence_packet.py`

## Do Not Upload

- `play_store/archive/feature_graphic_concept.png` - rejected asset, kept only for traceability.
- `play_store/source_assets/feature_background_imagegen.png` - source/background only.
- `play_store/source_assets/icon_imagegen_20260606.png` - source icon only; upload the cleaned `play_store/icon/play_icon_512.png` instead.
- `play_store/archive/icon_imagegen_20260605_rejected.png` - rejected previous icon, kept only for traceability.
- `play_store/archive/icon_imagegen_20260606_rejected_owner_review.png` - rejected owner-reviewed icon, kept only for traceability.
- `play_store/icon/play_icon_preview_masked.png` - local mask preview only; upload the full-square `play_store/icon/play_icon_512.png` because Google Play applies its own icon mask.
- `docs/qa_artifacts` - internal QA evidence only; do not upload these screenshots as Play preview assets.
- Release APK outputs under app/build/outputs/apk/release - generated install/testing artifacts only; Play upload uses the signed AAB listed above.
- `app/build/outputs/apk/debug/app-debug.apk` - debug build, not a Play upload artifact.
- `app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk` - test APK only.
- `keystore.properties` - signing secret file.
- `private/signing/qgrid-upload.p12` - upload keystore, must be backed up securely but never uploaded as a store asset.
- `private/signing/line56-upload.p12` - stale ignored local keystore from the earlier package/signing name; do not use or upload.
- `play_store/signing_certificate_report.md` - public certificate reference for handoff, not a store asset.
- `local.properties` - local SDK path only.
- `play_store/store_asset_review_sheet.png` - internal owner visual review sheet only; do not upload it to Play Console.
- `build/play_upload/line56_v1_google_play_upload_packet.zip` - generated owner handoff archive only; unpack it and upload the individual files, not the ZIP itself.

## Final Manual Gate

Before production rollout, verify generated APKs in Play Console, complete policy forms, run required testing tracks, receive Play Console production access if required and confirm the privacy policy URL is public.

If the AAB, icon, feature graphic or phone/tablet screenshots are rebuilt or recaptured, keep `play_store/upload_checksums.md` in sync and rerun `./tools/verify_release.py`. For store screenshots and feature graphic, use `tools/capture_store_screenshots.py`; it updates the checksum manifest automatically after a successful capture.
