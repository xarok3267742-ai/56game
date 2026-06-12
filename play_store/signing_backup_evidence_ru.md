# Signing Backup Evidence - RU

Этот файл предназначен для безопасной фиксации owner-controlled backup перед Google Play upload. До реального backup все пункты остаются внешними и не доказываются локальным репозиторием.

Не записывать сюда пароли, private keys, keystore contents, recovery codes, password-manager secrets, ссылки с доступом к закрытому хранилищу или персональные данные тестеров.

## Local Inputs To Back Up

- Active upload keystore: `private/signing/qgrid-upload.p12`.
- Signing credentials file: `keystore.properties`.
- Active key alias: `qgrid_upload`.
- Public certificate reference: `play_store/signing_certificate_report.md`.
- Legacy ignored local key: `private/signing/line56-upload.p12`; do not use it as the active upload key and do not upload it to Play Console.

## Local Preflight

Run before making or refreshing the secure backup:

```bash
./tools/check_signing_backup_inputs.py
./tools/print_signing_backup_evidence_packet.py
```

Latest local preflight, checked on 6 June 2026:

- Command returned `signing_backup_input_ok`.
- Active upload keystore exists and is owner-only: `private/signing/qgrid-upload.p12`, mode `0o600`.
- `keystore.properties` exists and is owner-only: mode `0o600`.
- `keystore.properties` points to `private/signing/qgrid-upload.p12`: `private/signing/qgrid-upload.p12`.
- `keystore.properties` uses key alias `qgrid_upload`: `qgrid_upload`.
- `storePassword` and `keyPassword` fields are present; values were not printed or recorded: present; values were not printed and not recorded.
- Legacy ignored local key exists and is owner-only: `private/signing/line56-upload.p12`, mode `0o600`; ignored, not active.

Expected owner-side backup result:

- Backup completed before Play upload: not yet available locally.
- Secure owner-controlled storage type chosen: not yet available locally.
- At least two owner-controlled secure copies exist: not yet available locally.
- Recovery tested without exposing secrets: not yet available locally.

When replacing the pending backup lines after a real backup, keep the values safe and specific:

- Run `./tools/print_signing_backup_evidence_packet.py --backup-date <date/time>` after the real owner-controlled backup and copy only the safe owner backup lines. Do not copy the placeholder backup date from the default no-argument output.
- For backup completion, explicitly mention `private/signing/qgrid-upload.p12`, `keystore.properties` and `before Play upload`.
- For storage type, use wording like `owner-controlled secure password manager plus encrypted offline backup`.
- For secure copies, use wording like `yes, two owner-controlled secure copies exist`.
- For recovery, use wording like `yes, recovery tested without exposing secrets`.
- For responsible owner, use a role-based safe reference like `release owner recorded in owner tracker`.
- For backup record location, mention an `owner tracker` or `password manager` backup record without recording storage access details.

## Backup Evidence To Record

- Responsible owner: not yet available locally.
- Backup date/time: not yet available locally.
- Backup record location in owner tracker or password manager: not yet available locally.

## Stop-Release Notes

Stop the Play upload until resolved if any of these are true:

- `./tools/check_signing_backup_inputs.py` does not return `signing_backup_input_ok`.
- `keystore.properties` points anywhere other than `private/signing/qgrid-upload.p12`.
- The key alias is not `qgrid_upload`.
- The active upload keystore or `keystore.properties` is group/world-readable.
- The active upload keystore and credentials are not backed up in owner-controlled secure storage.
- Fewer than two owner-controlled secure backup copies exist.
- Recovery has not been tested without exposing secrets.
- The legacy `private/signing/line56-upload.p12` is being treated as the active upload key.

## Safe Summary To Copy Back

After backup, copy only a safe summary into `docs/release_report.md`: backup completed, backup evidence recorded in owner-controlled storage and `./tools/check_signing_backup_inputs.py` returned `signing_backup_input_ok`. Do not copy passwords, keystore contents, private keys or storage access details.
