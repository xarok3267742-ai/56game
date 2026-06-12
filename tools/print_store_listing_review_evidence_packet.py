#!/usr/bin/env python3
"""Print safe store-listing preview evidence lines for the owner.

This helper is intentionally read-only. It does not claim that Play Console
preview review was completed locally; it prints exact lines to copy only after
the owner has actually reviewed the Play Console store listing preview and
checked the current store asset review sheet.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION_EVIDENCE = "play_store/play_console_post_upload_evidence_ru.md"
REVIEW_SHEET = "play_store/store_asset_review_sheet.png"
REVIEW_SHEET_SIZE = (1800, 2050)

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class StoreListingReviewEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise StoreListingReviewEvidencePacketError(message)


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"review sheet must be a PNG: {path}")
    require(len(data) >= 24, f"review sheet PNG is truncated: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def verify_review_sheet() -> None:
    sheet = ROOT / REVIEW_SHEET
    require(sheet.is_file(), f"missing store asset review sheet: {REVIEW_SHEET}")
    require(png_size(sheet) == REVIEW_SHEET_SIZE, f"store asset review sheet must be {REVIEW_SHEET_SIZE[0]}x{REVIEW_SHEET_SIZE[1]}")


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"store-listing review evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "store-listing review evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "store-listing review evidence must not contain personal email addresses",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "store-listing review evidence must not contain private URLs or account links",
    )


def evidence_lines() -> list[str]:
    lines = [
        (
            "- Store listing preview checked for damaging image crops: "
            "Play Console store listing preview and current store asset review sheet checked for icon, "
            "feature graphic, phone screenshots and tablet screenshots; no damaging crops."
        ),
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def main() -> int:
    try:
        verify_review_sheet()
        lines = evidence_lines()
    except StoreListingReviewEvidencePacketError as exc:
        print(f"store_listing_review_evidence_packet_error: {exc}")
        return 1

    print("Store listing review evidence packet")
    print("====================================")
    print(f"- Destination evidence file: {DESTINATION_EVIDENCE}")
    print(f"- Source review sheet: {REVIEW_SHEET}")
    print("- Source review command: ./tools/create_store_asset_review_sheet.py --write")
    print("- Use these lines only after the Play Console store listing preview and current store asset review sheet are actually checked.")
    print("- Do not record account tokens, screenshots with account data, private URLs or reviewer personal data.")
    print()
    print("Store Preview Lines")
    print("-------------------")
    for line in lines:
        print(line)
    print()
    print("store_listing_review_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
