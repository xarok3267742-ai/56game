#!/usr/bin/env python3
"""Print safe Play Console form evidence lines for the owner.

This helper is intentionally read-only. It does not claim that Play Console
forms were completed locally; it prints exact lines to copy only after the
owner has actually completed the matching Play Console forms.
"""

from __future__ import annotations

import re


FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class PlayConsoleFormsEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlayConsoleFormsEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"Play Console forms evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "Play Console forms evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "Play Console forms evidence must not contain personal email addresses",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "Play Console forms evidence must not contain private URLs or invite links",
    )


def evidence_lines() -> list[str]:
    lines = [
        "- App access completed as no restricted access/login/account: Play Console App access completed as no restricted access, no login and no account required.",
        "- Ads declaration completed as no ads: Play Console ads declaration completed as no ads.",
        "- Data Safety completed as no user data collected or shared: Data Safety completed as no user data collected and no user data shared.",
        "- Content rating completed as Games / Puzzle posture: Content rating completed with Games / Puzzle posture.",
        "- Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path: Target audience completed as 13+ non-child-directed posture.",
        "- AI disclosure completed as no in-app generative AI features: AI disclosure completed as no in-app generative AI features.",
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def main() -> int:
    try:
        lines = evidence_lines()
    except PlayConsoleFormsEvidencePacketError as exc:
        print(f"play_console_forms_evidence_packet_error: {exc}")
        return 1

    print("Play Console forms evidence packet")
    print("==================================")
    print("- Destination evidence file: play_store/play_console_post_upload_evidence_ru.md")
    print("- Use these lines only after the matching Play Console forms are actually completed.")
    print("- Do not record account tokens, support-contact values, tester personal data or invite links.")
    print()
    print("Policy Form Lines")
    print("-----------------")
    for line in lines:
        print(line)
    print()
    print("play_console_forms_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
