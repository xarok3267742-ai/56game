#!/usr/bin/env python3
"""Print safe privacy/contact evidence lines for the owner.

This helper is intentionally read-only. It does not claim that Play Console
support/contact fields were populated locally; it prints exact lines to copy
only after the owner has actually populated those Play Console fields and
entered the verified privacy policy URL.
"""

from __future__ import annotations

import argparse
import re


RECORDED_PRIVACY_URL = "https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html"
DESTINATION_EVIDENCE = "play_store/play_console_post_upload_evidence_ru.md"
PRIVACY_CONTACT_HANDOFF = "play_store/privacy_contact_handoff_ru.md"

CONTACT_TYPES = {
    "support-email": "email",
    "support-website": "support website URL",
}

CONTACT_TYPE_LINES = CONTACT_TYPES

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class PrivacyContactEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrivacyContactEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"privacy/contact evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "privacy/contact evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "privacy/contact evidence must not contain the actual support email address",
    )
    require(
        re.search(r"https?://(?!xarok3267742-ai\.github\.io/56game/privacy_policy_ru\.html\b)|www\.", value, re.I)
        is None,
        "privacy/contact evidence must not contain the actual support website URL or private links",
    )


def validate_contact_type(contact_type: str) -> None:
    allowed = ", ".join(sorted(CONTACT_TYPES))
    require(contact_type in CONTACT_TYPES, f"contact type must be one of: {allowed}")


def evidence_lines(contact_type: str) -> list[str]:
    validate_contact_type(contact_type)
    safe_type = CONTACT_TYPES[contact_type]
    lines = [
        f"- Public privacy policy URL: {RECORDED_PRIVACY_URL}.",
        "- Privacy policy URL check command returned `privacy_policy_url_ok`: privacy_policy_url_ok.",
        "- Privacy policy URL is HTTPS: yes.",
        "- Privacy policy URL is accessible without login: yes.",
        "- Privacy policy URL is not PDF: yes.",
        (
            "- Play Console support/contact field populated: "
            f"Play Console support/contact field populated with a real support contact {safe_type} for privacy inquiries."
        ),
        (
            "- Support/contact mechanism matches `play_store/privacy_policy_ru.html`: "
            "privacy policy inquiry mechanism uses the Google Play listing support contact."
        ),
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print safe Play Console privacy/contact evidence lines.")
    parser.add_argument(
        "--contact-type",
        choices=tuple(CONTACT_TYPES),
        default="support-email",
        help="Safe support/contact type to mention without recording the actual contact value.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        lines = evidence_lines(args.contact_type)
    except PrivacyContactEvidencePacketError as exc:
        print(f"privacy_contact_evidence_packet_error: {exc}")
        return 1

    print("Privacy/contact evidence packet")
    print("===============================")
    print(f"- Destination evidence file: {DESTINATION_EVIDENCE}")
    print(f"- Source handoff: {PRIVACY_CONTACT_HANDOFF}")
    print(f"- Recorded privacy policy URL: {RECORDED_PRIVACY_URL}")
    print("- Recheck URL before Play Console entry: ./tools/check_privacy_policy_url.py --url <https-url>")
    print("- Use these lines only after the Play Console support/contact field is actually populated and the privacy policy URL is entered.")
    print("- Do not record the actual support email address, support website URL, account tokens or private links.")
    print()
    print("Privacy URL Lines")
    print("-----------------")
    for line in lines[:5]:
        print(line)
    print()
    print("Privacy Contact Lines")
    print("---------------------")
    for line in lines[5:]:
        print(line)
    print()
    print("privacy_contact_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
