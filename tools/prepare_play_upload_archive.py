#!/usr/bin/env python3
"""Prepare a safe owner handoff archive for the Google Play upload packet.

The archive is generated under build/ and is not a Play upload artifact itself.
Unpack it on upload day and use the exact AAB, icon, feature graphic and
screenshots inside it, plus the included handoff notes.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKSUMS_PATH = ROOT / "play_store/upload_checksums.md"
MANIFEST_PATH = ROOT / "play_store/upload_manifest.md"
DEFAULT_OUTPUT = ROOT / "build/play_upload/line56_v1_google_play_upload_packet.zip"
ARCHIVE_ROOT = "line56_v1_google_play_upload_packet"
ZIP_TIMESTAMP = (2026, 6, 6, 0, 0, 0)

FORBIDDEN_SOURCE_PATH_MARKERS = (
    "keystore.properties",
    "local.properties",
    "private/signing",
    "app-debug.apk",
    "androidTest",
    ".apks",
    ".idsig",
)

FORBIDDEN_ARCHIVE_NAME_MARKERS = (
    "keystore.properties",
    "local.properties",
    "private/signing",
    "app-debug.apk",
    "androidTest",
    ".apks",
    ".idsig",
    "source_assets",
    "archive/",
    "store_asset_review_sheet",
)

SCREENSHOT_NAMES = (
    "01_onboarding.png",
    "02_home.png",
    "03_game_start.png",
    "04_game_line.png",
    "05_settings.png",
)

REQUIRED_UPLOAD_PATHS = (
    "app/build/outputs/bundle/release/app-release.aab",
    "play_store/icon/play_icon_512.png",
    "play_store/feature_graphic.png",
    *[f"play_store/screenshots/phone/{name}" for name in SCREENSHOT_NAMES],
    *[f"play_store/screenshots/tablet/{name}" for name in SCREENSHOT_NAMES],
)

HANDOFF_FILES = (
    "play_store/upload_manifest.md",
    "play_store/upload_checksums.md",
    "play_store/upload_runbook_ru.md",
    "play_store/play_console_submission_ru.md",
    "play_store/app_content_answers_ru.md",
    "play_store/data_safety_ru.md",
    "play_store/content_rating_notes.md",
    "play_store/owner_release_inputs.md",
    "play_store/publication_readiness_owner_actions_ru.md",
    "play_store/play_console_post_upload_evidence_ru.md",
    "play_store/signing_backup_evidence_ru.md",
    "play_store/signing_certificate_report.md",
    "play_store/privacy_policy_ru.md",
    "play_store/privacy_policy_ru.html",
    "play_store/privacy_policy_hosting_checklist.md",
    "play_store/asset_alt_text_ru.md",
)


class ArchiveError(RuntimeError):
    pass


def project_path(relative_path: str, root: Path = ROOT, label: str = "source") -> Path:
    if not relative_path or "\\" in relative_path:
        raise ArchiveError(f"Unsafe {label} path: {relative_path}")
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ArchiveError(f"Unsafe {label} path: {relative_path}")
    return root / path


def parse_byte_count(value: str, line: str) -> int:
    if not value.isdigit():
        raise ArchiveError(f"Bad upload checksum byte count: {value} in row: {line}")
    return int(value)


def require_sha256(value: str, line: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ArchiveError(f"Bad upload checksum SHA-256: {value} in row: {line}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum_rows(checksums_path: Path = CHECKSUMS_PATH) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    seen_paths: set[str] = set()
    for line in checksums_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 3:
            raise ArchiveError(f"Bad checksum row: {line}")
        path = parts[0].strip("`")
        if path in seen_paths:
            raise ArchiveError(f"Duplicate upload checksum row: {path}")
        seen_paths.add(path)
        byte_count = parse_byte_count(parts[1], line)
        checksum = parts[2].strip("`")
        require_sha256(checksum, line)
        rows.append((path, byte_count, checksum))
    if not rows:
        raise ArchiveError("No upload checksum rows found.")
    return rows


def archive_upload_path(relative_path: str) -> str:
    project_path(relative_path, label="upload archive")
    source = Path(relative_path)
    name = source.name
    if relative_path.endswith(".aab"):
        return f"{ARCHIVE_ROOT}/01_app_bundle/{name}"
    if relative_path == "play_store/icon/play_icon_512.png":
        return f"{ARCHIVE_ROOT}/02_store_icon/{name}"
    if relative_path == "play_store/feature_graphic.png":
        return f"{ARCHIVE_ROOT}/03_feature_graphic/{name}"
    if "/screenshots/phone/" in relative_path:
        return f"{ARCHIVE_ROOT}/04_phone_screenshots/{name}"
    if "/screenshots/tablet/" in relative_path:
        return f"{ARCHIVE_ROOT}/05_large_tablet_screenshots/{name}"
    return f"{ARCHIVE_ROOT}/upload/{name}"


def archive_handoff_path(relative_path: str) -> str:
    project_path(relative_path, label="handoff archive")
    return f"{ARCHIVE_ROOT}/_owner_handoff/{Path(relative_path).name}"


def validate_upload_rows(
    rows: list[tuple[str, int, str]],
    manifest_path: Path = MANIFEST_PATH,
    root: Path = ROOT,
) -> None:
    manifest = manifest_path.read_text(encoding="utf-8")
    for relative_path, expected_size, expected_sha in rows:
        path = project_path(relative_path, root=root, label="upload source")
        lowered = relative_path.lower()
        for marker in FORBIDDEN_SOURCE_PATH_MARKERS:
            if marker.lower() in lowered:
                raise ArchiveError(f"Forbidden upload source path: {relative_path}")
        if relative_path not in manifest:
            raise ArchiveError(f"Upload source path missing from upload_manifest.md: {relative_path}")
        if not path.is_file():
            raise ArchiveError(f"Upload source is missing: {relative_path}")
        if path.stat().st_size != expected_size:
            raise ArchiveError(f"Size mismatch for {relative_path}: {path.stat().st_size} != {expected_size}")
        actual_sha = sha256(path)
        if actual_sha != expected_sha:
            raise ArchiveError(f"SHA-256 mismatch for {relative_path}: {actual_sha} != {expected_sha}")


def verify_required_upload_paths(rows: list[tuple[str, int, str]]) -> None:
    paths = [path for path, _, _ in rows]
    expected_paths = set(REQUIRED_UPLOAD_PATHS)
    actual_paths = set(paths)
    missing = sorted(expected_paths - actual_paths)
    unexpected = sorted(actual_paths - expected_paths)
    if missing:
        raise ArchiveError(f"Upload checksum manifest missing required archive paths: {', '.join(missing)}")
    if unexpected:
        raise ArchiveError(f"Upload checksum manifest contains unexpected archive paths: {', '.join(unexpected)}")
    if tuple(paths) != REQUIRED_UPLOAD_PATHS:
        raise ArchiveError("Upload checksum manifest path order must match the Play upload archive order.")


def validate_handoff_files(handoff_files: tuple[str, ...] = HANDOFF_FILES, root: Path = ROOT) -> None:
    for relative_path in handoff_files:
        path = project_path(relative_path, root=root, label="handoff")
        if not path.is_file():
            raise ArchiveError(f"Handoff file is missing: {relative_path}")


def planned_archive_entries(rows: list[tuple[str, int, str]], handoff_files: tuple[str, ...] = HANDOFF_FILES) -> tuple[str, ...]:
    entries = [f"{ARCHIVE_ROOT}/README_UPLOAD_PACKET.txt"]
    entries.extend(archive_upload_path(relative_path) for relative_path, _, _ in rows)
    entries.extend(archive_handoff_path(relative_path) for relative_path in handoff_files)

    seen: set[str] = set()
    for entry in entries:
        if entry in seen:
            raise ArchiveError(f"Duplicate archive entry: {entry}")
        seen.add(entry)
        lowered = entry.lower()
        for marker in FORBIDDEN_ARCHIVE_NAME_MARKERS:
            if marker.lower() in lowered:
                raise ArchiveError(f"Forbidden archive entry path: {entry}")
    return tuple(entries)


def readme_text(rows: list[tuple[str, int, str]]) -> str:
    upload_lines = "\n".join(
        f"- {archive_upload_path(relative_path)} ({byte_count} bytes, sha256 {checksum})"
        for relative_path, byte_count, checksum in rows
    )
    return (
        "Line 56 Google Play upload packet\n"
        "=================================\n\n"
        "This ZIP is an owner handoff bundle, not a Play Console upload artifact.\n"
        "Unpack it and upload only the individual AAB, icon, feature graphic and screenshots listed below.\n\n"
        "Upload files\n"
        "------------\n"
        f"{upload_lines}\n\n"
        "Owner handoff files\n"
        "-------------------\n"
        "- _owner_handoff/upload_manifest.md lists the exact files and the Do Not Upload set.\n"
        "- _owner_handoff/upload_runbook_ru.md gives the upload-day sequence.\n"
        "- _owner_handoff/play_console_submission_ru.md contains copy-ready Play Console text.\n"
        "- _owner_handoff/publication_readiness_owner_actions_ru.md groups external owner actions and evidence fields.\n"
        "- _owner_handoff/signing_backup_evidence_ru.md gives the safe signing-backup evidence template.\n"
        "- _owner_handoff/signing_certificate_report.md documents the public upload certificate fingerprints.\n"
        "- _owner_handoff/privacy_policy_ru.html must be hosted at a public HTTPS URL before production.\n\n"
        "Do not upload this ZIP as a whole, generated APKs, signing files, local.properties or source/rejected assets.\n"
    )


def zip_write_file(archive: zipfile.ZipFile, source: Path, archive_name: str) -> None:
    info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, source.read_bytes())


def zip_write_text(archive: zipfile.ZipFile, archive_name: str, text: str) -> None:
    info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, text.encode("utf-8"))


def write_archive(output: Path, rows: list[tuple[str, int, str]], handoff_files: tuple[str, ...] = HANDOFF_FILES) -> None:
    verify_required_upload_paths(rows)
    planned_archive_entries(rows, handoff_files)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        zip_write_text(archive, f"{ARCHIVE_ROOT}/README_UPLOAD_PACKET.txt", readme_text(rows))
        for relative_path, _, _ in rows:
            zip_write_file(archive, project_path(relative_path), archive_upload_path(relative_path))
        for relative_path in handoff_files:
            zip_write_file(archive, project_path(relative_path), archive_handoff_path(relative_path))


def verify_existing_archive(output: Path, rows: list[tuple[str, int, str]], handoff_files: tuple[str, ...] = HANDOFF_FILES) -> tuple[str, ...]:
    verify_required_upload_paths(rows)
    expected_entries = planned_archive_entries(rows, handoff_files)
    if not output.is_file():
        raise ArchiveError(f"Generated Play upload archive is missing: {output}")
    if output.stat().st_size >= 10 * 1024 * 1024:
        raise ArchiveError(f"Generated Play upload archive is unexpectedly large: {output.stat().st_size} bytes")

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ArchiveError("Generated Play upload archive contains duplicate entries")
        actual_entries = set(names)
        expected_entry_set = set(expected_entries)
        missing = sorted(expected_entry_set - actual_entries)
        unexpected = sorted(actual_entries - expected_entry_set)
        if missing or unexpected:
            raise ArchiveError(f"Generated Play upload archive entry mismatch; missing={missing}; unexpected={unexpected}")

        for info in archive.infolist():
            if info.date_time != ZIP_TIMESTAMP:
                raise ArchiveError(f"Generated Play upload archive entry timestamp drifted: {info.filename}")
            if info.external_attr != 0o644 << 16:
                raise ArchiveError(f"Generated Play upload archive entry mode drifted: {info.filename}")
            lowered = info.filename.lower()
            for marker in FORBIDDEN_ARCHIVE_NAME_MARKERS:
                if marker.lower() in lowered:
                    raise ArchiveError(f"Forbidden archive entry path: {info.filename}")

        for relative_path, expected_size, expected_sha in rows:
            entry = archive_upload_path(relative_path)
            data = archive.read(entry)
            source_data = project_path(relative_path).read_bytes()
            if data != source_data:
                raise ArchiveError(f"Generated Play upload archive entry is stale: {entry}")
            if len(data) != expected_size:
                raise ArchiveError(f"Generated Play upload archive byte mismatch for {entry}: {len(data)} != {expected_size}")
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != expected_sha:
                raise ArchiveError(f"Generated Play upload archive SHA-256 mismatch for {entry}: {actual_sha} != {expected_sha}")

        for relative_path in handoff_files:
            entry = archive_handoff_path(relative_path)
            if archive.read(entry) != project_path(relative_path).read_bytes():
                raise ArchiveError(f"Generated Play upload archive handoff file is stale: {entry}")

        readme_entry = f"{ARCHIVE_ROOT}/README_UPLOAD_PACKET.txt"
        readme = archive.read(readme_entry).decode("utf-8")
        if readme != readme_text(rows):
            raise ArchiveError(f"Generated Play upload archive README is stale: {readme_entry}")

    return expected_entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the Line 56 Google Play upload packet archive.")
    parser.add_argument("--dry-run", action="store_true", help="Verify and print the archive contents without writing a ZIP.")
    parser.add_argument("--verify-existing", action="store_true", help="Verify the existing ZIP exactly matches current upload assets and handoff notes.")
    parser.add_argument("--write", action="store_true", help="Write the ZIP archive under build/play_upload or --output.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output ZIP path for --write or --verify-existing.")
    args = parser.parse_args()
    selected_modes = sum(1 for enabled in (args.dry_run, args.verify_existing, args.write) if enabled)
    if selected_modes > 1:
        parser.error("--dry-run, --verify-existing and --write are mutually exclusive")
    if selected_modes == 0:
        args.dry_run = True
    return args


def main() -> int:
    args = parse_args()
    try:
        rows = parse_checksum_rows()
        verify_required_upload_paths(rows)
        validate_upload_rows(rows)
        validate_handoff_files()
        entries = planned_archive_entries(rows)
        output = args.output if args.output.is_absolute() else ROOT / args.output
        if args.write:
            write_archive(output, rows)
            print("Google Play upload archive")
            print("==========================")
            print(f"- archive: {output.relative_to(ROOT)}")
            print(f"- bytes: {output.stat().st_size}")
            print(f"- sha256: {sha256(output)}")
            print("- contains:")
        elif args.verify_existing:
            entries = verify_existing_archive(output, rows)
            print("Google Play upload archive existing verification")
            print("================================================")
            print(f"- archive: {output.relative_to(ROOT)}")
            print(f"- bytes: {output.stat().st_size}")
            print(f"- sha256: {sha256(output)}")
            print("- verified contents:")
        else:
            print("Google Play upload archive dry run")
            print("==================================")
            print(f"- planned archive: {output.relative_to(ROOT)}")
            print("- would contain:")

        for entry in entries:
            print(f"  - {entry}")
        print()
        if args.write:
            print("play_upload_archive_ok")
        elif args.verify_existing:
            print("play_upload_archive_existing_ok")
        else:
            print("play_upload_archive_dry_run_ok")
        return 0
    except (ArchiveError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"play_upload_archive_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
