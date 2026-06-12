#!/usr/bin/env python3
"""Print safe closed-testing and production-access evidence lines for the owner.

This helper is intentionally read-only. It does not claim that Google Play
closed testing or production access was completed locally; it prints exact
lines to copy only after the owner has verified the matching Play Console
account path.
"""

from __future__ import annotations

import argparse
import re


DESTINATION_EVIDENCE = "play_store/play_console_post_upload_evidence_ru.md"
MODE_NOT_REQUIRED = "not_required"
MODE_REQUIRED_COMPLETED = "required_completed"

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class ClosedTestingEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClosedTestingEvidencePacketError(message)


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"closed-testing evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "closed-testing evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "closed-testing evidence must not contain tester email addresses",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "closed-testing evidence must not contain tester URLs or private links",
    )


def evidence_lines(mode: str) -> list[str]:
    if mode == MODE_NOT_REQUIRED:
        lines = [
            "- Closed testing required for this account: no.",
            "- Closed testing status if required: not required for this account.",
            "- Production access status if required: not required for this account.",
        ]
    elif mode == MODE_REQUIRED_COMPLETED:
        lines = [
            "- Closed testing required for this account: yes.",
            "- Closed testing status if required: completed required closed testing with 12 opted-in testers for 14 continuous days.",
            "- Production access status if required: Play Console production access granted.",
        ]
    else:
        raise ClosedTestingEvidencePacketError(f"unknown closed-testing mode: {mode}")
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print safe closed-testing evidence lines.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--not-required",
        action="store_true",
        help="Print lines for accounts where Play Console does not require closed testing before production.",
    )
    group.add_argument(
        "--required-completed",
        action="store_true",
        help="Print lines for accounts where required closed testing is completed and production access is granted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the available evidence modes without printing copyable evidence lines.",
    )
    args = parser.parse_args()
    if args.dry_run and (args.not_required or args.required_completed):
        parser.error("--dry-run cannot be combined with evidence modes")
    return args


def selected_mode(args: argparse.Namespace) -> str | None:
    if args.not_required:
        return MODE_NOT_REQUIRED
    if args.required_completed:
        return MODE_REQUIRED_COMPLETED
    return None


def print_header() -> None:
    print("Closed testing evidence packet")
    print("==============================")
    print(f"- Destination evidence file: {DESTINATION_EVIDENCE}")
    print("- Use one evidence mode only after the matching Play Console account path is actually confirmed.")
    print("- Do not record tester names, tester emails, invite links, private URLs, screenshots with account data or tokens.")


def main() -> int:
    args = parse_args()
    mode = selected_mode(args)
    if mode is None:
        print_header()
        print()
        print("Available Evidence Modes")
        print("------------------------")
        print("- Account does not require closed testing: ./tools/print_closed_testing_evidence_packet.py --not-required")
        print("- Required closed testing completed and Play Console production access granted: ./tools/print_closed_testing_evidence_packet.py --required-completed")
        print()
        print("closed_testing_evidence_packet_dry_run_ok")
        return 0

    try:
        lines = evidence_lines(mode)
    except ClosedTestingEvidencePacketError as exc:
        print(f"closed_testing_evidence_packet_error: {exc}")
        return 1

    print_header()
    print()
    print("Testing Track Lines")
    print("-------------------")
    for line in lines:
        print(line)
    print()
    print("closed_testing_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
