#!/usr/bin/env python3
"""Boot a clean project-owned API 36 AVD and run the connected final local gate.

The helper intentionally targets a dedicated serial/port and refuses to touch a
different AVD on that serial. If it starts the emulator, it stops only that
emulator during cleanup. If the requested serial was already running, it leaves
that emulator running. When the helper starts the AVD, it wipes the AVD data by
default so stale debug/test APKs from older local projects cannot steal focus
during instrumentation. Some emulator builds exit after the wipe reset instead
of continuing to boot, so the helper retries once without -wipe-data after that clean reset.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AVD = "Medium_Phone_API_36"
DEFAULT_SERIAL = "emulator-5560"
DEFAULT_PORT = 5560
DEFAULT_BOOT_TIMEOUT_SECONDS = 180
DEFAULT_LOG = Path("/tmp/line56_api36_connected_gate.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Line 56 final gate with a managed API 36 emulator.")
    parser.add_argument("--avd", default=DEFAULT_AVD, help=f"AVD name to boot. Default: {DEFAULT_AVD}.")
    parser.add_argument("--serial", default=DEFAULT_SERIAL, help=f"ADB serial to use. Default: {DEFAULT_SERIAL}.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Emulator console port. Default: {DEFAULT_PORT}.")
    parser.add_argument(
        "--boot-timeout",
        type=int,
        default=DEFAULT_BOOT_TIMEOUT_SECONDS,
        help=f"Seconds to wait for boot_completed. Default: {DEFAULT_BOOT_TIMEOUT_SECONDS}.",
    )
    parser.add_argument("--emulator-log", type=Path, default=DEFAULT_LOG, help=f"Emulator log path. Default: {DEFAULT_LOG}.")
    parser.add_argument("--keep-emulator", action="store_true", help="Do not stop an emulator started by this helper.")
    parser.add_argument(
        "--preserve-avd-data",
        action="store_true",
        help="Do not pass -wipe-data when this helper starts the project-owned AVD.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without starting or stopping emulators.")
    args = parser.parse_args()
    expected_serial = f"emulator-{args.port}"
    if args.serial != expected_serial:
        parser.error(f"--serial must match --port; expected {expected_serial} for port {args.port}")
    if args.boot_timeout <= 0:
        parser.error("--boot-timeout must be positive")
    return args


def sdk_dir() -> Path:
    local_properties = ROOT / "local.properties"
    if local_properties.is_file():
        for raw_line in local_properties.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("sdk.dir="):
                return Path(line.split("=", 1)[1]).expanduser()
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(env_name)
        if value:
            return Path(value).expanduser()
    raise RuntimeError("Android SDK not found; set local.properties sdk.dir or ANDROID_HOME")


def emulator_binary() -> Path:
    binary = sdk_dir() / "emulator" / "emulator"
    if not binary.is_file():
        raise RuntimeError(f"missing emulator binary: {binary}")
    return binary


def adb_command(serial: str, *args: str) -> list[str]:
    return ["adb", "-s", serial, *args]


def run_text(command: list[str], *, timeout: int = 30) -> str:
    return subprocess.check_output(command, cwd=ROOT, stderr=subprocess.STDOUT, text=True, timeout=timeout)


def adb_devices() -> dict[str, str]:
    output = run_text(["adb", "devices"], timeout=15)
    devices: dict[str, str] = {}
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            devices[parts[0]] = parts[1]
    return devices


def serial_state(serial: str) -> str | None:
    return adb_devices().get(serial)


def avd_name(serial: str) -> str:
    output = run_text(adb_command(serial, "emu", "avd", "name"), timeout=15)
    return output.splitlines()[0].strip()


def sdk_level(serial: str) -> str:
    return run_text(adb_command(serial, "shell", "getprop", "ro.build.version.sdk"), timeout=15).strip()


def boot_completed(serial: str) -> bool:
    try:
        return run_text(adb_command(serial, "shell", "getprop", "sys.boot_completed"), timeout=10).strip() == "1"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def wait_for_boot(serial: str, avd: str, timeout_seconds: int, process: subprocess.Popen[bytes] | None, log_path: Path) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"emulator exited before boot; log tail:\n{log_tail(log_path)}")
        if serial_state(serial) == "device" and boot_completed(serial):
            actual_avd = avd_name(serial)
            actual_sdk = sdk_level(serial)
            if actual_avd != avd:
                raise RuntimeError(f"{serial} is {actual_avd}, expected {avd}")
            if actual_sdk != "36":
                raise RuntimeError(f"{serial} is API {actual_sdk}, expected API 36")
            return
        time.sleep(2)
    raise RuntimeError(f"timed out waiting for {serial} / {avd}; log tail:\n{log_tail(log_path)}")


def process_exited_before_boot(exc: Exception) -> bool:
    return "emulator exited before boot" in str(exc)


def log_tail(path: Path, lines: int = 80) -> str:
    if not path.is_file():
        return "<missing emulator log>"
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:])


def start_emulator(avd: str, port: int, log_path: Path, wipe_data: bool) -> subprocess.Popen[bytes]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("wb")
    command = [
        str(emulator_binary()),
        "-avd",
        avd,
        "-port",
        str(port),
        "-no-window",
        "-no-audio",
        "-no-boot-anim",
        "-gpu",
        "swiftshader_indirect",
        "-no-snapshot-load",
        "-no-snapshot-save",
    ]
    if wipe_data:
        command.append("-wipe-data")
    process = subprocess.Popen(command, cwd=ROOT, stdout=log_file, stderr=subprocess.STDOUT)
    log_file.close()
    return process


def stop_started_emulator(serial: str, process: subprocess.Popen[bytes] | None) -> None:
    try:
        if serial_state(serial) == "device":
            subprocess.run(adb_command(serial, "emu", "kill"), cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    except subprocess.TimeoutExpired:
        pass

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if serial_state(serial) != "device" and (process is None or process.poll() is not None):
            return
        time.sleep(1)

    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def run_gate(serial: str) -> int:
    command = ["./tools/run_final_local_gate.py", "--include-connected", "--connected-serial", serial]
    completed = subprocess.run(command, cwd=ROOT)
    return completed.returncode


def main() -> int:
    args = parse_args()
    print("API 36 connected final gate")
    print("===========================")
    print(f"AVD: {args.avd}")
    print(f"Serial: {args.serial}")
    print(f"Port: {args.port}")
    print(f"Emulator log: {args.emulator_log}")
    print(f"Wipe AVD data on managed start: {not args.preserve_avd_data}")

    if args.dry_run:
        print("- verify requested serial is absent or already the requested API 36 AVD")
        wipe_note = " with -wipe-data" if not args.preserve_avd_data else " without -wipe-data"
        print(f"- start {args.avd} on {args.serial} if needed{wipe_note}")
        if not args.preserve_avd_data:
            print("- if -wipe-data exits after reset before boot, retry the cleaned AVD once without -wipe-data")
        print(f"- ./tools/run_final_local_gate.py --include-connected --connected-serial {args.serial}")
        print("- stop only the emulator started by this helper unless --keep-emulator is set")
        print("api36_connected_gate_dry_run_ok")
        return 0

    process: subprocess.Popen[bytes] | None = None
    started_by_helper = False
    try:
        state = serial_state(args.serial)
        if state is None:
            process = start_emulator(args.avd, args.port, args.emulator_log, wipe_data=not args.preserve_avd_data)
            started_by_helper = True
        elif state != "device":
            raise RuntimeError(f"{args.serial} is present but not usable: {state}")
        else:
            actual_avd = avd_name(args.serial)
            actual_sdk = sdk_level(args.serial)
            if actual_avd != args.avd or actual_sdk != "36":
                raise RuntimeError(f"{args.serial} is {actual_avd} API {actual_sdk}; refusing to use or stop it")

        try:
            wait_for_boot(args.serial, args.avd, args.boot_timeout, process, args.emulator_log)
        except RuntimeError as exc:
            if args.preserve_avd_data or not started_by_helper or not process_exited_before_boot(exc):
                raise
            print("wipe-data boot exited before boot; retrying cleaned AVD without -wipe-data")
            process = start_emulator(args.avd, args.port, args.emulator_log, wipe_data=False)
            wait_for_boot(args.serial, args.avd, args.boot_timeout, process, args.emulator_log)
        exit_code = run_gate(args.serial)
        if exit_code != 0:
            return exit_code
        print("api36_connected_gate_ok")
        return 0
    except Exception as exc:
        print(f"api36_connected_gate_error: {exc}", file=sys.stderr)
        return 1
    finally:
        if started_by_helper and not args.keep_emulator:
            stop_started_emulator(args.serial, process)


if __name__ == "__main__":
    raise SystemExit(main())
