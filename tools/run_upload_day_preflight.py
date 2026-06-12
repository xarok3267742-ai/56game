#!/usr/bin/env python3
"""Run the upload-day preflight and write safe owner handoff outputs.

This helper is for the final local pass immediately before Play Console upload.
It keeps the external owner gates explicit: it does not edit evidence templates,
does not upload to Play Console and does not claim production readiness.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FINAL_LOCAL_GATE = ("./tools/run_final_local_gate.py",)
MANAGED_API36_CONNECTED_GATE = ("./tools/run_api36_connected_gate.py", "--include-hosted-privacy")
WRITE_AND_VERIFY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("./tools/create_store_asset_review_sheet.py", "--write"),
    ("./tools/prepare_play_upload_archive.py", "--write"),
    ("./tools/prepare_play_upload_archive.py", "--verify-existing"),
    ("./tools/print_upload_packet.py",),
    ("./tools/print_play_console_packet.py",),
    ("./tools/print_publication_readiness.py", "--check-recorded-privacy-url"),
)
REMOTE_RELEASE_COMMAND_PREFIX = ("./tools/verify_remote_release.py", "--tag")
MANAGED_GATE_TRANSIENT_EXIT_CODES = (-15, 241)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Line 56 upload-day preflight.")
    parser.add_argument("--dry-run", action="store_true", help="Print the upload-day command sequence without executing it.")
    parser.add_argument(
        "--include-connected",
        action="store_true",
        help="Run the hosted-privacy final local gate with connectedDebugAndroidTest on a supplied serial.",
    )
    parser.add_argument("--connected-serial", help="ANDROID_SERIAL value for --include-connected, for example emulator-5560.")
    parser.add_argument(
        "--managed-api36-connected",
        action="store_true",
        help="Use the project-owned API 36 AVD helper instead of a plain final local gate.",
    )
    parser.add_argument(
        "--release-tag",
        help="Optional annotated release tag to verify remotely after the local upload packet is prepared.",
    )
    args = parser.parse_args()
    if args.connected_serial and not args.include_connected:
        parser.error("--connected-serial requires --include-connected")
    if args.include_connected and not args.connected_serial:
        parser.error("--include-connected requires --connected-serial")
    if args.managed_api36_connected and (args.include_connected or args.connected_serial):
        parser.error("--managed-api36-connected cannot be combined with --include-connected or --connected-serial")
    return args


def local_gate_command(args: argparse.Namespace) -> tuple[str, ...]:
    if args.managed_api36_connected:
        return MANAGED_API36_CONNECTED_GATE
    command = [*FINAL_LOCAL_GATE]
    if args.include_connected:
        command.extend(["--include-connected", "--connected-serial", args.connected_serial])
    command.append("--include-hosted-privacy")
    return tuple(command)


def planned_commands(args: argparse.Namespace) -> tuple[tuple[str, ...], ...]:
    commands = [local_gate_command(args), *WRITE_AND_VERIFY_COMMANDS]
    if args.release_tag:
        commands.append((*REMOTE_RELEASE_COMMAND_PREFIX, args.release_tag))
    return tuple(commands)


def managed_api36_gate_was_terminated(command: tuple[str, ...], exit_code: int) -> bool:
    return command == MANAGED_API36_CONNECTED_GATE and exit_code in MANAGED_GATE_TRANSIENT_EXIT_CODES


def run_command(command: tuple[str, ...]) -> int:
    completed = subprocess.run(command, cwd=ROOT)
    if managed_api36_gate_was_terminated(command, completed.returncode):
        print("managed API 36 connected preflight ended during emulator loss; retrying that managed gate once")
        completed = subprocess.run(command, cwd=ROOT)
    return completed.returncode


def main() -> int:
    args = parse_args()
    print("Upload day preflight")
    print("====================")
    print("This helper writes only generated review/handoff outputs and keeps external owner gates unresolved until real Play Console evidence is recorded.")
    print()

    for command in planned_commands(args):
        printable = " ".join(command)
        if args.dry_run:
            print(f"- {printable}")
            if command == MANAGED_API36_CONNECTED_GATE:
                print("- if that managed API 36 gate is terminated by transient emulator loss, rerun it once")
            continue
        print(f"$ {printable}")
        exit_code = run_command(command)
        if exit_code != 0:
            print(f"upload_day_preflight_error: command failed with exit {exit_code}: {printable}", file=sys.stderr)
            return exit_code
        print()

    if args.dry_run:
        print("upload_day_preflight_dry_run_ok")
    else:
        print("Owner handoff archive: build/play_upload/line56_v1_google_play_upload_packet.zip")
        print("Store asset review sheet: play_store/store_asset_review_sheet.png")
        print("Next production gate after external evidence: ./tools/print_publication_readiness.py --check-recorded-privacy-url --require-production-ready")
        print("upload_day_preflight_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
