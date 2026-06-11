#!/usr/bin/env python3
"""Verify a Play-generated APK or local release APK against the release identity.

Use this after Play Console creates downloadable APK artifacts from the uploaded
AAB, or locally against `app/build/outputs/apk/release/app-release.apk` as a
pre-upload sanity check. This does not replace installing and launching the
Play-generated APK on a device; it catches package, version and permission
regressions before rollout, including native-library 16 KB page-size alignment.
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PACKAGE = "com.qgrid.mobile"
EXPECTED_VERSION_CODE = "1"
EXPECTED_VERSION_NAME = "1.0.0"
EXPECTED_LABEL = "Линия 56"
EXPECTED_MIN_SDK = "24"
EXPECTED_TARGET_SDK = "36"
EXPECTED_ICON_SIZE = (512, 512)
REQUIRED_NATIVE_LOAD_ALIGNMENT = 16 * 1024

FORBIDDEN_PERMISSIONS = {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
    "android.permission.CAMERA",
    "android.permission.RECORD_AUDIO",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.READ_MEDIA_AUDIO",
    "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS",
    "android.permission.GET_ACCOUNTS",
    "android.permission.READ_CALENDAR",
    "android.permission.WRITE_CALENDAR",
    "android.permission.READ_PHONE_STATE",
    "android.permission.CALL_PHONE",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.SEND_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_SMS",
    "android.permission.BODY_SENSORS",
    "android.permission.POST_NOTIFICATIONS",
}

FORBIDDEN_ZIP_MARKERS = (
    "androidtest",
    "espresso",
    "junit",
    "ui-test",
    "test-manifest",
    "com/qgrid/mobile/debug",
)


class ApkReviewError(RuntimeError):
    pass


def project_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def sdk_dir() -> Path:
    local_properties = ROOT / "local.properties"
    if local_properties.is_file():
        for line in local_properties.read_text(encoding="utf-8").splitlines():
            if line.startswith("sdk.dir="):
                return Path(line.split("=", 1)[1]).expanduser()
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(env_name)
        if value:
            return Path(value).expanduser()
    raise ApkReviewError("Android SDK path not found; set local.properties sdk.dir or ANDROID_HOME.")


def find_aapt() -> Path:
    build_tools = sdk_dir() / "build-tools"
    if not build_tools.is_dir():
        raise ApkReviewError(f"Android build-tools directory not found: {build_tools}")
    candidates = sorted(build_tools.glob("*/aapt"), key=lambda item: item.parent.name)
    if not candidates:
        raise ApkReviewError(f"aapt not found under {build_tools}")
    return candidates[-1]


def run_aapt_badging(apk: Path) -> str:
    completed = subprocess.run(
        [str(find_aapt()), "dump", "badging", str(apk)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ApkReviewError(f"aapt dump badging failed: {completed.stderr.strip()}")
    return completed.stdout


def regex_value(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text)
    if match is None:
        raise ApkReviewError(f"Could not read {label} from APK badging output.")
    return match.group(1)


def permissions_from_badging(badging: str) -> list[str]:
    permissions: list[str] = []
    for line in badging.splitlines():
        if not line.startswith("uses-permission"):
            continue
        match = re.search(r"name='([^']+)'", line)
        if match:
            permissions.append(match.group(1))
    return permissions


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
        return None
    return struct.unpack(">II", data[16:24])


def elf_load_alignments(entry_name: str, data: bytes) -> list[int]:
    if data[:4] != b"\x7fELF":
        raise ApkReviewError(f"Native library is not an ELF file: {entry_name}")
    if len(data) < 64:
        raise ApkReviewError(f"Native library ELF header is truncated: {entry_name}")

    elf_class = data[4]
    endian = data[5]
    if endian not in {1, 2}:
        raise ApkReviewError(f"Native library has unsupported ELF endianness: {entry_name}")
    prefix = "<" if endian == 1 else ">"

    if elf_class == 2:
        e_phoff = struct.unpack_from(prefix + "Q", data, 32)[0]
        e_phentsize = struct.unpack_from(prefix + "H", data, 54)[0]
        e_phnum = struct.unpack_from(prefix + "H", data, 56)[0]
        align_offset = 48
        align_format = prefix + "Q"
    elif elf_class == 1:
        e_phoff = struct.unpack_from(prefix + "I", data, 28)[0]
        e_phentsize = struct.unpack_from(prefix + "H", data, 42)[0]
        e_phnum = struct.unpack_from(prefix + "H", data, 44)[0]
        align_offset = 28
        align_format = prefix + "I"
    else:
        raise ApkReviewError(f"Native library has unsupported ELF class: {entry_name}")

    if e_phnum <= 0:
        raise ApkReviewError(f"Native library has no ELF program headers: {entry_name}")
    if e_phentsize < align_offset + struct.calcsize(align_format):
        raise ApkReviewError(f"Native library program header is too small: {entry_name}")
    if e_phoff + e_phentsize * e_phnum > len(data):
        raise ApkReviewError(f"Native library program header table is truncated: {entry_name}")

    alignments: list[int] = []
    for index in range(e_phnum):
        offset = e_phoff + index * e_phentsize
        p_type = struct.unpack_from(prefix + "I", data, offset)[0]
        if p_type == 1:  # PT_LOAD
            alignments.append(struct.unpack_from(align_format, data, offset + align_offset)[0])
    if not alignments:
        raise ApkReviewError(f"Native library has no PT_LOAD program headers: {entry_name}")
    return alignments


def native_library_alignment_summary(apk: Path) -> tuple[list[str], int | None]:
    native_library_names: list[str] = []
    minimum_alignment: int | None = None
    with zipfile.ZipFile(apk) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if not info.filename.endswith(".so"):
                continue
            native_library_names.append(info.filename)
            for alignment in elf_load_alignments(info.filename, archive.read(info.filename)):
                if minimum_alignment is None or alignment < minimum_alignment:
                    minimum_alignment = alignment
    return native_library_names, minimum_alignment


def verify_native_library_alignment(apk: Path) -> tuple[list[str], int | None]:
    native_libraries, minimum_native_alignment = native_library_alignment_summary(apk)
    if minimum_native_alignment is not None and minimum_native_alignment < REQUIRED_NATIVE_LOAD_ALIGNMENT:
        raise ApkReviewError(
            f"APK native libraries must support 16 KB page sizes; minimum PT_LOAD alignment is {minimum_native_alignment}"
        )
    return native_libraries, minimum_native_alignment


def icon_candidates(apk: Path) -> list[str]:
    candidates: list[str] = []
    with zipfile.ZipFile(apk) as archive:
        for info in archive.infolist():
            lowered = info.filename.lower()
            for marker in FORBIDDEN_ZIP_MARKERS:
                if marker in lowered:
                    raise ApkReviewError(f"APK contains forbidden debug/test marker: {info.filename}")
            if not lowered.endswith(".png"):
                continue
            dimensions = png_dimensions(archive.read(info.filename))
            if dimensions == EXPECTED_ICON_SIZE:
                candidates.append(info.filename)
    return candidates


def verify_apk(apk: Path) -> dict[str, object]:
    if not apk.is_file():
        raise ApkReviewError(f"APK file not found: {apk}")
    if apk.suffix.lower() != ".apk":
        raise ApkReviewError(f"Expected an .apk file, got: {apk}")

    badging = run_aapt_badging(apk)
    package_name = regex_value(r"package: name='([^']+)'", badging, "package name")
    version_code = regex_value(r"versionCode='([^']+)'", badging, "versionCode")
    version_name = regex_value(r"versionName='([^']+)'", badging, "versionName")
    min_sdk = regex_value(r"sdkVersion:'([^']+)'", badging, "minSdk")
    target_sdk = regex_value(r"targetSdkVersion:'([^']+)'", badging, "targetSdk")
    label = regex_value(r"application-label:'([^']+)'", badging, "application label")
    icon_reference = regex_value(r"application: label='[^']*' icon='([^']*)'", badging, "application icon")

    expected_pairs = [
        ("package", package_name, EXPECTED_PACKAGE),
        ("versionCode", version_code, EXPECTED_VERSION_CODE),
        ("versionName", version_name, EXPECTED_VERSION_NAME),
        ("minSdk", min_sdk, EXPECTED_MIN_SDK),
        ("targetSdk", target_sdk, EXPECTED_TARGET_SDK),
        ("label", label, EXPECTED_LABEL),
    ]
    for label_name, actual, expected in expected_pairs:
        if actual != expected:
            raise ApkReviewError(f"APK {label_name} mismatch: {actual!r} != {expected!r}")

    if ".debug" in package_name or "-debug" in version_name:
        raise ApkReviewError("APK looks like a debug build.")
    if not icon_reference:
        raise ApkReviewError("APK has no application icon reference.")

    permissions = permissions_from_badging(badging)
    allowed_dynamic_permission = f"{EXPECTED_PACKAGE}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
    unexpected_permissions = [
        permission
        for permission in permissions
        if permission != allowed_dynamic_permission
    ]
    if unexpected_permissions:
        raise ApkReviewError(f"APK requests unexpected permissions: {', '.join(unexpected_permissions)}")
    forbidden_permissions = sorted(FORBIDDEN_PERMISSIONS.intersection(permissions))
    if forbidden_permissions:
        raise ApkReviewError(f"APK requests forbidden permissions: {', '.join(forbidden_permissions)}")

    icons = icon_candidates(apk)
    if not icons:
        raise ApkReviewError("APK does not contain a 512x512 PNG icon candidate.")

    native_libraries, minimum_native_alignment = verify_native_library_alignment(apk)

    return {
        "package": package_name,
        "versionCode": version_code,
        "versionName": version_name,
        "minSdk": min_sdk,
        "targetSdk": target_sdk,
        "label": label,
        "permissions": permissions,
        "iconReference": icon_reference,
        "iconCandidates": icons,
        "nativeLibraries": native_libraries,
        "minimumNativeLoadAlignment": minimum_native_alignment,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a Play-generated Line 56 APK artifact.")
    parser.add_argument("--apk", help="Path to the Play-generated APK, or a local release APK for sanity checking.")
    parser.add_argument("--dry-run", action="store_true", help="Print expected checks without requiring an APK file.")
    args = parser.parse_args()
    if args.dry_run and args.apk:
        parser.error("--dry-run and --apk are mutually exclusive")
    if not args.dry_run and not args.apk:
        parser.error("Provide --apk <path> or --dry-run")
    return args


def main() -> int:
    args = parse_args()
    try:
        if args.dry_run:
            print("Play-generated APK verification dry run")
            print("=======================================")
            print(f"- expected package: {EXPECTED_PACKAGE}")
            print(f"- expected versionCode: {EXPECTED_VERSION_CODE}")
            print(f"- expected versionName: {EXPECTED_VERSION_NAME}")
            print(f"- expected label: {EXPECTED_LABEL}")
            print(f"- expected minSdk/targetSdk: {EXPECTED_MIN_SDK}/{EXPECTED_TARGET_SDK}")
            print("- required permissions posture: no INTERNET, no ACCESS_NETWORK_STATE and no dangerous runtime permissions")
            print("- required artifact posture: no debug package, no androidTest/JUnit/Espresso/test leakage")
            print("- required native posture: native libraries, when present, have PT_LOAD alignment >= 16384 bytes for 16 KB page sizes")
            print()
            print("play_generated_apk_verify_dry_run_ok")
            return 0

        apk = project_path(args.apk)
        result = verify_apk(apk)
        print("Play-generated APK verification")
        print("===============================")
        print(f"- apk: {apk.relative_to(ROOT) if apk.is_relative_to(ROOT) else apk}")
        print(f"- package: {result['package']}")
        print(f"- versionCode: {result['versionCode']}")
        print(f"- versionName: {result['versionName']}")
        print(f"- label: {result['label']}")
        print(f"- minSdk/targetSdk: {result['minSdk']}/{result['targetSdk']}")
        permissions = result["permissions"]
        print(f"- permissions: {', '.join(permissions) if permissions else 'none'}")
        print(f"- application icon reference: {result['iconReference']}")
        print(f"- 512x512 icon candidates: {', '.join(result['iconCandidates'])}")
        native_libraries = result["nativeLibraries"]
        minimum_native_alignment = result["minimumNativeLoadAlignment"]
        if native_libraries:
            print(f"- native libraries: {len(native_libraries)} checked; minimum PT_LOAD alignment: {minimum_native_alignment} bytes")
        else:
            print("- native libraries: none")
        print()
        print("play_generated_apk_verify_ok")
        return 0
    except (ApkReviewError, OSError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        print(f"play_generated_apk_verify_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
