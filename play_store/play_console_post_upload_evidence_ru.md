# Play Console Post-Upload Evidence - RU

Этот файл предназначен для безопасной фиксации внешних Play Console фактов после upload. До реальной загрузки все пункты остаются owner-controlled и не доказываются локальным репозиторием.

Не записывать сюда пароли, private keys, keystore contents, внутренние Play account tokens, персональные данные тестеров или закрытые ссылки с доступом к аккаунту.

## Upload Artifact

- Uploaded package name: not yet available locally; must be `com.qgrid.mobile`.
- Uploaded version code: not yet available locally; must be `1`.
- Uploaded version name: not yet available locally; must be `1.0.0`.
- Uploaded AAB SHA-256: not yet available locally; compare with `play_store/upload_checksums.md`.
- First release track used: not yet available locally.
- Upload date/time: not yet available locally.

After the real Play Console upload, run `./tools/print_post_upload_evidence_packet.py --upload-date <date/time>` and copy the safe upload artifact/internal-testing evidence lines from its output. Do not copy the placeholder upload date from the default no-argument output.

## Privacy And Contact

- Public privacy policy URL: https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html.
- Privacy policy URL check command returned `privacy_policy_url_ok`: privacy_policy_url_ok.
- Privacy policy URL is HTTPS: yes.
- Privacy policy URL is accessible without login: yes.
- Privacy policy URL is not PDF: yes.
- Play Console support/contact field populated: not yet available locally.
- Support/contact mechanism matches `play_store/privacy_policy_ru.html`: not yet available locally.

After entering the privacy policy URL, keep support/contact evidence explicit and do not use a bare `yes`: the support/contact line must mention the Play Console support/contact field, that it is populated with a real support contact for privacy inquiries, and the safe contact type as support email or support website URL without recording the actual email address or URL. The mechanism line must mention the Google Play listing support contact, the privacy policy and the privacy inquiry mechanism.
Use `play_store/privacy_contact_handoff_ru.md` for exact safe evidence phrases. Do not record the actual support email address or support website URL.

## Signing Backup

- Signing backup evidence file: `play_store/signing_backup_evidence_ru.md`.
- Signing backup input check command returned `signing_backup_input_ok`: recorded locally on 6 June 2026.
- Active upload keystore backed up before AAB upload: not yet available locally.
- Owner-controlled backup evidence recorded without secrets: not yet available locally.

After the real backup is complete, keep the backup evidence line explicit and safe, for example: `yes, recorded without secrets`.
The active-keystore backup line must explicitly mention `private/signing/qgrid-upload.p12` and `before AAB upload`; do not record passwords, key contents or recovery codes.
Use `./tools/print_signing_backup_evidence_packet.py --backup-date <date/time>` after the real owner-controlled backup and copy only the safe post-upload backup lines.

## Play-Generated Artifact Review

- Play-generated APK verification command: run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` on a downloaded Play-generated APK artifact and require `play_generated_apk_verify_ok`.
- Play-generated APK package is `com.qgrid.mobile`: not yet available locally.
- Play-generated APK signature verifies and certificate SHA-256 recorded: not yet available locally.
- Play-generated app label is `Линия 56`: not yet available locally.
- Play-generated icon matches `play_store/icon/play_icon_512.png`: not yet available locally.
- Play-generated version code/name match this release candidate: not yet available locally.
- Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions: not yet available locally.
- Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest: not yet available locally.
- Play-generated native libraries support 16 KB page sizes: not yet available locally.
- Play-generated APK installed and launched on at least one Android device or emulator: not yet available locally.

After Play-generated artifact review, the icon line must be based on helper output `store icon pixel matches: ...`, `application icon linked store icon: ...` and `round icon linked store icon: ...`, not only a visual/manual size check.
The signature line must explicitly include `verified`, `SHA-256` and the signer certificate SHA-256 fingerprint from helper output `signer certificate SHA-256: ...`; do not record signing passwords or keystore contents.
The icon line must explicitly mention application-icon-linked and round-icon-linked store-icon pixel matches.
The version line must explicitly include `versionCode 1` and `versionName 1.0.0`, based on helper output `versionCode: 1` and `versionName: 1.0.0`.
After Play-generated artifact review, the permissions line must explicitly include `no INTERNET`, `no ACCESS_NETWORK_STATE` and `no dangerous runtime permissions`.
The manifest privacy line must explicitly include `allowBackup=false` and `no debuggable`, based on helper output `allowBackup: false` and `debuggable: absent` or `debuggable: false`.
The native-library line must explicitly include `16 KB`, `16384`, `uncompressed`, `ZIP-aligned` and `extractNativeLibs=false`, based on helper output `native libraries: 8 checked; minimum PT_LOAD alignment: 16384 bytes`, `native APK packaging: 8 uncompressed; minimum ZIP data alignment: 16384 bytes` and `extractNativeLibs: false`.
The install/launch line must explicitly say the Play-generated APK was `installed` and `launched` on an Android device or Android emulator; do not use a bare `yes`.

## Policy Forms

- App access completed as no restricted access/login/account: not yet available locally.
- Ads declaration completed as no ads: not yet available locally.
- Data Safety completed as no user data collected or shared: not yet available locally.
- Content rating completed as Games / Puzzle posture: not yet available locally.
- Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path: not yet available locally.
- AI disclosure completed as no in-app generative AI features: not yet available locally.

After completing Policy Forms, keep the evidence explicit and do not use a bare `yes`: app access must mention `no restricted access`, `no login` and `no account`; ads must mention `no ads`; Data Safety must mention `no user data collected` and `no user data shared`; content rating must mention `Games` and `Puzzle`; target audience must mention `13+` and `non-child-directed`; AI disclosure must mention `no in-app generative AI features`.

## Testing And Review

- Internal testing upload completed: not yet available locally.
- Closed testing required for this account: not yet available locally.
- Closed testing status if required: not yet available locally.
- Production access status if required: not yet available locally.
- Pre-launch report result: not yet available locally.
- Reproducible crashes in pre-launch report: not yet available locally.
- Play policy warnings: not yet available locally.
- Store listing preview checked for damaging image crops: not yet available locally.

After internal testing upload, the internal-testing line must explicitly mention `internal testing` and that the AAB was uploaded or upload completed; do not use a bare `yes`.
If closed testing is required for the publisher account, the closed-testing status line must explicitly mention completed required closed testing, at least 12 opted-in testers and at least 14 continuous days. Do not record tester names, emails, URLs or invite links.
If closed testing is required for the publisher account, the production-access status line must explicitly mention `Play Console production access` and that it was `granted` or `approved`. If closed testing is not required for this account, record `not required for this account`.
After Play Console pre-launch review, the pre-launch result line must explicitly mention `Play Console pre-launch report` and `passed` or `no blocking issues`; the crash line must mention `pre-launch report` and `no reproducible crashes`; the policy-warning line must mention `Play policy warnings` and `no warnings`, `no unresolved warnings` or `resolved`.
After store-listing preview review, the preview-crop line must explicitly mention the icon, feature graphic, phone screenshots, tablet screenshots and `no damaging crops`; do not use a bare `yes`.

## Stop-Release Notes

Stop production rollout and return to local rebuild/recheck if any external evidence contradicts:

- package `com.qgrid.mobile`;
- versionCode `1` and versionName `1.0.0`;
- no-data/no-network/no-ads/no-payments/no-accounts posture;
- Play-ready icon, feature graphic and screenshot set;
- no reproducible crash in Play-generated artifacts;
- owner-approved public privacy policy URL and support/contact fields.

## Safe Summary To Copy Back

After upload, copy only a safe summary into `docs/release_report.md`: track used, public privacy policy URL, Play-generated artifact review result, pre-launch report result, policy warning status and testing-track status. Do not copy secrets or tester personal data.
