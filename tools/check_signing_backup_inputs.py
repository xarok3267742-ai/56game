#!/usr/bin/env python3
"""Check local signing inputs before the owner makes a secure backup.

This helper is intentionally read-only and never prints password values. It
verifies that the ignored local signing files exist, are owner-only, and point
to the active neutral upload key for this release candidate.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_KEYSTORE = ROOT / "private/signing/qgrid-upload.p12"
LEGACY_KEYSTORE = ROOT / "private/signing/line56-upload.p12"
KEYSTORE_PROPERTIES = ROOT / "keystore.properties"
EXPECTED_ALIAS = "qgrid_upload"


class SigningBackupInputError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SigningBackupInputError(message)


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def check_owner_only_file(path: Path, label: str) -> int:
    require(path.is_file(), f"{label} is missing: {relative(path)}")
    mode = path.stat().st_mode & 0o777
    require(mode & 0o077 == 0, f"{relative(path)} must not be group/world readable or writable")
    return mode


def parse_properties(path: Path) -> dict[str, str]:
    properties: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        properties[key.strip()] = value.strip().replace("\\:", ":")
    return properties


def resolve_store_file(value: str) -> Path:
    store_path = Path(value).expanduser()
    if not store_path.is_absolute():
        store_path = ROOT / store_path
    return store_path.resolve()


def validate_properties(properties: dict[str, str]) -> str:
    for key in ("storeFile", "storePassword", "keyAlias", "keyPassword"):
        require(key in properties and bool(properties[key]), f"keystore.properties must contain non-empty {key}")

    store_file = properties["storeFile"]
    resolved_store_file = resolve_store_file(store_file)
    require(
        resolved_store_file == ACTIVE_KEYSTORE.resolve(),
        "keystore.properties storeFile must point to private/signing/qgrid-upload.p12",
    )
    require("line56" not in store_file.lower(), "keystore.properties must not point to the legacy obvious signing file")
    require(properties["keyAlias"] == EXPECTED_ALIAS, f"keystore.properties must use keyAlias={EXPECTED_ALIAS}")
    return store_file


def main() -> int:
    try:
        active_mode = check_owner_only_file(ACTIVE_KEYSTORE, "active upload keystore")
        properties_mode = check_owner_only_file(KEYSTORE_PROPERTIES, "keystore properties")
        properties = parse_properties(KEYSTORE_PROPERTIES)
        validate_properties(properties)

        print("signing_backup_input_check")
        print(f"- active upload keystore: {relative(ACTIVE_KEYSTORE)} (mode {active_mode:#04o})")
        print(
            f"- signing properties: {relative(KEYSTORE_PROPERTIES)} "
            f"(mode {properties_mode:#04o}; storePassword/keyPassword present, values hidden)"
        )
        print(f"- store file target: {relative(ACTIVE_KEYSTORE)}")
        print(f"- key alias: {EXPECTED_ALIAS}")
        if LEGACY_KEYSTORE.exists():
            legacy_mode = check_owner_only_file(LEGACY_KEYSTORE, "legacy signing file")
            print(f"- legacy signing file: {relative(LEGACY_KEYSTORE)} (mode {legacy_mode:#04o}; ignored, not active)")
        print("signing_backup_input_ok")
    except (OSError, SigningBackupInputError) as exc:
        print(f"signing_backup_input_error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
