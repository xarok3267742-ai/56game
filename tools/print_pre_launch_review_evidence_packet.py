#!/usr/bin/env python3
"""Print safe Play pre-launch and policy review evidence lines for the owner.

This helper is intentionally read-only. It does not claim that Play Console
pre-launch review was completed locally; it prints exact lines to copy only
after the owner has actually reviewed the Play Console pre-launch report and
policy warnings for the uploaded release.
"""

from __future__ import annotations

import re


DESTINATION_EVIDENCE = "play_store/play_console_post_upload_evidence_ru.md"

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class PreLaunchReviewEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreLaunchReviewEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"pre-launch review evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "pre-launch review evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "pre-launch review evidence must not contain personal email addresses",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "pre-launch review evidence must not contain private URLs or account links",
    )


def evidence_lines() -> list[str]:
    lines = [
        "- Pre-launch report result: Play Console pre-launch report passed with no blocking issues.",
        "- Reproducible crashes in pre-launch report: Play Console pre-launch report shows no reproducible crashes.",
        "- Play policy warnings: Play policy warnings reviewed: no unresolved warnings.",
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def main() -> int:
    try:
        lines = evidence_lines()
    except PreLaunchReviewEvidencePacketError as exc:
        print(f"pre_launch_review_evidence_packet_error: {exc}")
        return 1

    print("Play pre-launch review evidence packet")
    print("======================================")
    print(f"- Destination evidence file: {DESTINATION_EVIDENCE}")
    print("- Use these lines only after the Play Console pre-launch report and policy warnings are actually reviewed.")
    print("- Do not record account tokens, tester personal data, private URLs or Play Console screenshot links.")
    print()
    print("Pre-Launch Review Lines")
    print("-----------------------")
    for line in lines:
        print(line)
    print()
    print("pre_launch_review_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
