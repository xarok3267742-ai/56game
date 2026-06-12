# Owner Release Inputs

This file lists the external owner-controlled inputs that must be resolved before the local release candidate can become a real Google Play submission.

## Fixed Local Decisions

- Production package: `com.qgrid.mobile`.
- Debug package: `com.qgrid.mobile.debug`.
- Upload version for this release candidate: versionCode `1`, versionName `1.0.0`.
- App name: `Линия 56`.
- Default language: Russian (`ru-RU`).
- App type/category: Game / Puzzle.
- Monetization: free, no ads, no in-app purchases.
- Data Safety posture: no user data collected, no user data shared.
- Target audience recommendation for a non-child-directed release: select `13-15`, `16-17`, and `18 and over`; do not select child age groups unless the publisher intentionally prepares a Families/child-directed release path.

## Required Owner Inputs

| Input | Required Decision | Where To Apply | Local Source |
|---|---|---|---|
| Support contact | Working owner email or support website URL; the privacy policy points users to the Google Play listing support contact as the inquiry mechanism | Play Console support/contact fields, then verify the hosted policy still matches that mechanism | `play_store/privacy_policy_ru.html`, `play_store/privacy_policy_ru.md` |
| Privacy policy URL | Public HTTPS URL, accessible without login, no credentials/query/fragments, not PDF, not editable by readers, with hosted normalized text matching `play_store/privacy_policy_ru.html` | Play Console App content > Privacy Policy | `play_store/privacy_policy_hosting_checklist.md` |
| Signing backup | Secure owner-controlled backup of `private/signing/qgrid-upload.p12` and `keystore.properties` after `./tools/check_signing_backup_inputs.py` returns `signing_backup_input_ok`; record two owner-controlled secure copies and recovery tested without exposing secrets | Owner password manager / secure storage | `play_store/signing_certificate_report.md`, `play_store/signing_backup_evidence_ru.md` |
| Play account testing path | Internal testing first; closed testing with 12 opted-in testers for 14 continuous days if required by account type, then Play Console production access granted/approved if required | Play Console testing tracks / Dashboard production access request | `play_store/app_content_answers_ru.md`, `play_store/closed_testing_handoff_ru.md`, `play_store/production_access_answers_ru.md`, `play_store/publication_readiness_owner_actions_ru.md` |
| Final generated-artifact review | Inspect Play-generated APKs, pre-launch report, package, APK signature/certificate fingerprint, icon, label, manifest privacy/debug posture, screenshots and policy warnings | Play Console release review | `docs/google_play_checklist.md` |

## Upload Execution

Use `play_store/upload_runbook_ru.md` as the owner-facing sequence for the upload day. It combines the local preflight commands, owner inputs, Play Console form sources, exact upload artifacts, Do Not Upload list, release-track order, stop conditions and post-upload evidence to record.

Before upload, use `play_store/signing_backup_evidence_ru.md` to record only safe owner-side backup facts. If closed testing is required, use `play_store/closed_testing_handoff_ru.md` for tester task coverage, aggregate feedback topics and safe evidence phrases. If production access is required, use `play_store/production_access_answers_ru.md` to prepare aggregate production-access answers without tester personal data. After upload, use `play_store/play_console_post_upload_evidence_ru.md` to record only safe external facts: uploaded package/version, public privacy URL, Play-generated artifact review, policy form status, testing-track status, production-access status, pre-launch result and policy warnings. Do not record secrets or tester personal data.

After hosting the privacy policy, run `./tools/check_privacy_policy_url.py --url <https-url>` and require `privacy_policy_url_ok` before entering the URL in Play Console. The helper rejects non-public/non-HTTPS URLs, PDF responses, invalid UTF-8, script/tracker/widget markers and hosted text that does not match the current local HTML policy text.

## Do Not Change Without Rebuilding And Rechecking

- `applicationId` / package name.
- Version code or version name.
- Store icon, feature graphic or screenshots.
- AAB signing key, alias or keystore path.
- Privacy/data-safety posture.
- Target audience posture.
- Any store copy that changes app functionality claims.

After changing any item above, rerun:

```bash
./gradlew test lint assembleDebug assembleDebugAndroidTest bundleRelease
./tools/verify_release.py
```

Run `./gradlew connectedDebugAndroidTest` again when an emulator or device is available, especially after app UI, navigation, persistence or accessibility changes.

## Current Publication Status

The local release candidate is prepared and verifier-approved, and the privacy policy is hosted at `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`. The publication is still blocked externally until the owner enters that URL in Play Console, populates real Play Console support/contact fields, backs up signing material securely, completes Play Console forms/testing tracks and receives Play Console production access if required.
