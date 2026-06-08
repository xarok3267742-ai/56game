#!/usr/bin/env python3
"""Print the Google Play upload packet and verify upload checksums.

This helper is intentionally read-only. It does not build, copy or package
artifacts; it only verifies the current files listed in upload_checksums.md and
prints the exact assets that should be uploaded to Play Console.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKSUMS_PATH = ROOT / "play_store/upload_checksums.md"
MANIFEST_PATH = ROOT / "play_store/upload_manifest.md"

FORBIDDEN_UPLOAD_MARKERS = (
    "keystore.properties",
    "local.properties",
    "private/signing",
    "app-debug.apk",
    "androidTest",
    ".apks",
    ".idsig",
)

SECTION_LABELS = {
    "app/build/outputs/bundle/release/app-release.aab": "App bundle",
    "play_store/icon/play_icon_512.png": "Store icon",
    "play_store/feature_graphic.png": "Feature graphic",
}

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


class UploadPacketError(RuntimeError):
    pass


def require_safe_relative_path(path: str) -> None:
    if not path or "\\" in path:
        raise UploadPacketError(f"Unsafe upload checksum path: {path}")
    parsed = Path(path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise UploadPacketError(f"Unsafe upload checksum path: {path}")


def parse_byte_count(value: str, line: str) -> int:
    if not value.isdigit():
        raise UploadPacketError(f"Bad upload checksum byte count: {value} in row: {line}")
    return int(value)


def require_sha256(value: str, line: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise UploadPacketError(f"Bad upload checksum SHA-256: {value} in row: {line}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum_rows(checksums_path: Path = CHECKSUMS_PATH) -> list[tuple[str, int, str]]:
    text = checksums_path.read_text(encoding="utf-8")
    rows: list[tuple[str, int, str]] = []
    seen_paths: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) != 3:
            raise UploadPacketError(f"Bad checksum row: {line}")
        path = parts[0].strip("`")
        require_safe_relative_path(path)
        if path in seen_paths:
            raise UploadPacketError(f"Duplicate upload checksum row: {path}")
        seen_paths.add(path)
        byte_count = parse_byte_count(parts[1], line)
        checksum = parts[2].strip("`")
        require_sha256(checksum, line)
        rows.append((path, byte_count, checksum))
    if not rows:
        raise UploadPacketError("No upload checksum rows found.")
    return rows


def do_not_upload_entries() -> list[str]:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    match = re.search(r"## Do Not Upload\s*(.*?)\n## ", text, re.S)
    if not match:
        raise UploadPacketError("Do Not Upload section is missing from upload_manifest.md.")
    entries: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            entries.append(stripped[2:])
    if not entries:
        raise UploadPacketError("Do Not Upload section has no entries.")
    return entries


def verify_required_upload_paths(rows: list[tuple[str, int, str]]) -> None:
    paths = [path for path, _, _ in rows]
    expected_paths = set(REQUIRED_UPLOAD_PATHS)
    actual_paths = set(paths)
    missing = sorted(expected_paths - actual_paths)
    unexpected = sorted(actual_paths - expected_paths)
    if missing:
        raise UploadPacketError(f"Upload checksum manifest missing required upload paths: {', '.join(missing)}")
    if unexpected:
        raise UploadPacketError(f"Upload checksum manifest contains unexpected upload paths: {', '.join(unexpected)}")
    if tuple(paths) != REQUIRED_UPLOAD_PATHS:
        raise UploadPacketError("Upload checksum manifest path order must match the Play upload packet order.")


def verify_rows(rows: list[tuple[str, int, str]]) -> None:
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    for relative_path, expected_size, expected_sha in rows:
        lowered = relative_path.lower()
        for marker in FORBIDDEN_UPLOAD_MARKERS:
            if marker.lower() in lowered:
                raise UploadPacketError(f"Forbidden file appears in upload checksums: {relative_path}")
        if relative_path not in manifest:
            raise UploadPacketError(f"Upload checksum path missing from upload_manifest.md: {relative_path}")

        path = ROOT / relative_path
        if not path.is_file():
            raise UploadPacketError(f"Upload artifact is missing: {relative_path}")
        actual_size = path.stat().st_size
        if actual_size != expected_size:
            raise UploadPacketError(f"Size mismatch for {relative_path}: {actual_size} != {expected_size}")
        actual_sha = sha256(path)
        if actual_sha != expected_sha:
            raise UploadPacketError(f"SHA-256 mismatch for {relative_path}: {actual_sha} != {expected_sha}")


def label_for(path: str) -> str:
    if path in SECTION_LABELS:
        return SECTION_LABELS[path]
    if "/screenshots/phone/" in path:
        return "Phone screenshot"
    if "/screenshots/tablet/" in path:
        return "Large/tablet screenshot"
    return "Upload asset"


def main() -> int:
    try:
        rows = parse_checksum_rows()
        verify_required_upload_paths(rows)
        verify_rows(rows)
        blocked = do_not_upload_entries()
    except UploadPacketError as exc:
        print(f"upload_packet_error: {exc}", file=sys.stderr)
        return 1

    print("Google Play upload packet")
    print("=========================")
    for relative_path, byte_count, checksum in rows:
        print(f"- {label_for(relative_path)}: {relative_path}")
        print(f"  bytes: {byte_count}")
        print(f"  sha256: {checksum}")

    print()
    print("Do not upload")
    print("-------------")
    for entry in blocked:
        print(f"- {entry}")

    print()
    print("upload_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
