# Publication Readiness Owner Actions - RU

Этот файл фиксирует внешние owner-controlled действия, которые нельзя доказать локальным репозиторием. Он нужен для upload day и должен оставаться синхронизированным с выводом:

```bash
./tools/print_publication_readiness.py
./tools/print_publication_readiness.py --check-recorded-privacy-url
```

Текущий локальный статус: `publication_readiness_local_ready_external_pending`.

Production rollout нельзя начинать, пока после записи безопасных внешних evidence не проходит:

```bash
./tools/print_publication_readiness.py --check-recorded-privacy-url --require-production-ready
```

Не записывать в этот файл, `play_store/play_console_post_upload_evidence_ru.md` или `play_store/signing_backup_evidence_ru.md` пароли, private keys, keystore contents, Play account tokens, закрытые ссылки с доступом, recovery codes или персональные данные тестеров.

## 1. Upload Artifact Identity

Action: upload the signed AAB through a testing track first and record exact artifact facts.

Evidence file: `play_store/play_console_post_upload_evidence_ru.md`.

Command:

```bash
./tools/print_upload_packet.py
```

Fields to resolve:

- Uploaded package name.
- Uploaded version code.
- Uploaded version name.
- Uploaded AAB SHA-256.
- First release track used.
- Upload date/time.

Required posture:

- Package must be `com.qgrid.mobile`.
- versionCode must be `1`.
- versionName must be `1.0.0`.
- AAB SHA-256 must match `play_store/upload_checksums.md`.
- First track must be internal testing; record closed testing separately if the publisher account requires it.

## 2. Privacy Policy And Play Contact

Action: validate the hosted privacy policy URL, enter it in Play Console and populate Play Console support/contact fields.

Evidence file: `play_store/play_console_post_upload_evidence_ru.md`.

Commands:

```bash
./tools/check_privacy_policy_url.py --local
./tools/check_privacy_policy_url.py --url <https-url>
```

Fields to resolve:

- Public privacy policy URL.
- Privacy policy URL check command returned `privacy_policy_url_ok`.
- Privacy policy URL is HTTPS.
- Privacy policy URL is accessible without login.
- Privacy policy URL is not PDF.
- Play Console support/contact field populated.
- Support/contact mechanism matches `play_store/privacy_policy_ru.html`.

Required posture:

- URL must be public HTTPS, without credentials, query parameters or fragments.
- Hosted text must match `play_store/privacy_policy_ru.html`.
- The policy inquiry mechanism must use the populated Google Play listing support/contact field.
- Evidence must not use bare `yes`; it must explicitly say the Play Console support/contact field is populated and that the privacy policy uses the Google Play listing support contact.

## 3. Signing Backup

Action: back up the active upload keystore and credentials before Play upload, then record safe owner evidence.

Evidence files:

- `play_store/signing_backup_evidence_ru.md`.
- `play_store/play_console_post_upload_evidence_ru.md`.

Command:

```bash
./tools/check_signing_backup_inputs.py
```

Required posture:

- `./tools/check_signing_backup_inputs.py` must return `signing_backup_input_ok`.
- Active-keystore backup evidence must explicitly mention `private/signing/qgrid-upload.p12` and `before AAB upload`.

Fields to resolve:

- Active upload keystore backed up before AAB upload.
- Owner-controlled backup evidence recorded without secrets.
- Backup completed before Play upload.
- Secure owner-controlled storage type chosen.
- At least two owner-controlled secure copies exist.
- Recovery tested without exposing secrets.
- Responsible owner.
- Backup date/time.
- Backup record location in owner tracker or password manager.

Required posture:

- Active keystore is `private/signing/qgrid-upload.p12`.
- Credentials file is `keystore.properties`.
- Active key alias is `qgrid_upload`.
- `./tools/check_signing_backup_inputs.py` must return `signing_backup_input_ok`.
- Evidence must explicitly say backup evidence was recorded without secrets, two owner-controlled secure copies exist and recovery was tested without exposing secrets.

## 4. Play-Generated Artifact Review

Action: download or inspect Play-generated artifacts and prove package, signature, label, version, icon, permission, manifest privacy and native 16 KB page-size posture.

Evidence file: `play_store/play_console_post_upload_evidence_ru.md`.

Commands:

```bash
./tools/verify_play_generated_apk.py --dry-run
./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>
```

Fields to resolve:

- Play-generated APK package is `com.qgrid.mobile`.
- Play-generated APK signature verifies and certificate SHA-256 recorded.
- Play-generated app label is `Линия 56`.
- Play-generated icon matches `play_store/icon/play_icon_512.png`.
- Play-generated version code/name match this release candidate.
- Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions.
- Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest.
- Play-generated native libraries support 16 KB page sizes.
- Play-generated APK installed and launched on at least one Android device or emulator.

Required posture:

- Generated artifacts must not contain debug package ids, Android Debug signing certificates, missing/invalid APK signatures, androidTest/JUnit/Espresso/test leakage, forbidden permissions, `allowBackup=true`, `debuggable=true`, `extractNativeLibs=true`, compressed native libraries, native ZIP data offsets below 16 KB alignment, icon pixels that differ from `play_store/icon/play_icon_512.png`, application/round icon references that are not linked to that matching PNG, or native `.so` files below 16 KB ELF `PT_LOAD` alignment.
- Version evidence must explicitly mention `versionCode 1` and `versionName 1.0.0`.
- Install/launch evidence must explicitly say the downloaded Play-generated APK was installed and launched on an Android device or Android emulator.
- Stop rollout if package, label, version, icon, permissions, manifest privacy or native 16 KB page-size posture differ from the local release candidate.

## 5. Play Console Forms

Action: complete App content, ads, Data Safety, content rating, target audience and AI disclosure forms.

Evidence file: `play_store/play_console_post_upload_evidence_ru.md`.

Command: no local command; complete the matching Play Console forms.

Sources:

- `play_store/app_content_answers_ru.md`.
- `play_store/data_safety_ru.md`.
- `play_store/content_rating_notes.md`.
- `play_store/play_console_submission_ru.md`.
- `play_store/owner_release_inputs.md`.

Fields to resolve:

- App access completed as no restricted access/login/account.
- Ads declaration completed as no ads.
- Data Safety completed as no user data collected or shared.
- Content rating completed as Games / Puzzle posture.
- Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path.
- AI disclosure completed as no in-app generative AI features.

Required posture:

- No accounts, ads, analytics, crash SDK, billing, UGC, online interaction, gambling, medical/financial/government claims or data collection.
- Target audience should stay 13+ and non-child-directed unless a new documented product decision changes the release path.
- Evidence must not use bare `yes`; it must explicitly mention no restricted access/login/account, no ads, no user data collected/shared, Games / Puzzle content rating, 13+ non-child-directed target audience and no in-app generative AI features.

## 6. Testing Track And Final Review

Action: finish required testing, review Play warnings/pre-launch results and inspect store preview crops.

Evidence file: `play_store/play_console_post_upload_evidence_ru.md`.

Commands:

```bash
./tools/create_store_asset_review_sheet.py --write
./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>
```

Fields to resolve:

- Internal testing upload completed.
- Closed testing required for this account.
- Closed testing status if required.
- Pre-launch report result.
- Reproducible crashes in pre-launch report.
- Play policy warnings.
- Store listing preview checked for damaging image crops.

Required posture:

- Upload first through internal testing.
- Internal-testing evidence must explicitly mention `internal testing` and that the AAB was uploaded or upload completed.
- If the publisher account requires closed testing, complete the required tester/time gate before production.
- Pre-launch report must have no blocking issues, no reproducible crashes and no unresolved policy warnings.
- Pre-launch/policy evidence must explicitly mention `Play Console pre-launch report`, `no reproducible crashes` and `Play policy warnings`.
- Store listing preview evidence must explicitly mention the icon, feature graphic, phone screenshots, tablet screenshots and no damaging crops.

## Final Production Gate

Before production rollout:

```bash
./tools/run_final_local_gate.py --include-hosted-privacy
./tools/print_publication_readiness.py --check-recorded-privacy-url --require-production-ready
```

Expected production-ready marker only after all external evidence is recorded:

```text
publication_readiness_production_ready_owner_confirmed
```
