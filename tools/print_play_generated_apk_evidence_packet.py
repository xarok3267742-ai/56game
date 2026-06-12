#!/usr/bin/env python3
"""Print safe Play-generated APK review evidence lines for the owner.

This helper is intentionally read-only. It verifies the supplied APK through
`tools/verify_play_generated_apk.py`, then prints copy-ready evidence lines for
`play_store/play_console_post_upload_evidence_ru.md`. It requires explicit
owner confirmation that the APK came from Play Console and that it was installed
and launched on an Android device or emulator before printing real evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION_EVIDENCE = "play_store/play_console_post_upload_evidence_ru.md"
VERIFY_HELPER = ROOT / "tools/verify_play_generated_apk.py"
LAUNCH_DEVICE = "device"
LAUNCH_EMULATOR = "emulator"

FORBIDDEN_EVIDENCE_MARKERS = (
    "storePassword=",
    "keyPassword=",
    "BEGIN PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "AIza",
    "ya29.",
    "Bearer ",
)


class PlayGeneratedApkEvidencePacketError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlayGeneratedApkEvidencePacketError(message)


def project_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def validate_no_forbidden_evidence(value: str) -> None:
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        require(marker not in value, f"Play-generated APK evidence must not contain forbidden marker: {marker}")
    require(
        re.search(r"(?im)\b(?:password|token|secret|api[_-]?key)\s*[:=]\s*\S+", value) is None,
        "Play-generated APK evidence must not contain password, token, secret or API key assignments",
    )
    require(
        re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", value) is None,
        "Play-generated APK evidence must not contain email addresses",
    )
    require(
        re.search(r"https?://|www\.", value, re.I) is None,
        "Play-generated APK evidence must not contain URLs or private links",
    )


def load_verifier_module():
    spec = importlib.util.spec_from_file_location("line56_play_generated_apk_verifier", VERIFY_HELPER)
    require(spec is not None and spec.loader is not None, "could not load tools/verify_play_generated_apk.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def launch_evidence_text(launch_target: str) -> str:
    if launch_target == LAUNCH_DEVICE:
        return "downloaded Play-generated APK was installed and launched on an Android device."
    if launch_target == LAUNCH_EMULATOR:
        return "downloaded Play-generated APK was installed and launched on an Android emulator."
    raise PlayGeneratedApkEvidencePacketError(f"unknown launch target: {launch_target}")


def native_evidence_text(result: dict[str, object]) -> str:
    native_libraries = result["nativeLibraries"]
    if not native_libraries:
        return (
            "verified 16 KB page-size posture: no native libraries are packaged; "
            "extractNativeLibs=false."
        )
    count = len(native_libraries)
    return (
        f"verified 16 KB page-size support: {count} native libraries checked, "
        f"minimum PT_LOAD alignment {result['minimumNativeLoadAlignment']} bytes; "
        f"native APK packaging verified: {count} uncompressed, ZIP-aligned native libraries, "
        f"minimum ZIP data alignment {result['minimumNativeZipAlignment']} bytes, "
        "extractNativeLibs=false."
    )


def evidence_lines(result: dict[str, object], launch_target: str) -> list[str]:
    signature = result["signature"]
    lines = [
        f"- Play-generated APK package is `com.qgrid.mobile`: {result['package']}.",
        (
            "- Play-generated APK signature verifies and certificate SHA-256 recorded: "
            f"verified; signer certificate SHA-256 {signature['certificateSha256']}."
        ),
        f"- Play-generated app label is `Линия 56`: {result['label']}.",
        (
            "- Play-generated icon matches `play_store/icon/play_icon_512.png`: "
            "yes, store icon pixel match verified; application icon linked store icon pixel match "
            "and round icon linked store icon pixel match verified."
        ),
        (
            "- Play-generated version code/name match this release candidate: "
            f"verified versionCode {result['versionCode']} and versionName {result['versionName']}."
        ),
        (
            "- Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` "
            "and no dangerous runtime permissions: no INTERNET, no ACCESS_NETWORK_STATE and no dangerous "
            "runtime permissions; only the expected dynamic receiver permission is present."
        ),
        (
            "- Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest: "
            f"allowBackup=false and no debuggable release manifest; debuggable: {result['debuggable']}."
        ),
        f"- Play-generated native libraries support 16 KB page sizes: {native_evidence_text(result)}",
        (
            "- Play-generated APK installed and launched on at least one Android device or emulator: "
            f"{launch_evidence_text(launch_target)}"
        ),
    ]
    for line in lines:
        validate_no_forbidden_evidence(line)
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print safe Play-generated APK review evidence lines.")
    parser.add_argument("--apk", help="Path to a downloaded Play-generated APK artifact.")
    parser.add_argument(
        "--confirm-play-generated",
        action="store_true",
        help="Confirm the APK was downloaded/generated by Play Console from this uploaded release.",
    )
    launch_group = parser.add_mutually_exclusive_group()
    launch_group.add_argument(
        "--installed-launched-on-device",
        action="store_true",
        help="Confirm the downloaded Play-generated APK was installed and launched on an Android device.",
    )
    launch_group.add_argument(
        "--installed-launched-on-emulator",
        action="store_true",
        help="Confirm the downloaded Play-generated APK was installed and launched on an Android emulator.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print expected owner steps without requiring a Play-generated APK.",
    )
    args = parser.parse_args()
    if args.dry_run and (args.apk or args.confirm_play_generated or args.installed_launched_on_device or args.installed_launched_on_emulator):
        parser.error("--dry-run cannot be combined with APK evidence options")
    if not args.dry_run:
        if not args.apk:
            parser.error("Provide --apk <path> or --dry-run")
        if not args.confirm_play_generated:
            parser.error("--confirm-play-generated is required with --apk")
        if not (args.installed_launched_on_device or args.installed_launched_on_emulator):
            parser.error("Confirm install/launch with --installed-launched-on-device or --installed-launched-on-emulator")
    return args


def selected_launch_target(args: argparse.Namespace) -> str:
    if args.installed_launched_on_device:
        return LAUNCH_DEVICE
    if args.installed_launched_on_emulator:
        return LAUNCH_EMULATOR
    raise PlayGeneratedApkEvidencePacketError("missing install/launch target")


def print_header() -> None:
    print("Play-generated APK evidence packet")
    print("==================================")
    print(f"- Destination evidence file: {DESTINATION_EVIDENCE}")
    print("- Requires a downloaded Play-generated APK artifact, not a locally built APK.")
    print("- Requires successful install and launch on an Android device or Android emulator.")
    print("- Do not record account tokens, private Play Console URLs, signing secrets or screenshots with account data.")


def main() -> int:
    args = parse_args()
    print_header()
    print()

    if args.dry_run:
        print("Required Command")
        print("----------------")
        print(
            "./tools/print_play_generated_apk_evidence_packet.py "
            "--apk <path-to-play-generated.apk> --confirm-play-generated "
            "--installed-launched-on-device"
        )
        print("or")
        print(
            "./tools/print_play_generated_apk_evidence_packet.py "
            "--apk <path-to-play-generated.apk> --confirm-play-generated "
            "--installed-launched-on-emulator"
        )
        print()
        print("play_generated_apk_evidence_packet_dry_run_ok")
        return 0

    try:
        verifier = load_verifier_module()
        result = verifier.verify_apk(project_path(args.apk))
        lines = evidence_lines(result, selected_launch_target(args))
    except (PlayGeneratedApkEvidencePacketError, OSError, zipfile.BadZipFile) as exc:
        print(f"play_generated_apk_evidence_packet_error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if exc.__class__.__name__ == "ApkReviewError":
            print(f"play_generated_apk_evidence_packet_error: {exc}", file=sys.stderr)
            return 1
        raise

    print("Verified By")
    print("-----------")
    print("./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk> -> play_generated_apk_verify_ok")
    print()
    print("Play-Generated APK Review Lines")
    print("-------------------------------")
    for line in lines:
        print(line)
    print()
    print("play_generated_apk_evidence_packet_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
