#!/usr/bin/env python3
"""Print safe post-upload evidence lines for the owner.

This helper is intentionally read-only. It does not claim that Play Console
upload happened locally; it prints exact lines to copy only after the owner has
actually uploaded the signed AAB through Play Console.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from print_upload_packet import (  # noqa: E402
    ROOT,
    UploadPacketError,
    parse_checksum_rows,
    verify_required_upload_paths,
    verify_rows,
)


AAB_PATH = "app/build/outputs/bundle/release/app-release.aab"
PACKAGE_NAME = "com.qgrid.mobile"
VERSION_CODE = "1"
VERSION_NAME = "1.0.0"
DEFAULT_TRACK = "internal testing"
UPLOAD_DATE_PLACEHOLDER = "REPLACE_WITH_ACTUAL_UPLOAD_DATE_TIME"

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
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


class PostUploadEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PostUploadEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"upload evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "upload evidence must not contain password, token, secret or API key assignments",
    )


def validate_upload_date(upload_date: str) -> str:
    value = upload_date.strip()
    require(value, "--upload-date must not be empty")
    validate_no_forbidden_evidence(value)
    lowered = value.lower()
    for marker in NEGATIVE_DATE_MARKERS:
        require(marker not in lowered, f"--upload-date must be a concrete date/time, not {upload_date!r}")
    require(
        any(re.search(pattern, value) for pattern in FULL_DATE_PATTERNS),
        "--upload-date must include a full date such as 2026-06-12",
    )
    return value


def verified_aab_sha256() -> str:
    rows = parse_checksum_rows()
    verify_required_upload_paths(rows)
    verify_rows(rows)
    for relative_path, _, checksum in rows:
        if relative_path == AAB_PATH:
            return checksum
    raise PostUploadEvidencePacketError(f"Upload checksum manifest missing {AAB_PATH}")


def evidence_lines(*, upload_date: str | None) -> list[str]:
    date_value = validate_upload_date(upload_date) if upload_date is not None else UPLOAD_DATE_PLACEHOLDER
    aab_sha = verified_aab_sha256()
    lines = [
        f"- Uploaded package name: {PACKAGE_NAME}.",
        f"- Uploaded version code: {VERSION_CODE}.",
        f"- Uploaded version name: {VERSION_NAME}.",
        f"- Uploaded AAB SHA-256: {aab_sha}.",
        f"- First release track used: {DEFAULT_TRACK}.",
        f"- Upload date/time: {date_value}.",
        "- Internal testing upload completed: internal testing upload completed; signed AAB was uploaded to internal testing.",
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print safe Play Console post-upload evidence lines.")
    parser.add_argument(
        "--upload-date",
        help="Concrete date/time of the real Play Console upload, for example '2026-06-12 14:30 local time'.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        lines = evidence_lines(upload_date=args.upload_date)
    except (OSError, UploadPacketError, PostUploadEvidencePacketError) as exc:
        print(f"post_upload_evidence_packet_error: {exc}", file=sys.stderr)
        return 1

    print("Post-upload evidence packet")
    print("===========================")
    print("- Source AAB: app/build/outputs/bundle/release/app-release.aab")
    print("- Destination evidence file: play_store/play_console_post_upload_evidence_ru.md")
    print("- Use these lines only after the signed AAB is actually uploaded through Play Console.")
    if args.upload_date is None:
        print(f"- Upload date/time line contains `{UPLOAD_DATE_PLACEHOLDER}`; replace it or rerun with --upload-date.")
    print()
    print("Upload Artifact Lines")
    print("---------------------")
    for line in lines[:6]:
        print(line)
    print()
    print("Testing Track Line")
    print("------------------")
    print(lines[6])
    print()
    print("post_upload_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
