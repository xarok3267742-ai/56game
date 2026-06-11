#!/usr/bin/env python3
"""Print local-vs-production publication readiness for the owner.

This helper is intentionally read-only. It separates the locally verified
release candidate from the external Google Play publication gates that cannot
be proven from this repository: public privacy URL, support contact, signing
backup, Play Console forms, testing tracks and Play-generated artifact review.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse


ROOT = Path(__file__).resolve().parents[1]
POST_UPLOAD_EVIDENCE = ROOT / "play_store/play_console_post_upload_evidence_ru.md"
SIGNING_BACKUP_EVIDENCE = ROOT / "play_store/signing_backup_evidence_ru.md"
OWNER_INPUTS = ROOT / "play_store/owner_release_inputs.md"
UPLOAD_CHECKSUMS = ROOT / "play_store/upload_checksums.md"
PRIVACY_URL_CHECK = ROOT / "tools/check_privacy_policy_url.py"

REQUIRED_OWNER_GATES = (
    "Public privacy policy URL",
    "Play Console support/contact field populated",
    "Active upload keystore backed up before AAB upload",
    "App access completed as no restricted access/login/account",
    "Ads declaration completed as no ads",
    "Data Safety completed as no user data collected or shared",
    "Content rating completed as Games / Puzzle posture",
    "Target audience completed as non-child-directed 13+ posture",
    "Internal testing upload completed",
    "Pre-launch report result",
    "Store listing preview checked for damaging image crops",
)

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)

FORBIDDEN_EVIDENCE_PATTERNS = (
    r"(?im)(?:^|[\s`'\"-])(?:storePassword|keyPassword|store_password|key_password|client_secret|api[_-]?key|access[_-]?token|refresh[_-]?token|password|token)\s*[`'\"\]]*\s*[:=]\s*\S+",
    r"(?im)\bbearer\s+[A-Za-z0-9._~+/=-]+",
)

PLACEHOLDER_PRIVACY_HOSTS = (
    "example.com",
    "example.org",
    "example.net",
)

POSITIVE_EVIDENCE_VALUES = (
    "yes",
    "completed",
    "recorded",
    "passed",
    "ok",
)

NEGATIVE_EVIDENCE_PHRASES = (
    "not yet",
    "not available",
    "not completed",
    "not done",
    "pending",
    "blocked",
    "failed",
    "incomplete",
    "unavailable",
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

POST_UPLOAD_LABELS = (
    "Uploaded package name",
    "Uploaded version code",
    "Uploaded version name",
    "Uploaded AAB SHA-256",
    "First release track used",
    "Upload date/time",
    "Public privacy policy URL",
    "Privacy policy URL check command returned `privacy_policy_url_ok`",
    "Privacy policy URL is HTTPS",
    "Privacy policy URL is accessible without login",
    "Privacy policy URL is not PDF",
    "Play Console support/contact field populated",
    "Support/contact mechanism matches `play_store/privacy_policy_ru.html`",
    "Signing backup evidence file",
    "Signing backup input check command returned `signing_backup_input_ok`",
    "Active upload keystore backed up before AAB upload",
    "Owner-controlled backup evidence recorded without secrets",
    "Play-generated APK package is `com.qgrid.mobile`",
    "Play-generated app label is `Линия 56`",
    "Play-generated icon matches `play_store/icon/play_icon_512.png`",
    "Play-generated version code/name match this release candidate",
    "Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions",
    "Play-generated native libraries support 16 KB page sizes",
    "Play-generated APK installed and launched on at least one Android device or emulator",
    "App access completed as no restricted access/login/account",
    "Ads declaration completed as no ads",
    "Data Safety completed as no user data collected or shared",
    "Content rating completed as Games / Puzzle posture",
    "Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path",
    "AI disclosure completed as no in-app generative AI features",
    "Internal testing upload completed",
    "Closed testing required for this account",
    "Closed testing status if required",
    "Pre-launch report result",
    "Reproducible crashes in pre-launch report",
    "Play policy warnings",
    "Store listing preview checked for damaging image crops",
)

SIGNING_BACKUP_LABELS = (
    "Active upload keystore",
    "Signing credentials file",
    "Active key alias",
    "Public certificate reference",
    "Legacy ignored local key",
    "Command returned `signing_backup_input_ok`",
    "Active upload keystore exists and is owner-only",
    "`keystore.properties` exists and is owner-only",
    "`keystore.properties` points to `private/signing/qgrid-upload.p12`",
    "`keystore.properties` uses key alias `qgrid_upload`",
    "`storePassword` and `keyPassword` fields are present; values were not printed or recorded",
    "Legacy ignored local key exists and is owner-only",
    "Backup completed before Play upload",
    "Secure owner-controlled storage type chosen",
    "At least two owner-controlled secure copies exist",
    "Recovery tested without exposing secrets",
    "Responsible owner",
    "Backup date/time",
    "Backup record location in owner tracker or password manager",
)

OWNER_ACTION_GROUPS = (
    (
        "Upload artifact identity",
        "Upload the signed AAB through a testing track first and record exact artifact facts.",
        ("play_store/play_console_post_upload_evidence_ru.md",),
        ("./tools/print_upload_packet.py",),
        (
            "Uploaded package name",
            "Uploaded version code",
            "Uploaded version name",
            "Uploaded AAB SHA-256",
            "First release track used",
            "Upload date/time",
        ),
    ),
    (
        "Privacy policy and Play contact",
        "Validate the hosted privacy policy URL, enter it in Play Console and populate Play Console support/contact fields.",
        ("play_store/play_console_post_upload_evidence_ru.md",),
        ("./tools/check_privacy_policy_url.py --url <https-url>",),
        (
            "Public privacy policy URL",
            "Privacy policy URL check command returned `privacy_policy_url_ok`",
            "Privacy policy URL is HTTPS",
            "Privacy policy URL is accessible without login",
            "Privacy policy URL is not PDF",
            "Play Console support/contact field populated",
            "Support/contact mechanism matches `play_store/privacy_policy_ru.html`",
        ),
    ),
    (
        "Signing backup",
        "Back up the active upload keystore and credentials before Play upload, then record safe owner evidence.",
        (
            "play_store/play_console_post_upload_evidence_ru.md",
            "play_store/signing_backup_evidence_ru.md",
        ),
        ("./tools/check_signing_backup_inputs.py",),
        (
            "Active upload keystore backed up before AAB upload",
            "Owner-controlled backup evidence recorded without secrets",
            "Backup completed before Play upload",
            "Secure owner-controlled storage type chosen",
            "At least two owner-controlled secure copies exist",
            "Recovery tested without exposing secrets",
            "Responsible owner",
            "Backup date/time",
            "Backup record location in owner tracker or password manager",
        ),
    ),
    (
        "Play-generated artifact review",
        "Download or inspect Play-generated artifacts and prove package, label, version, icon, permission and native 16 KB page-size posture.",
        ("play_store/play_console_post_upload_evidence_ru.md",),
        ("./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>",),
        (
            "Play-generated APK package is `com.qgrid.mobile`",
            "Play-generated app label is `Линия 56`",
            "Play-generated icon matches `play_store/icon/play_icon_512.png`",
            "Play-generated version code/name match this release candidate",
            "Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions",
            "Play-generated native libraries support 16 KB page sizes",
            "Play-generated APK installed and launched on at least one Android device or emulator",
        ),
    ),
    (
        "Play Console forms",
        "Complete App content, ads, Data Safety, content rating, target audience and AI disclosure forms.",
        ("play_store/play_console_post_upload_evidence_ru.md",),
        ("no local command; complete the matching Play Console forms",),
        (
            "App access completed as no restricted access/login/account",
            "Ads declaration completed as no ads",
            "Data Safety completed as no user data collected or shared",
            "Content rating completed as Games / Puzzle posture",
            "Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path",
            "AI disclosure completed as no in-app generative AI features",
        ),
    ),
    (
        "Testing track and final review",
        "Finish required testing, review Play warnings/pre-launch results and inspect store preview crops.",
        ("play_store/play_console_post_upload_evidence_ru.md",),
        (
            "./tools/create_store_asset_review_sheet.py --write",
            "./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>",
        ),
        (
            "Internal testing upload completed",
            "Closed testing required for this account",
            "Closed testing status if required",
            "Pre-launch report result",
            "Reproducible crashes in pre-launch report",
            "Play policy warnings",
            "Store listing preview checked for damaging image crops",
        ),
    ),
)


class PublicationReadinessError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationReadinessError(message)


def read(path: Path) -> str:
    require(path.is_file(), f"missing file: {path.relative_to(ROOT).as_posix()}")
    return path.read_text(encoding="utf-8")


def strip_value(value: str) -> str:
    return value.strip().rstrip(".").strip()


def lower_value(value: str) -> str:
    return strip_value(value).strip("`").lower()


def is_pending(value: str) -> bool:
    return "not yet available locally" in value


def find_bullet_value(text: str, label: str, file_label: str) -> str:
    pattern = re.compile(rf"^- {re.escape(label)}: (?P<value>.+)$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        exact_bullet = f"- {label}."
        if exact_bullet in text:
            if "signing_backup_input_ok" in label:
                return "signing_backup_input_ok"
            return "yes"
    require(match is not None, f"{file_label} missing evidence line: {label}")
    return match.group("value").strip()


def expected_aab_sha256(upload_checksums: str) -> str:
    pattern = re.compile(
        r"\| `app/build/outputs/bundle/release/app-release\.aab` \| \d+ \| `(?P<sha>[0-9a-f]{64})` \|"
    )
    match = pattern.search(upload_checksums)
    require(match is not None, "upload checksums missing parseable AAB SHA-256 row")
    return match.group("sha")


def validate_no_forbidden_evidence(text: str, file_label: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in text, f"{file_label} must not record secret/private marker: {marker}")
    for pattern in FORBIDDEN_EVIDENCE_PATTERNS:
        require(
            re.search(pattern, text) is None,
            f"{file_label} must not record secret/private evidence matching pattern: {pattern}",
        )


def negative_status_markers(value: str) -> list[str]:
    normalized = lower_value(value)
    return [phrase for phrase in NEGATIVE_EVIDENCE_PHRASES if phrase in normalized]


def validate_yes(label: str, value: str, file_label: str) -> None:
    normalized = lower_value(value)
    negative = negative_status_markers(value)
    require(
        not negative,
        f"{file_label} value for {label} must be a positive confirmation without negative status markers: {value}",
    )
    require(
        normalized in POSITIVE_EVIDENCE_VALUES or normalized.startswith(("yes ", "yes,")),
        f"{file_label} has unexpected value for {label}: {value}",
    )


def validate_exact(label: str, value: str, file_label: str, *accepted: str) -> None:
    normalized = strip_value(value).strip("`")
    require(
        normalized in {item.strip("`") for item in accepted},
        f"{file_label} has unexpected value for {label}: {value}",
    )


def validate_contains_all(label: str, value: str, file_label: str, markers: tuple[str, ...]) -> None:
    lowered = value.lower()
    missing = [marker for marker in markers if marker.lower() not in lowered]
    require(not missing, f"{file_label} value for {label} is missing {missing}: {value}")


def validate_no_negative_markers(label: str, value: str, file_label: str) -> None:
    negative = negative_status_markers(value)
    require(
        not negative,
        f"{file_label} value for {label} must not include negative status markers: {value}",
    )


def normalized_public_https_url(label: str, value: str, file_label: str) -> str:
    cleaned = strip_value(value).strip("`")
    parsed = urlparse(cleaned)
    require(parsed.scheme == "https", f"{file_label} value for {label} must be HTTPS: {value}")
    require(bool(parsed.netloc), f"{file_label} value for {label} must include a host: {value}")
    require(parsed.username is None and parsed.password is None, f"{file_label} value for {label} must not include credentials: {value}")
    require(parsed.query == "", f"{file_label} value for {label} must not include query parameters: {value}")
    require(parsed.fragment == "", f"{file_label} value for {label} must not include a URL fragment: {value}")
    host = (parsed.hostname or "").lower()
    require(host not in {"localhost", "127.0.0.1", "::1"}, f"{file_label} value for {label} must be public: {value}")
    require(host not in PLACEHOLDER_PRIVACY_HOSTS, f"{file_label} value for {label} must not use a placeholder host: {value}")
    require(not host.endswith(".localhost"), f"{file_label} value for {label} must be public: {value}")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        require(not ip.is_private and not ip.is_loopback and not ip.is_link_local, f"{file_label} value for {label} must be public: {value}")
    require(not parsed.path.lower().endswith(".pdf"), f"{file_label} value for {label} must not be a PDF: {value}")
    netloc = host
    if parsed.port is not None:
        netloc = f"{host}:{parsed.port}"
    path = parsed.path or "/"
    return urlunparse(("https", netloc, path, "", parsed.query, ""))


def validate_public_https_url(label: str, value: str, file_label: str) -> None:
    normalized_public_https_url(label, value, file_label)


def validate_privacy_url_matches_recorded(argument_url: str, recorded_value: str, file_label: str) -> None:
    recorded_url = normalized_public_https_url("Public privacy policy URL", recorded_value, file_label)
    checked_url = normalized_public_https_url("--privacy-url", argument_url, "command line")
    require(
        checked_url == recorded_url,
        f"--privacy-url must match recorded Public privacy policy URL in {file_label}: {argument_url} != {recorded_url}",
    )


def validate_date_like(label: str, value: str, file_label: str) -> None:
    negative = negative_status_markers(value)
    require(
        not negative,
        f"{file_label} value for {label} must be a concrete date/time without negative status markers: {value}",
    )
    require(
        any(re.search(pattern, value) for pattern in FULL_DATE_PATTERNS),
        f"{file_label} value for {label} must include a full date such as 2026-06-06: {value}",
    )


def validate_non_empty(label: str, value: str, file_label: str) -> None:
    require(bool(strip_value(value)), f"{file_label} value for {label} must not be empty")
    negative = negative_status_markers(value)
    require(
        not negative,
        f"{file_label} value for {label} must not be pending, unknown or negative evidence: {value}",
    )


def validate_contains_0o600(label: str, value: str, file_label: str) -> None:
    validate_contains_all(label, value, file_label, ("0o600",))


def validate_post_upload_value(label: str, value: str, file_label: str, expected_sha: str) -> None:
    if label == "Uploaded package name":
        validate_exact(label, value, file_label, "com.qgrid.mobile")
    elif label == "Uploaded version code":
        validate_exact(label, value, file_label, "1")
    elif label == "Uploaded version name":
        validate_exact(label, value, file_label, "1.0.0")
    elif label == "Uploaded AAB SHA-256":
        validate_exact(label, value, file_label, expected_sha)
    elif label == "First release track used":
        normalized = lower_value(value)
        require(
            normalized in {"internal testing", "closed testing"},
            f"{file_label} value for {label} must be internal testing or closed testing, never direct production: {value}",
        )
    elif label == "Upload date/time":
        validate_date_like(label, value, file_label)
    elif label == "Public privacy policy URL":
        validate_public_https_url(label, value, file_label)
    elif label == "Privacy policy URL check command returned `privacy_policy_url_ok`":
        validate_exact(label, value, file_label, "privacy_policy_url_ok")
    elif label in {
        "Privacy policy URL is HTTPS",
        "Privacy policy URL is accessible without login",
        "Privacy policy URL is not PDF",
        "Play Console support/contact field populated",
        "Support/contact mechanism matches `play_store/privacy_policy_ru.html`",
        "Active upload keystore backed up before AAB upload",
        "Play-generated version code/name match this release candidate",
        "Play-generated APK installed and launched on at least one Android device or emulator",
        "App access completed as no restricted access/login/account",
        "Ads declaration completed as no ads",
        "Data Safety completed as no user data collected or shared",
        "Content rating completed as Games / Puzzle posture",
        "Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path",
        "AI disclosure completed as no in-app generative AI features",
        "Internal testing upload completed",
        "Store listing preview checked for damaging image crops",
    }:
        validate_yes(label, value, file_label)
    elif label == "Signing backup evidence file":
        validate_exact(label, value, file_label, "play_store/signing_backup_evidence_ru.md")
    elif label == "Signing backup input check command returned `signing_backup_input_ok`":
        normalized = lower_value(value)
        require(
            normalized == "signing_backup_input_ok" or "recorded locally" in normalized,
            f"{file_label} value for {label} must be signing_backup_input_ok or recorded locally: {value}",
        )
    elif label == "Owner-controlled backup evidence recorded without secrets":
        validate_yes(label, value, file_label)
        lowered = value.lower()
        require(
            "without secrets" in lowered or "without exposing secrets" in lowered,
            f"{file_label} value for {label} must explicitly say evidence was recorded without secrets: {value}",
        )
    elif label == "Play-generated APK package is `com.qgrid.mobile`":
        validate_exact(label, value, file_label, "com.qgrid.mobile")
    elif label == "Play-generated app label is `Линия 56`":
        validate_exact(label, value, file_label, "Линия 56")
    elif label == "Play-generated icon matches `play_store/icon/play_icon_512.png`":
        validate_yes(label, value, file_label)
        validate_contains_all(label, value, file_label, ("application icon", "round icon", "store icon", "pixel"))
    elif label == "Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions":
        validate_no_negative_markers(label, value, file_label)
        validate_contains_all(label, value, file_label, ("no INTERNET", "no ACCESS_NETWORK_STATE", "no dangerous"))
    elif label == "Play-generated native libraries support 16 KB page sizes":
        validate_no_negative_markers(label, value, file_label)
        validate_contains_all(label, value, file_label, ("16 KB", "16384"))
    elif label == "Closed testing required for this account":
        normalized = lower_value(value)
        require(normalized in {"yes", "no"}, f"{file_label} value for {label} must be yes or no: {value}")
    elif label == "Closed testing status if required":
        normalized = lower_value(value)
        require(
            normalized in {"not required for this account", "completed required closed testing"},
            f"{file_label} value for {label} must be not required or completed: {value}",
        )
    elif label == "Pre-launch report result":
        normalized = lower_value(value)
        require(
            normalized in {"passed", "no blocking issues", "no issues"},
            f"{file_label} value for {label} must indicate passed/no blocking issues: {value}",
        )
    elif label == "Reproducible crashes in pre-launch report":
        normalized = lower_value(value)
        require(normalized in {"none", "no", "no reproducible crashes"}, f"{file_label} value for {label} must be none/no: {value}")
    elif label == "Play policy warnings":
        normalized = lower_value(value)
        require(normalized in {"none", "no", "no warnings", "resolved"}, f"{file_label} value for {label} must be none/no/resolved: {value}")
    else:
        validate_non_empty(label, value, file_label)


def validate_closed_testing_consistency(post_upload: str, file_label: str) -> None:
    required_value = find_bullet_value(post_upload, "Closed testing required for this account", file_label)
    status_value = find_bullet_value(post_upload, "Closed testing status if required", file_label)
    if is_pending(required_value) or is_pending(status_value):
        return

    required = lower_value(required_value)
    status = lower_value(status_value)
    if required == "yes":
        require(
            status == "completed required closed testing",
            f"{file_label} closed testing is required but status is not completed: {status_value}",
        )
    elif required == "no":
        require(
            status == "not required for this account",
            f"{file_label} closed testing is not required but status says completed: {status_value}",
        )


def validate_signing_backup_value(label: str, value: str, file_label: str) -> None:
    if label == "Active upload keystore":
        validate_exact(label, value, file_label, "private/signing/qgrid-upload.p12")
    elif label == "Signing credentials file":
        validate_exact(label, value, file_label, "keystore.properties")
    elif label == "Active key alias":
        validate_exact(label, value, file_label, "qgrid_upload")
    elif label == "Public certificate reference":
        validate_exact(label, value, file_label, "play_store/signing_certificate_report.md")
    elif label == "Legacy ignored local key":
        validate_contains_all(label, value, file_label, ("private/signing/line56-upload.p12", "do not use", "do not upload"))
    elif label == "Command returned `signing_backup_input_ok`":
        validate_exact(label, value, file_label, "signing_backup_input_ok")
    elif label == "Active upload keystore exists and is owner-only":
        validate_contains_all(label, value, file_label, ("private/signing/qgrid-upload.p12", "0o600"))
    elif label == "`keystore.properties` exists and is owner-only":
        validate_contains_0o600(label, value, file_label)
    elif label == "`keystore.properties` points to `private/signing/qgrid-upload.p12`":
        validate_exact(label, value, file_label, "private/signing/qgrid-upload.p12")
    elif label == "`keystore.properties` uses key alias `qgrid_upload`":
        validate_exact(label, value, file_label, "qgrid_upload")
    elif label == "`storePassword` and `keyPassword` fields are present; values were not printed or recorded":
        validate_contains_all(label, value, file_label, ("present", "not printed", "not recorded"))
    elif label == "Legacy ignored local key exists and is owner-only":
        validate_contains_all(label, value, file_label, ("private/signing/line56-upload.p12", "0o600", "ignored", "not active"))
    elif label == "Backup completed before Play upload":
        validate_yes(label, value, file_label)
    elif label == "At least two owner-controlled secure copies exist":
        validate_yes(label, value, file_label)
        normalized = lower_value(value)
        require(
            re.search(r"\b(?:2|two)\b", normalized) is not None,
            f"{file_label} value for {label} must explicitly mention at least two secure copies: {value}",
        )
    elif label == "Recovery tested without exposing secrets":
        validate_yes(label, value, file_label)
        lowered = value.lower()
        require(
            "without exposing secrets" in lowered or "without secrets" in lowered,
            f"{file_label} value for {label} must explicitly say recovery was tested without exposing secrets: {value}",
        )
    elif label == "Secure owner-controlled storage type chosen":
        validate_non_empty(label, value, file_label)
    elif label == "Responsible owner":
        validate_non_empty(label, value, file_label)
    elif label == "Backup date/time":
        validate_date_like(label, value, file_label)
    elif label == "Backup record location in owner tracker or password manager":
        validate_non_empty(label, value, file_label)
    else:
        validate_non_empty(label, value, file_label)


def collect_evidence_status(
    text: str,
    labels: tuple[str, ...],
    file_label: str,
    *,
    expected_sha: str | None = None,
) -> list[str]:
    unresolved: list[str] = []
    validate_no_forbidden_evidence(text, file_label)
    for label in labels:
        value = find_bullet_value(text, label, file_label)
        if is_pending(value):
            unresolved.append(f"- {label}: {value}")
            continue
        if expected_sha is not None:
            validate_post_upload_value(label, value, file_label, expected_sha)
        else:
            validate_signing_backup_value(label, value, file_label)
    return unresolved


def verify_local_handoff_files() -> tuple[list[str], list[str]]:
    owner_inputs = read(OWNER_INPUTS)
    post_upload = read(POST_UPLOAD_EVIDENCE)
    signing_backup = read(SIGNING_BACKUP_EVIDENCE)
    upload_checksums = read(UPLOAD_CHECKSUMS)
    expected_sha = expected_aab_sha256(upload_checksums)

    for marker in [
        "publication is still blocked externally",
        "After hosting the privacy policy, run `./tools/check_privacy_policy_url.py --url <https-url>`",
        "The local release candidate is prepared and verifier-approved",
    ]:
        require(marker in owner_inputs, f"owner release inputs missing marker: {marker}")

    post_upload_unresolved = collect_evidence_status(
        post_upload,
        POST_UPLOAD_LABELS,
        "play_store/play_console_post_upload_evidence_ru.md",
        expected_sha=expected_sha,
    )
    validate_closed_testing_consistency(post_upload, "play_store/play_console_post_upload_evidence_ru.md")
    signing_backup_unresolved = collect_evidence_status(
        signing_backup,
        SIGNING_BACKUP_LABELS,
        "play_store/signing_backup_evidence_ru.md",
    )

    require("Command returned `signing_backup_input_ok`." in signing_backup, "signing backup local preflight marker is missing")
    require("app/build/outputs/bundle/release/app-release.aab" in upload_checksums, "upload checksums missing signed AAB row")
    require("play_store/icon/play_icon_512.png" in upload_checksums, "upload checksums missing Play icon row")

    return post_upload_unresolved, signing_backup_unresolved


def recorded_privacy_url_value() -> str | None:
    post_upload = read(POST_UPLOAD_EVIDENCE)
    value = find_bullet_value(post_upload, "Public privacy policy URL", "play_store/play_console_post_upload_evidence_ru.md")
    if is_pending(value):
        return None
    return value


def validate_privacy_url(url: str, *, recorded_value: str | None = None) -> None:
    checked_url = normalized_public_https_url("--privacy-url", url, "command line")
    if recorded_value is not None:
        validate_privacy_url_matches_recorded(url, recorded_value, "play_store/play_console_post_upload_evidence_ru.md")
    completed = subprocess.run(
        [str(PRIVACY_URL_CHECK), "--url", checked_url],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        raise PublicationReadinessError(completed.stdout.strip() or "privacy URL check failed")
    require("privacy_policy_url_ok" in completed.stdout, "privacy URL helper did not return privacy_policy_url_ok")


def unresolved_label(line: str) -> str:
    body = line[2:] if line.startswith("- ") else line
    return body.split(": ", 1)[0]


def print_owner_action_breakdown(unresolved: list[str]) -> None:
    unresolved_labels = {unresolved_label(line) for line in unresolved}
    print("Owner action breakdown")
    print("----------------------")
    if not unresolved_labels:
        print("- no unresolved owner action groups remain.")
        print()
        return

    grouped_labels: set[str] = set()
    for title, action, evidence_files, commands, labels in OWNER_ACTION_GROUPS:
        matching_labels = [label for label in labels if label in unresolved_labels]
        if not matching_labels:
            continue
        grouped_labels.update(matching_labels)
        print(f"- {title}: {len(matching_labels)} unresolved field(s).")
        print(f"  action: {action}")
        print(f"  evidence: {', '.join(evidence_files)}")
        for command in commands:
            print(f"  command: {command}")
        print(f"  fields: {', '.join(matching_labels)}")

    ungrouped = sorted(unresolved_labels - grouped_labels)
    if ungrouped:
        print(f"- Other evidence: {len(ungrouped)} unresolved field(s).")
        print(f"  evidence: {POST_UPLOAD_EVIDENCE.relative_to(ROOT).as_posix()}, {SIGNING_BACKUP_EVIDENCE.relative_to(ROOT).as_posix()}")
        print(f"  fields: {', '.join(ungrouped)}")
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print Line 56 publication readiness status.")
    parser.add_argument(
        "--privacy-url",
        help="Optional public HTTPS privacy policy URL to validate with check_privacy_policy_url.py.",
    )
    parser.add_argument(
        "--check-recorded-privacy-url",
        action="store_true",
        help="Validate the recorded Public privacy policy URL from play_store/play_console_post_upload_evidence_ru.md.",
    )
    parser.add_argument(
        "--require-production-ready",
        action="store_true",
        help="Exit non-zero unless external owner evidence has been recorded and the privacy URL validates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the checks this helper performs without reading external URL content.",
    )
    return parser.parse_args()


def print_status(
    post_upload_unresolved: list[str],
    signing_backup_unresolved: list[str],
    *,
    privacy_url_checked: bool,
    require_production_ready: bool,
) -> int:
    unresolved = post_upload_unresolved + signing_backup_unresolved
    print("Publication readiness")
    print("=====================")
    print("- Local release candidate: READY when `./tools/run_final_local_gate.py` returns `final_local_gate_ok`.")
    print("- Production rollout: READY only after owner-controlled external gates are recorded and verified.")
    print()
    print("Owner gates")
    print("-----------")
    if unresolved:
        print("Production rollout status: NOT READY")
        for line in unresolved:
            print(f"- unresolved: {line[2:]}")
    else:
        print("Production rollout status: external evidence recorded locally.")
    if privacy_url_checked:
        print("- public privacy URL check: privacy_policy_url_ok")
    else:
        print("- public privacy URL check: not run; use `--privacy-url <https-url>` after hosting.")
    print()
    print_owner_action_breakdown(unresolved)
    print("Required owner actions before production")
    print("----------------------------------------")
    print("- Enter the verified hosted privacy policy URL in Play Console.")
    print("- Populate Play Console support/contact fields used by the policy inquiry mechanism.")
    print("- Back up `private/signing/qgrid-upload.p12` and `keystore.properties` in secure owner-controlled storage.")
    print("- Complete Play Console App content, Data Safety, content rating, target audience and AI disclosure forms.")
    print("- Upload through testing tracks, review Play-generated artifacts and record safe evidence.")
    print()

    if require_production_ready and (unresolved or not privacy_url_checked):
        print("publication_readiness_blocked")
        return 1
    if unresolved or not privacy_url_checked:
        print("publication_readiness_local_ready_external_pending")
    else:
        print("publication_readiness_production_ready_owner_confirmed")
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run:
            print("Publication readiness dry run")
            print("=============================")
            print("- validate owner release inputs")
            print("- validate upload/post-upload/signing evidence handoff files")
            print("- validate exact recorded evidence values against package/version/checksum/privacy/signing expectations")
            print("- list owner-controlled external gates that remain `not yet available locally`")
            print("- group unresolved owner actions by evidence file and required command")
            print("- optionally validate public HTTPS privacy policy URL via `--privacy-url <https-url>`")
            print("- optionally validate recorded public HTTPS privacy policy URL via `--check-recorded-privacy-url`")
            print("- with `--require-production-ready`, fail while external owner gates remain unresolved")
            print("publication_readiness_dry_run_ok")
            return 0

        post_upload_unresolved, signing_backup_unresolved = verify_local_handoff_files()
        privacy_url_checked = False
        recorded_url = recorded_privacy_url_value()
        if args.check_recorded_privacy_url:
            require(recorded_url is not None, "recorded Public privacy policy URL is still pending")
            require(args.privacy_url is None, "use either --privacy-url or --check-recorded-privacy-url, not both")
            validate_privacy_url(recorded_url, recorded_value=recorded_url)
            privacy_url_checked = True
        elif args.privacy_url:
            validate_privacy_url(args.privacy_url, recorded_value=recorded_url)
            privacy_url_checked = True
        return print_status(
            post_upload_unresolved,
            signing_backup_unresolved,
            privacy_url_checked=privacy_url_checked,
            require_production_ready=args.require_production_ready,
        )
    except (OSError, PublicationReadinessError) as exc:
        print(f"publication_readiness_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
