#!/usr/bin/env python3
"""Run the final local gate before owner handoff.

This script is intentionally local by default. It builds/tests the release
candidate, optionally refreshes connected Android test evidence, then runs the
read-only handoff helpers that verify upload assets, the store-asset review
sheet, the optional upload archive, Play Console copy, post-upload evidence
draft, closed-testing evidence routing draft, privacy/contact evidence draft,
Play Console form evidence draft, pre-launch review evidence draft,
store-listing preview evidence draft, Play-generated APK review posture,
Play-generated APK evidence draft, local privacy HTML, signing input hygiene and
signing-backup evidence draft. Use --include-hosted-privacy only for a pre-upload run that should also revalidate the recorded hosted privacy policy URL.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BUILD_COMMAND: tuple[str, ...] = ("./gradlew", "test", "lint", "assembleDebug", "assembleRelease", "bundleRelease")
CONNECTED_COMMAND: tuple[str, ...] = ("./gradlew", "connectedDebugAndroidTest")
CONNECTED_OUTPUT_DIRS: tuple[Path, ...] = (
    ROOT / "app/build/outputs/androidTest-results/connected/debug",
    ROOT / "app/build/reports/androidTests/connected/debug",
)
FOCUS_BLOCKING_CONNECTED_PACKAGES: tuple[str, ...] = (
    "com.qgrid.mobile",
)
STALE_CONNECTED_PACKAGES: tuple[str, ...] = (
    "com.qgrid.mobile.debug.test",
    "com.qgrid.mobile.debug",
    "com.fiftyfive.seconds",
    "com.fiftyfive.seconds.debug.test",
    "com.fiftyfive.seconds.debug",
    "com.andrejivliev.shawarma58",
    "com.andrejivliev.shawarma58.debug.test",
    "com.andrejivliev.shawarma58.debug",
    "com.ivliev.line56.debug.test",
    "com.ivliev.line56.debug",
    "com.ivliev.line56",
)
PUBLICATION_READINESS_COMMAND: tuple[str, ...] = ("./tools/print_publication_readiness.py",)
PUBLICATION_READINESS_WITH_RECORDED_PRIVACY_COMMAND: tuple[str, ...] = (
    "./tools/print_publication_readiness.py",
    "--check-recorded-privacy-url",
)
HANDOFF_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("./tools/verify_release.py",),
    ("./tools/print_upload_packet.py",),
    ("./tools/print_post_upload_evidence_packet.py",),
    ("./tools/print_closed_testing_evidence_packet.py", "--dry-run"),
    ("./tools/print_privacy_contact_evidence_packet.py",),
    ("./tools/print_play_console_forms_evidence_packet.py",),
    ("./tools/print_pre_launch_review_evidence_packet.py",),
    ("./tools/create_store_asset_review_sheet.py", "--dry-run"),
    ("./tools/print_store_listing_review_evidence_packet.py",),
    ("./tools/prepare_play_upload_archive.py", "--dry-run"),
    ("./tools/prepare_play_upload_archive.py", "--verify-existing"),
    ("./tools/print_play_console_packet.py",),
    PUBLICATION_READINESS_COMMAND,
    ("./tools/verify_play_generated_apk.py", "--dry-run"),
    ("./tools/print_play_generated_apk_evidence_packet.py", "--dry-run"),
    ("./tools/check_privacy_policy_url.py", "--local"),
    ("./tools/check_signing_backup_inputs.py",),
    ("./tools/print_signing_backup_evidence_packet.py",),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Line 56 final local gate before handoff.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the commands without executing them.",
    )
    parser.add_argument(
        "--include-connected",
        action="store_true",
        help="Run connectedDebugAndroidTest before the verifier so API 36 instrumentation evidence is refreshed.",
    )
    parser.add_argument(
        "--connected-serial",
        help="ANDROID_SERIAL value for --include-connected, for example emulator-5560.",
    )
    parser.add_argument(
        "--include-hosted-privacy",
        action="store_true",
        help="Validate the recorded hosted privacy policy URL during publication-readiness output.",
    )
    args = parser.parse_args()
    if args.connected_serial and not args.include_connected:
        parser.error("--connected-serial requires --include-connected")
    return args


def handoff_commands(include_hosted_privacy: bool) -> tuple[tuple[str, ...], ...]:
    if not include_hosted_privacy:
        return HANDOFF_COMMANDS
    return tuple(
        PUBLICATION_READINESS_WITH_RECORDED_PRIVACY_COMMAND
        if command == PUBLICATION_READINESS_COMMAND
        else command
        for command in HANDOFF_COMMANDS
    )


def planned_commands(include_connected: bool, include_hosted_privacy: bool) -> tuple[tuple[str, ...], ...]:
    handoff = handoff_commands(include_hosted_privacy)
    if include_connected:
        return (BUILD_COMMAND, CONNECTED_COMMAND, *handoff)
    return (BUILD_COMMAND, *handoff)


def printable_command(command: tuple[str, ...], connected_serial: str | None) -> str:
    printable = " ".join(command)
    if command == CONNECTED_COMMAND and connected_serial:
        return f"ANDROID_SERIAL={connected_serial} {printable}"
    return printable


def command_environment(command: tuple[str, ...], connected_serial: str | None) -> dict[str, str] | None:
    if command != CONNECTED_COMMAND or not connected_serial:
        return None
    env = os.environ.copy()
    env["ANDROID_SERIAL"] = connected_serial
    return env


def clean_connected_outputs() -> None:
    for directory in CONNECTED_OUTPUT_DIRS:
        if directory.exists():
            shutil.rmtree(directory)


def installed_packages(serial: str) -> set[str]:
    completed = subprocess.run(
        ["adb", "-s", serial, "shell", "pm", "list", "packages"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    packages: set[str] = set()
    for line in completed.stdout.splitlines():
        if line.startswith("package:"):
            packages.add(line.removeprefix("package:").strip())
    return packages


def stale_process_ids(serial: str) -> dict[str, list[str]]:
    processes: dict[str, list[str]] = {}
    for package_name in (*FOCUS_BLOCKING_CONNECTED_PACKAGES, *STALE_CONNECTED_PACKAGES):
        completed = subprocess.run(
            ["adb", "-s", serial, "shell", "pidof", package_name],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        pids = [pid for pid in completed.stdout.split() if pid.strip()]
        if pids:
            processes[package_name] = pids
    return processes


def stop_stale_connected_processes(serial: str) -> None:
    for package_name in (*FOCUS_BLOCKING_CONNECTED_PACKAGES, *STALE_CONNECTED_PACKAGES):
        subprocess.run(
            ["adb", "-s", serial, "shell", "am", "force-stop", package_name],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    for pids in stale_process_ids(serial).values():
        subprocess.run(
            ["adb", "-s", serial, "shell", "kill", "-9", *pids],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def clean_stale_connected_packages(serial: str | None) -> None:
    if not serial:
        return
    stale_packages = set(STALE_CONNECTED_PACKAGES)
    stop_stale_connected_processes(serial)
    installed_stale_packages = installed_packages(serial) & stale_packages
    for package_name in sorted(installed_stale_packages):
        completed = subprocess.run(
            ["adb", "-s", serial, "uninstall", package_name],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            output = (completed.stdout + completed.stderr).strip()
            raise RuntimeError(f"Stale connected package uninstall failed for {package_name}: {output}")
    remaining_stale_packages = installed_packages(serial) & stale_packages
    if remaining_stale_packages:
        remaining = ", ".join(sorted(remaining_stale_packages))
        raise RuntimeError(f"Stale connected packages still installed on {serial}: {remaining}")
    stop_stale_connected_processes(serial)
    remaining_stale_processes = stale_process_ids(serial)
    if remaining_stale_processes:
        remaining = ", ".join(
            f"{package_name}({','.join(pids)})"
            for package_name, pids in sorted(remaining_stale_processes.items())
        )
        raise RuntimeError(f"Stale connected processes still running on {serial}: {remaining}")


def main() -> int:
    args = parse_args()
    print("Final local gate")
    print("================")
    for command in planned_commands(args.include_connected, args.include_hosted_privacy):
        printable = printable_command(command, args.connected_serial)
        if command == CONNECTED_COMMAND:
            if args.dry_run:
                print("- clean connected test outputs")
                print("- stop focus-blocking packages and uninstall stale connected debug/test packages on the selected serial")
            else:
                print()
                print("$ clean connected test outputs")
                clean_connected_outputs()
                print()
                print("$ stop focus-blocking packages and uninstall stale connected debug/test packages on the selected serial")
                try:
                    clean_stale_connected_packages(args.connected_serial)
                except RuntimeError as exc:
                    print(f"final_local_gate_error: {exc}", file=sys.stderr)
                    return 1
        if args.dry_run:
            print(f"- {printable}")
            continue

        print()
        print(f"$ {printable}")
        completed = subprocess.run(command, cwd=ROOT, env=command_environment(command, args.connected_serial))
        if completed.returncode != 0:
            print(f"final_local_gate_error: command failed with exit {completed.returncode}: {printable}", file=sys.stderr)
            return completed.returncode

    if args.dry_run:
        print("final_local_gate_dry_run_ok")
    else:
        print()
        print("final_local_gate_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
