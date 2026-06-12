#!/usr/bin/env python3
"""Print and verify the Play Console form packet for the owner.

This helper is intentionally read-only. It does not build, upload, contact
Google Play or print signing secrets; it verifies the local handoff files and
prints the copy-ready listing, app-content posture and remaining owner gates.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LISTING_PATH = ROOT / "play_store/listing_ru.md"
SUBMISSION_PATH = ROOT / "play_store/play_console_submission_ru.md"
APP_CONTENT_PATH = ROOT / "play_store/app_content_answers_ru.md"
CLOSED_TESTING_PATH = ROOT / "play_store/closed_testing_handoff_ru.md"
PRODUCTION_ACCESS_PATH = ROOT / "play_store/production_access_answers_ru.md"
PRIVACY_CONTACT_PATH = ROOT / "play_store/privacy_contact_handoff_ru.md"
DATA_SAFETY_PATH = ROOT / "play_store/data_safety_ru.md"
CONTENT_RATING_PATH = ROOT / "play_store/content_rating_notes.md"
OWNER_INPUTS_PATH = ROOT / "play_store/owner_release_inputs.md"
PRIVACY_CHECKLIST_PATH = ROOT / "play_store/privacy_policy_hosting_checklist.md"
SIGNING_BACKUP_EVIDENCE_PATH = ROOT / "play_store/signing_backup_evidence_ru.md"
POST_UPLOAD_EVIDENCE_PATH = ROOT / "play_store/play_console_post_upload_evidence_ru.md"
FORBIDDEN_LISTING_MARKERS = (
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bplaceholder\b",
    r"contact-required",
)


class PlayConsolePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlayConsolePacketError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing handoff file: {path.relative_to(ROOT).as_posix()}")
    return path.read_text(encoding="utf-8")


def markdown_section(text: str, heading: str, level: int = 2) -> str:
    marker = "#" * level
    pattern = re.compile(rf"^{re.escape(marker)}\s+{re.escape(heading)}\s*$", re.M)
    match = pattern.search(text)
    require(match is not None, f"missing markdown section: {heading}")
    next_heading = re.compile(rf"^#{{1,{level}}}\s+", re.M)
    next_match = next_heading.search(text, match.end())
    end = next_match.start() if next_match else len(text)
    return text[match.end() : end].strip()


def one_line_section(text: str, heading: str) -> str:
    section = markdown_section(text, heading)
    lines = [line.strip() for line in section.splitlines() if line.strip()]
    require(len(lines) == 1, f"{heading} must be one non-empty line")
    return lines[0]


def verify_listing(listing: str, submission: str) -> dict[str, str]:
    app_name = one_line_section(listing, "App Name")
    short_description = one_line_section(listing, "Short Description")
    full_description = markdown_section(listing, "Full Description")
    release_notes = markdown_section(listing, "Release Notes")

    require(len(app_name) <= 30, "app name exceeds Play Console 30-character limit")
    require(len(short_description) <= 80, "short description exceeds Play Console 80-character limit")
    require(len(full_description) <= 4000, "full description exceeds Play Console 4000-character limit")
    require(len(release_notes) <= 500, "release notes exceed Play Console 500-character limit")
    for value_name, value in [
        ("app name", app_name),
        ("short description", short_description),
        ("full description", full_description),
        ("release notes", release_notes),
    ]:
        for marker in FORBIDDEN_LISTING_MARKERS:
            require(re.search(marker, value, re.I) is None, f"{value_name} contains forbidden placeholder marker: {marker}")
        require(value in submission, f"{value_name} is not synced into play_console_submission_ru.md")

    return {
        "app_name": app_name,
        "short_description": short_description,
        "full_description": full_description,
        "release_notes": release_notes,
    }


def require_markers(path: Path, markers: tuple[str, ...]) -> str:
    text = read(path)
    relative = path.relative_to(ROOT).as_posix()
    for marker in markers:
        require(marker in text, f"{relative} missing marker: {marker}")
    return text


def verify_policy_handoff() -> None:
    require_markers(
        APP_CONTENT_PATH,
        (
            "Restricted access: No.",
            "Contains ads: No.",
            "Does the app collect or share any required user data types: No.",
            "User data collected: none.",
            "User data shared: none.",
            "Target age groups: 13-15, 16-17, 18 and over.",
            "In-app generative AI features: No.",
            "First upload target: Internal testing.",
        ),
    )
    require_markers(
        PRODUCTION_ACCESS_PATH,
        (
            "Production Access Answers - RU",
            "Apply for production access",
            "About Your Closed Test",
            "About Your App Or Game",
            "Production Readiness",
            "No tester names, email addresses or invite links are included here.",
            "Production access status if required",
        ),
    )
    require_markers(
        CLOSED_TESTING_PATH,
        (
            "Closed Testing Handoff - RU",
            "App testing requirements for new personal developer accounts",
            "at least 12 testers who have been opted-in for at least the last 14 days continuously",
            "Tester Task Script",
            "Feedback Topics",
            "Evidence Phrases Accepted By Local Gate",
            "Closed testing status if required: completed required closed testing with 12 opted-in testers for 14 continuous days.",
            "No tester names, email addresses, invite links or private tester URLs are recorded.",
        ),
    )
    require_markers(
        PRIVACY_CONTACT_PATH,
        (
            "Privacy Contact Handoff - RU",
            "Google Play Console Help `User Data`",
            "https://support.google.com/googleplay/android-developer/answer/10144311?hl=en",
            "Hosted privacy policy URL: `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.",
            "Play Console support/contact field populated: Play Console support/contact field populated with a real support contact email for privacy inquiries.",
            "Support/contact mechanism matches `play_store/privacy_policy_ru.html`: privacy policy inquiry mechanism uses the Google Play listing support contact.",
            "do not record the actual support email or URL",
        ),
    )
    require_markers(
        DATA_SAFETY_PATH,
        (
            "Данные пользователя не собираются.",
            "Данные не передаются третьим лицам.",
            "Android backup для приложения отключён",
            "Manifest не запрашивает `INTERNET` или `ACCESS_NETWORK_STATE`.",
        ),
    )
    require_markers(
        CONTENT_RATING_PATH,
        (
            "Expected category: Games / Puzzle.",
            "Violence: none.",
            "Gambling, simulated gambling or betting: none.",
            "Online gameplay or online interaction: none.",
            "Personal data sharing: none.",
        ),
    )
    require_markers(
        OWNER_INPUTS_PATH,
        (
            "Production package: `com.qgrid.mobile`.",
            "Play Console developer account and package registration",
            "Privacy policy URL",
            "Signing backup",
            "Play account testing path",
            "publication is still blocked externally",
        ),
    )
    require_markers(
        PRIVACY_CHECKLIST_PATH,
        (
            "./tools/check_privacy_policy_url.py --local",
            "./tools/check_privacy_policy_url.py --url <https-url>",
            "Public HTTPS hosting",
        ),
    )
    require_markers(
        SIGNING_BACKUP_EVIDENCE_PATH,
        (
            "Command returned `signing_backup_input_ok`.",
            "Backup record location in owner tracker or password manager: not yet available locally.",
            "Do not copy passwords, keystore contents, private keys or storage access details.",
        ),
    )
    require_markers(
        POST_UPLOAD_EVIDENCE_PATH,
        (
            "Play Console Post-Upload Evidence - RU",
            "Play Console developer account identity verified: not yet available locally.",
            "Play Console package name `com.qgrid.mobile` registered: not yet available locally.",
            "Signing backup input check command returned `signing_backup_input_ok`: recorded locally on 6 June 2026.",
            "Public privacy policy URL: https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html.",
            "Privacy policy URL check command returned `privacy_policy_url_ok`: privacy_policy_url_ok.",
            "Use `play_store/privacy_contact_handoff_ru.md` for exact safe evidence phrases. Do not record the actual support email address or support website URL.",
            "Internal testing upload completed: not yet available locally.",
        ),
    )


def print_packet(listing_values: dict[str, str]) -> None:
    print("Google Play Console packet")
    print("==========================")
    print("- Package name: com.qgrid.mobile")
    print("- Version code: 1")
    print("- Version name: 1.0.0")
    print("- App type/category: Game / Puzzle")
    print("- Monetization: free; no ads; no in-app purchases")
    print()
    print("Store listing")
    print("-------------")
    print(f"App name: {listing_values['app_name']}")
    print(f"Short description: {listing_values['short_description']}")
    print("Full description:")
    print(listing_values["full_description"])
    print("Release notes:")
    print(listing_values["release_notes"])
    print()
    print("App content posture")
    print("-------------------")
    print("- App access: no restricted access, login, account or paid access.")
    print("- Ads: no.")
    print("- Data Safety: no user data collected or shared.")
    print("- Permissions: no INTERNET, no ACCESS_NETWORK_STATE and no dangerous runtime permissions.")
    print("- Content rating: Games / Puzzle; no violence, gambling, UGC, purchases or online interaction.")
    print("- Target audience recommendation: 13-15, 16-17, 18 and over; not child-directed.")
    print("- AI disclosure: no in-app generative AI features.")
    print()
    print("Manual owner gates")
    print("------------------")
    print("- Verify Play Console developer identity/profile and register or create package name com.qgrid.mobile.")
    print("- Enter privacy policy URL: https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html")
    print("- Recheck before entry: ./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html")
    print("- Populate Play Console support/contact fields used by the privacy policy inquiry mechanism.")
    print("- Use play_store/privacy_contact_handoff_ru.md for privacy/contact safe evidence wording.")
    print("- Complete secure signing backup using play_store/signing_backup_evidence_ru.md.")
    print("- Upload first to internal testing; run closed testing if the publisher account requires it.")
    print("- Use play_store/closed_testing_handoff_ru.md for closed-test tester instructions and safe evidence phrases.")
    print("- Receive Play Console production access if the publisher account requires it.")
    print("- Prepare production-access answers with play_store/production_access_answers_ru.md if Play Console asks for them.")
    print("- Record safe post-upload facts in play_store/play_console_post_upload_evidence_ru.md.")
    print()
    print("play_console_packet_ok")


def main() -> int:
    try:
        listing = read(LISTING_PATH)
        submission = require_markers(
            SUBMISSION_PATH,
            (
                "Package name: `com.qgrid.mobile`",
                "Version code: `1`",
                "Version name: `1.0.0`",
                "Field-by-field source: `play_store/app_content_answers_ru.md`.",
                "Use `play_store/privacy_contact_handoff_ru.md` for privacy URL, support/contact field and safe evidence wording without recording the actual support email or URL.",
                "Use `play_store/closed_testing_handoff_ru.md` for closed-test tester instructions, aggregate feedback topics and safe evidence phrases if closed testing is required.",
                "Final Manual Gates",
                "Re-run `./tools/run_final_local_gate.py` and require `final_local_gate_ok` immediately before uploading.",
            ),
        )
        listing_values = verify_listing(listing, submission)
        verify_policy_handoff()
        print_packet(listing_values)
    except (OSError, PlayConsolePacketError) as exc:
        print(f"play_console_packet_error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
