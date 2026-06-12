#!/usr/bin/env python3
"""Print safe Play Console developer account evidence lines for the owner.

This helper is intentionally read-only. It does not claim that the Play
Console developer account, developer profile or package-name registration were
completed locally; it prints exact safe lines to copy only after the owner has
actually verified those facts in Play Console.
"""

from __future__ import annotations

import re


DESTINATION_EVIDENCE = "play_store/play_console_post_upload_evidence_ru.md"
PACKAGE_NAME = "com.qgrid.mobile"

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class DeveloperAccountEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeveloperAccountEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"developer account evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "developer account evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "developer account evidence must not contain personal email addresses",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "developer account evidence must not contain private URLs or invite links",
    )


def evidence_lines() -> list[str]:
    lines = [
        "- Play Console developer account identity verified: Play Console developer account identity verification completed for the release account.",
        "- Play Console developer profile contact information completed: Play Console developer profile/contact information completed; no private contact value recorded.",
        f"- Play Console package name `{PACKAGE_NAME}` registered: Play Console package name `{PACKAGE_NAME}` registered in the release account.",
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def main() -> int:
    try:
        lines = evidence_lines()
    except DeveloperAccountEvidencePacketError as exc:
        print(f"developer_account_evidence_packet_error: {exc}")
        return 1

    print("Developer account evidence packet")
    print("=================================")
    print(f"- Destination evidence file: {DESTINATION_EVIDENCE}")
    print("- Use these lines only after Play Console developer identity/profile and package-name registration are actually confirmed.")
    print("- Do not record legal names, addresses, account tokens, contact values, private URLs or invite links.")
    print()
    print("Developer Account Lines")
    print("-----------------------")
    for line in lines:
        print(line)
    print()
    print("developer_account_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
