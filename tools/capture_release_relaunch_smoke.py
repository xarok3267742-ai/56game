#!/usr/bin/env python3
"""Capture release background/relaunch smoke evidence on an adb device."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.qgrid.mobile"
ACTIVITY = "com.qgrid.mobile/.MainActivity"
ARTIFACT_DIR = ROOT / "docs/qa_artifacts"
STATE_PATH = ARTIFACT_DIR / "release_relaunch_state.txt"
SCREENSHOT_PATH = ARTIFACT_DIR / "release_relaunch_home.png"


class RelaunchSmokeError(RuntimeError):
    pass


def read_sdk_dir() -> Path:
    local_properties = ROOT / "local.properties"
    if local_properties.is_file():
        for line in local_properties.read_text(encoding="utf-8").splitlines():
            if line.startswith("sdk.dir="):
                return Path(line.split("=", 1)[1].strip())
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if android_home:
        return Path(android_home)
    raise RelaunchSmokeError("Android SDK path not found in local.properties, ANDROID_HOME or ANDROID_SDK_ROOT")


def adb_path() -> Path:
    path = read_sdk_dir() / "platform-tools" / "adb"
    if not path.is_file():
        raise RelaunchSmokeError(f"adb not found: {path}")
    return path


def run_command(args: list[str], *, timeout: int = 60, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RelaunchSmokeError(f"command failed ({completed.returncode}): {' '.join(args)}\n{completed.stdout}")
    return completed.stdout.strip()


def adb(serial: str, *args: str, timeout: int = 30, text: bool = True) -> str | bytes:
    command = [str(adb_path()), "-s", serial, *args]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=text,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        output = completed.stdout if isinstance(completed.stdout, str) else completed.stdout.decode("utf-8", errors="ignore")
        raise RelaunchSmokeError(f"adb failed ({completed.returncode}): {' '.join(command)}\n{output}")
    return completed.stdout


def install_release(serial: str) -> None:
    env = os.environ.copy()
    env["ANDROID_SERIAL"] = serial
    run_command(["./gradlew", "installRelease"], timeout=180, env=env)


def dump_ui(serial: str) -> ET.Element:
    raw = adb(serial, "exec-out", "uiautomator", "dump", "/dev/tty", timeout=20)
    assert isinstance(raw, str)
    start = raw.find("<?xml")
    if start < 0:
        raise RelaunchSmokeError(f"uiautomator dump did not contain XML:\n{raw}")
    end = raw.find("</hierarchy>", start)
    if end < 0:
        raise RelaunchSmokeError(f"uiautomator dump did not contain a complete hierarchy:\n{raw}")
    xml = raw[start : end + len("</hierarchy>")]
    return ET.fromstring(xml)


def node_value(node: ET.Element, key: str) -> str:
    return node.attrib.get(key, "")


def find_node(root: ET.Element, *, text: str | None = None, contains_text: str | None = None) -> ET.Element | None:
    for node in root.iter("node"):
        node_text = node_value(node, "text")
        description = node_value(node, "content-desc")
        if text is not None and (node_text == text or description == text):
            return node
        if contains_text is not None and (contains_text in node_text or contains_text in description):
            return node
    return None


def bounds_center(node: ET.Element) -> tuple[int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node_value(node, "bounds"))
    if match is None:
        raise RelaunchSmokeError(f"node has invalid bounds: {node.attrib}")
    x1, y1, x2, y2 = (int(item) for item in match.groups())
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def wait_for(serial: str, label: str, predicate, *, timeout: float = 12.0) -> ET.Element:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            root = dump_ui(serial)
            if predicate(root):
                return root
        except Exception as exc:  # noqa: BLE001 - keep polling through transient UI dump failures.
            last_error = exc
        time.sleep(0.5)
    if last_error is not None:
        raise RelaunchSmokeError(f"timed out waiting for {label}: {last_error}") from last_error
    raise RelaunchSmokeError(f"timed out waiting for {label}")


def tap_text(serial: str, text: str) -> None:
    root = wait_for(serial, f"text {text}", lambda tree: find_node(tree, text=text) is not None)
    node = find_node(root, text=text)
    if node is None:
        raise RelaunchSmokeError(f"missing tappable text: {text}")
    x, y = bounds_center(node)
    adb(serial, "shell", "input", "tap", str(x), str(y), timeout=10)


def launch_app(serial: str) -> str:
    return str(adb(serial, "shell", "am", "start", "-W", "-n", ACTIVITY, timeout=30)).strip()


def collect_crash_summary(serial: str) -> str:
    crash_log = str(adb(serial, "shell", "logcat", "-b", "crash", "-d", timeout=20))
    package_lines = [line for line in crash_log.splitlines() if PACKAGE in line]
    if package_lines:
        return "matching app crash entries found:\n" + "\n".join(package_lines[-20:])
    return "no matching app crash entries"


def capture_screenshot(serial: str) -> None:
    png = adb(serial, "exec-out", "screencap", "-p", timeout=20, text=False)
    assert isinstance(png, bytes)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_PATH.write_bytes(png)


def text_present(root: ET.Element, text: str) -> bool:
    return find_node(root, text=text) is not None or find_node(root, contains_text=text) is not None


def normalize_expected_api(expected_api: str) -> str:
    expected = expected_api.strip().lower()
    if expected == "any":
        return expected
    if re.fullmatch(r"0|[1-9]\d{0,2}", expected):
        return expected
    raise RelaunchSmokeError("--expected-api must be an Android API number without leading zeroes or 'any' for diagnostics")


def validate_expected_api(actual_api: str, expected_api: str) -> str:
    expected = normalize_expected_api(expected_api)
    if expected == "any":
        return expected
    if actual_api != expected:
        raise RelaunchSmokeError(
            f"release relaunch smoke requires API {expected}; target is API {actual_api}. "
            "Use --expected-api any only for diagnostic runs that will not satisfy the release verifier.",
        )
    return expected


def emulator_avd_name(serial: str) -> str:
    output = str(adb(serial, "emu", "avd", "name", timeout=10)).strip().replace("\r", "\n")
    return output.splitlines()[0].strip()


def run_smoke(serial: str, *, skip_install: bool, expected_api: str) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    sdk = str(adb(serial, "shell", "getprop", "ro.build.version.sdk", timeout=10)).strip()
    expected_api = validate_expected_api(sdk, expected_api)

    if not skip_install:
        install_release(serial)

    avd_name = emulator_avd_name(serial)
    wm_size = str(adb(serial, "shell", "wm", "size", timeout=10)).strip()
    resolved_activity = str(adb(serial, "shell", "cmd", "package", "resolve-activity", "--brief", PACKAGE, timeout=10)).strip()

    adb(serial, "shell", "logcat", "-c", timeout=10)
    adb(serial, "shell", "pm", "clear", PACKAGE, timeout=20)
    first_launch = launch_app(serial)

    wait_for(serial, "onboarding", lambda tree: text_present(tree, "Линия 56") and text_present(tree, "Начать"))
    tap_text(serial, "Начать")
    wait_for(serial, "home after onboarding", lambda tree: text_present(tree, "Прогресс"))

    adb(serial, "shell", "input", "keyevent", "3", timeout=10)
    background_launch = launch_app(serial)
    wait_for(serial, "home after background return", lambda tree: text_present(tree, "Прогресс"))

    adb(serial, "shell", "am", "force-stop", PACKAGE, timeout=10)
    relaunch = launch_app(serial)
    relaunch_root = wait_for(serial, "home after force-stop relaunch", lambda tree: text_present(tree, "Прогресс"))
    capture_screenshot(serial)

    onboarding_still_visible = text_present(relaunch_root, "Соединяйте соседние клетки")
    progress_visible = text_present(relaunch_root, "Прогресс")
    start_visible = text_present(relaunch_root, "Начать")
    crash_summary = collect_crash_summary(serial)

    evidence = "\n".join(
        [
            "Release relaunch smoke evidence",
            f"checked_on={date.today().isoformat()}",
            f"serial={serial}",
            f"avd_name={avd_name}",
            f"expected_api={expected_api}",
            f"api={sdk}",
            f"wm_size={wm_size}",
            f"package={PACKAGE}",
            f"resolved_activity={resolved_activity}",
            "first_launch_command=am start -W -n com.qgrid.mobile/.MainActivity",
            f"first_launch_result={first_launch}",
            "background_return_command=input keyevent HOME then am start -W",
            f"background_return_result={background_launch}",
            "force_stop_relaunch_command=am force-stop com.qgrid.mobile then am start -W",
            f"force_stop_relaunch_result={relaunch}",
            f"home_progress_visible_after_relaunch={str(progress_visible).lower()}",
            f"home_start_action_visible_after_relaunch={str(start_visible).lower()}",
            f"onboarding_not_visible_after_relaunch={str(not onboarding_still_visible).lower()}",
            f"screenshot={SCREENSHOT_PATH.relative_to(ROOT).as_posix()}",
            f"crash_buffer={crash_summary}",
            "release_relaunch_smoke_ok",
            "",
        ],
    )
    STATE_PATH.write_text(evidence, encoding="utf-8")

    if not progress_visible or onboarding_still_visible or PACKAGE in crash_summary:
        raise RelaunchSmokeError(evidence)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture release relaunch smoke evidence on an adb device.")
    parser.add_argument("--serial", default=os.environ.get("ANDROID_SERIAL"), help="adb serial to use.")
    parser.add_argument("--skip-install", action="store_true", help="Do not run ./gradlew installRelease before the smoke.")
    parser.add_argument(
        "--expected-api",
        default="36",
        help="Required Android API before installing/running release smoke. Use 'any' only for diagnostics.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.serial:
        print("release_relaunch_smoke_error: --serial or ANDROID_SERIAL is required", file=sys.stderr)
        return 2
    try:
        run_smoke(args.serial, skip_install=args.skip_install, expected_api=args.expected_api)
    except RelaunchSmokeError as exc:
        print(f"release_relaunch_smoke_error: {exc}", file=sys.stderr)
        return 1
    print(f"release_relaunch_state={STATE_PATH.relative_to(ROOT).as_posix()}")
    print(f"release_relaunch_screenshot={SCREENSHOT_PATH.relative_to(ROOT).as_posix()}")
    print("release_relaunch_smoke_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
