#!/usr/bin/env python3
"""Print safe signing-backup evidence lines for the owner.

This helper is intentionally read-only. It validates the local signing inputs
without printing password values, then prints exact lines to copy only after
the owner has actually backed up the upload keystore and credentials.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from check_signing_backup_inputs import (  # noqa: E402
    ACTIVE_KEYSTORE,
    EXPECTED_ALIAS,
    KEYSTORE_PROPERTIES,
    LEGACY_KEYSTORE,
    ROOT,
    SigningBackupInputError,
    check_owner_only_file,
    parse_properties,
    relative,
    validate_properties,
)


BACKUP_DATE_PLACEHOLDER = "REPLACE_WITH_ACTUAL_BACKUP_DATE_TIME"
DEFAULT_STORAGE_TYPE = "owner-controlled secure password manager plus encrypted offline backup"
DEFAULT_RESPONSIBLE_OWNER = "release owner recorded in owner tracker"
DEFAULT_RECORD_LOCATION = "backup record stored in owner tracker without secrets"

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "recovery code",
    "recovery codes",
    "AIza",
    "ya29.",
    "Bearer ",
)

NEGATIVE_DATE_MARKERS = (
    "not yet",
    "pending",
    "unknown",
    "todo",
    "tbd",
)

FULL_DATE_PATTERNS = (
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{2}\.\d{2}\.\d{4}\b",
    r"\b\d{1,2}\s+[A-Za-zА-Яа-яЁё]+\s+\d{4}\b",
    r"\b[A-Za-zА-Яа-яЁё]+\s+\d{1,2},?\s+\d{4}\b",
)


class SigningBackupEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SigningBackupEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"signing-backup evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "signing-backup evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "signing-backup evidence must not contain storage URLs or private links",
    )


def validate_backup_date(backup_date: str) -> str:
    value = backup_date.strip()
    require(value, "--backup-date must not be empty")
    validate_no_forbidden_evidence(value)
    lowered = value.lower()
    for marker in NEGATIVE_DATE_MARKERS:
        require(marker not in lowered, f"--backup-date must be a concrete date/time, not {backup_date!r}")
    require(
        any(re.search(pattern, value) for pattern in FULL_DATE_PATTERNS),
        "--backup-date must include a full date such as 2026-06-12",
    )
    return value


def validate_storage_type(storage_type: str) -> str:
    value = storage_type.strip()
    require(value, "--storage-type must not be empty")
    validate_no_forbidden_evidence(value)
    lowered = value.lower()
    for marker in ("owner-controlled", "secure"):
        require(marker in lowered, f"--storage-type must mention {marker}: {storage_type}")
    require(
        "password manager" in lowered or "encrypted" in lowered or "offline backup" in lowered,
        "--storage-type must name a safe storage type such as password manager or encrypted offline backup",
    )
    return value


def validate_responsible_owner(owner: str) -> str:
    value = owner.strip()
    require(value, "--responsible-owner must not be empty")
    validate_no_forbidden_evidence(value)
    lowered = value.lower()
    require("release owner" in lowered, "--responsible-owner must use a role-based release owner reference")
    require("owner tracker" in lowered, "--responsible-owner must mention the owner tracker")
    return value


def validate_record_location(location: str) -> str:
    value = location.strip()
    require(value, "--record-location must not be empty")
    validate_no_forbidden_evidence(value)
    lowered = value.lower()
    require("backup record" in lowered, "--record-location must mention a backup record")
    require(
        "owner tracker" in lowered or "password manager" in lowered,
        "--record-location must mention an owner tracker or password manager backup record",
    )
    return value


def local_preflight_lines() -> list[str]:
    active_mode = check_owner_only_file(ACTIVE_KEYSTORE, "active upload keystore")
    properties_mode = check_owner_only_file(KEYSTORE_PROPERTIES, "keystore properties")
    properties = parse_properties(KEYSTORE_PROPERTIES)
    validate_properties(properties)

    lines = [
        "- Command returned `signing_backup_input_ok`: signing_backup_input_ok.",
        f"- Active upload keystore exists and is owner-only: `{relative(ACTIVE_KEYSTORE)}`, mode `{active_mode:#04o}`.",
        f"- `keystore.properties` exists and is owner-only: mode `{properties_mode:#04o}`.",
        f"- `keystore.properties` points to `private/signing/qgrid-upload.p12`: `{relative(ACTIVE_KEYSTORE)}`.",
        f"- `keystore.properties` uses key alias `qgrid_upload`: `{EXPECTED_ALIAS}`.",
        "- `storePassword` and `keyPassword` fields are present; values were not printed or recorded: present; values were not printed and not recorded.",
    ]
    if LEGACY_KEYSTORE.exists():
        legacy_mode = check_owner_only_file(LEGACY_KEYSTORE, "legacy signing file")
        lines.append(
            f"- Legacy ignored local key exists and is owner-only: `{relative(LEGACY_KEYSTORE)}`, "
            f"mode `{legacy_mode:#04o}`; ignored, not active."
        )
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def signing_backup_lines(
    *,
    backup_date: str | None,
    storage_type: str,
    responsible_owner: str,
    record_location: str,
) -> list[str]:
    date_value = validate_backup_date(backup_date) if backup_date is not None else BACKUP_DATE_PLACEHOLDER
    storage_value = validate_storage_type(storage_type)
    owner_value = validate_responsible_owner(responsible_owner)
    record_value = validate_record_location(record_location)
    lines = [
        "- Backup completed before Play upload: backup completed for `private/signing/qgrid-upload.p12` and `keystore.properties` before Play upload.",
        f"- Secure owner-controlled storage type chosen: {storage_value}.",
        "- At least two owner-controlled secure copies exist: yes, two owner-controlled secure copies exist.",
        "- Recovery tested without exposing secrets: yes, recovery tested without exposing secrets.",
        f"- Responsible owner: {owner_value}.",
        f"- Backup date/time: {date_value}.",
        f"- Backup record location in owner tracker or password manager: {record_value}.",
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def post_upload_lines() -> list[str]:
    lines = [
        "- Active upload keystore backed up before AAB upload: backup completed for `private/signing/qgrid-upload.p12` and `keystore.properties` before AAB upload.",
        "- Owner-controlled backup evidence recorded without secrets: yes, recorded without secrets.",
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print safe signing-backup evidence lines.")
    parser.add_argument(
        "--backup-date",
        help="Concrete date/time of the real owner-controlled signing backup, for example '2026-06-12 14:30 local time'.",
    )
    parser.add_argument(
        "--storage-type",
        default=DEFAULT_STORAGE_TYPE,
        help="Safe storage type wording; must mention owner-controlled, secure and a concrete storage type.",
    )
    parser.add_argument(
        "--responsible-owner",
        default=DEFAULT_RESPONSIBLE_OWNER,
        help="Safe role-based owner wording; do not include personal data.",
    )
    parser.add_argument(
        "--record-location",
        default=DEFAULT_RECORD_LOCATION,
        help="Safe backup-record location wording; do not include URLs, credentials or access details.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        local_lines = local_preflight_lines()
        backup_lines = signing_backup_lines(
            backup_date=args.backup_date,
            storage_type=args.storage_type,
            responsible_owner=args.responsible_owner,
            record_location=args.record_location,
        )
        post_upload = post_upload_lines()
    except (OSError, SigningBackupInputError, SigningBackupEvidencePacketError) as exc:
        print(f"signing_backup_evidence_packet_error: {exc}", file=sys.stderr)
        return 1

    print("Signing backup evidence packet")
    print("==============================")
    print("- Source preflight: ./tools/check_signing_backup_inputs.py")
    print("- Destination evidence file: play_store/signing_backup_evidence_ru.md")
    print("- Destination post-upload evidence file: play_store/play_console_post_upload_evidence_ru.md")
    print("- Use owner backup lines only after the upload keystore and credentials are actually backed up.")
    if args.backup_date is None:
        print(f"- Backup date/time line contains `{BACKUP_DATE_PLACEHOLDER}`; replace it or rerun with --backup-date.")
    print()
    print("Local Preflight Lines")
    print("---------------------")
    for line in local_lines:
        print(line)
    print()
    print("Owner Backup Lines")
    print("------------------")
    for line in backup_lines:
        print(line)
    print()
    print("Post-Upload Backup Lines")
    print("------------------------")
    for line in post_upload:
        print(line)
    print()
    print("signing_backup_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
