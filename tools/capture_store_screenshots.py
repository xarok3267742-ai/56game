#!/usr/bin/env python3
"""Capture Google Play screenshots from the installed release app.

The script drives the real release app through UIAutomator, captures five phone
screenshots and five large/tablet screenshots, converts them to RGB PNG files,
and rebuilds the feature graphic from the refreshed gameplay screenshot crop.
After a successful capture it updates play_store/upload_checksums.md so the
handoff stays in sync with the regenerated Play upload assets.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError as exc:  # pragma: no cover - operator environment check
    raise SystemExit("Pillow is required: python3 -m pip install Pillow") from exc


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.qgrid.mobile"
ACTIVITY = "com.qgrid.mobile/.MainActivity"
PHONE_CAPTURE_SIZE = (1080, 2400)
PHONE_UPLOAD_SIZE = (1080, 2064)
PHONE_UPLOAD_CROP_BOX = (0, 96, PHONE_UPLOAD_SIZE[0], 96 + PHONE_UPLOAD_SIZE[1])
TABLET_SIZE = (1600, 2560)
TABLET_UPLOAD_SIZE = (1600, 2336)
TABLET_UPLOAD_CROP_BOX = (0, 64, TABLET_UPLOAD_SIZE[0], 64 + TABLET_UPLOAD_SIZE[1])
FEATURE_GRAPHIC_SIZE = (1024, 500)
FEATURE_GAMEPLAY_CROP_BOX = (43, 200, 1040, 1540)
FEATURE_GAMEPLAY_CROP_SIZE = (997, 1340)
FEATURE_PANEL_SIZE = (335, 450)
FEATURE_PANEL_POSITION = (650, 25)
SCREENSHOT_NAMES = [
    "01_onboarding.png",
    "02_home.png",
    "03_game_start.png",
    "04_game_line.png",
    "05_settings.png",
]
UPLOAD_CHECKSUM_PATHS = [
    "app/build/outputs/bundle/release/app-release.aab",
    "play_store/icon/play_icon_512.png",
    "play_store/feature_graphic.png",
    *[f"play_store/screenshots/phone/{name}" for name in SCREENSHOT_NAMES],
    *[f"play_store/screenshots/tablet/{name}" for name in SCREENSHOT_NAMES],
]
UPLOAD_CHECKSUM_PATH_SET = set(UPLOAD_CHECKSUM_PATHS)


class CaptureError(RuntimeError):
    pass


def run(command: list[str], *, capture: bool = False, env: dict[str, str] | None = None) -> bytes:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if result.returncode != 0:
        stdout = result.stdout.decode("utf-8", "replace") if result.stdout else ""
        stderr = result.stderr.decode("utf-8", "replace") if result.stderr else ""
        raise CaptureError(f"Command failed: {' '.join(command)}\nSTDOUT={stdout}\nSTDERR={stderr}")
    return result.stdout or b""


class Adb:
    def __init__(self, serial: str) -> None:
        self.serial = serial

    def adb(self, *args: str, capture: bool = False) -> bytes:
        return run(["adb", "-s", self.serial, *args], capture=capture)

    def shell(self, *args: str, capture: bool = False) -> bytes:
        return self.adb("shell", *args, capture=capture)


def dump_tree(adb: Adb) -> ET.Element:
    raw = adb.adb("exec-out", "uiautomator", "dump", "/dev/tty", capture=True).decode(
        "utf-8",
        "replace",
    )
    start = raw.find("<?xml")
    end = raw.rfind("</hierarchy>")
    if start < 0 or end < 0:
        raise CaptureError(f"UI dump has no complete XML: {raw[:500]}")
    return ET.fromstring(raw[start : end + len("</hierarchy>")])


def all_nodes(adb: Adb) -> list[ET.Element]:
    last_packages: set[str] = set()
    for attempt in range(3):
        nodes = list(dump_tree(adb).iter())
        last_packages = {node.attrib.get("package", "") for node in nodes if node.attrib.get("package", "")}
        if PACKAGE in last_packages:
            return nodes
        if attempt < 2:
            adb.shell("am", "start", "-W", "-n", ACTIVITY)
            time.sleep(1.0)
    raise CaptureError(
        f"UI tree is not from {PACKAGE}; packages={sorted(last_packages)}. "
        "Another foreground app is interfering with screenshot capture."
    )


def node_center(node: ET.Element) -> tuple[int, int]:
    bounds = node.attrib.get("bounds", "")
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
    if not match:
        raise CaptureError(f"Bad UIAutomator bounds: {bounds!r}")
    x1, y1, x2, y2 = map(int, match.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def find_node(
    adb: Adb,
    *,
    text: str | None = None,
    text_contains: str | None = None,
    desc: str | None = None,
    desc_contains: str | None = None,
) -> ET.Element | None:
    for node in all_nodes(adb):
        node_text = node.attrib.get("text", "")
        node_desc = node.attrib.get("content-desc", "")
        if text is not None and node_text != text:
            continue
        if text_contains is not None and text_contains not in node_text:
            continue
        if desc is not None and node_desc != desc:
            continue
        if desc_contains is not None and desc_contains not in node_desc:
            continue
        if node.attrib.get("bounds", "") == "[0,0][0,0]":
            continue
        return node
    return None


def wait_for(label: str, predicate, timeout: float = 20.0):
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            value = predicate()
            if value is not None and value is not False:
                return value
        except Exception as exc:  # UIAutomator can be transient during transitions.
            last_error = exc
        time.sleep(0.5)
    raise CaptureError(f"Timed out waiting for {label}; last_error={last_error}")


def tap_text(adb: Adb, label: str, fallback: tuple[int, int] | None = None) -> None:
    try:
        node = wait_for(
            f"text or description {label}",
            lambda: find_node(adb, text_contains=label) or find_node(adb, desc_contains=label),
            timeout=8.0 if fallback is not None else 30.0,
        )
        x, y = node_center(node)
    except CaptureError:
        if fallback is None:
            raise
        adb.shell("am", "start", "-W", "-n", ACTIVITY)
        time.sleep(0.8)
        x, y = fallback
    adb.shell("input", "tap", str(x), str(y))
    time.sleep(0.7)


def tap_desc(adb: Adb, label: str) -> None:
    node = wait_for(f"description {label}", lambda: find_node(adb, desc_contains=label))
    x, y = node_center(node)
    adb.shell("input", "tap", str(x), str(y))
    time.sleep(0.7)


def tap_first_hint_cell(adb: Adb) -> None:
    node = wait_for(
        "hinted cell",
        lambda: next(
            (
                item
                for item in all_nodes(adb)
                if "Клетка" in item.attrib.get("content-desc", "")
                and "подсказка" in item.attrib.get("content-desc", "")
            ),
            None,
        ),
        timeout=12.0,
    )
    x, y = node_center(node)
    adb.shell("input", "tap", str(x), str(y))
    time.sleep(0.7)


def fixed_tap_points(size: tuple[int, int]) -> dict[str, tuple[int, int]]:
    if size == PHONE_CAPTURE_SIZE:
        return {
            "onboarding_start": (540, 1370),
            "home_start": (540, 880),
            "hint": (540, 1685),
        }
    if size == TABLET_SIZE:
        return {
            "onboarding_start": (800, 888),
            "home_start": (800, 630),
            "hint": (800, 2060),
        }
    raise CaptureError(f"No fixed tap points for capture size {size}")


def configure_display(adb: Adb, width: int, height: int, density: int | None) -> None:
    adb.shell("wm", "size", "reset")
    adb.shell("wm", "density", "reset")
    if (width, height) != PHONE_CAPTURE_SIZE:
        adb.shell("wm", "size", f"{width}x{height}")
    if density is not None:
        adb.shell("wm", "density", str(density))
    adb.shell("settings", "put", "system", "font_scale", "1.0")
    adb.shell("settings", "put", "global", "window_animation_scale", "0")
    adb.shell("settings", "put", "global", "transition_animation_scale", "0")
    adb.shell("settings", "put", "global", "animator_duration_scale", "0")
    time.sleep(1.5)


def start_fresh(adb: Adb) -> None:
    adb.shell("am", "force-stop", PACKAGE)
    adb.shell("pm", "clear", PACKAGE)
    time.sleep(1.2)
    adb.shell("am", "start", "-S", "-W", "-n", ACTIVITY)
    time.sleep(2.0)
    wait_for("onboarding start", lambda: find_node(adb, text_contains="Начать"), timeout=60.0)


def crop_upload_image(
    image: Image.Image,
    crop_box: tuple[int, int, int, int] | None,
    source_label: str,
) -> Image.Image:
    if crop_box is None:
        return image
    left, top, right, bottom = crop_box
    if left < 0 or top < 0 or right <= left or bottom <= top or right > image.width or bottom > image.height:
        raise CaptureError(f"{source_label} crop box {crop_box} is outside capture image {image.size}")
    return image.crop(crop_box)


def validate_saved_png(path: Path, expected_size: tuple[int, int]) -> None:
    if not path.is_file():
        raise CaptureError(f"{path.relative_to(ROOT)} was not written")
    with Image.open(path) as saved:
        if saved.format != "PNG":
            raise CaptureError(f"{path.relative_to(ROOT)} expected PNG, got {saved.format}")
        if saved.size != expected_size:
            raise CaptureError(f"{path.relative_to(ROOT)} expected saved size {expected_size}, got {saved.size}")
        if saved.mode != "RGB":
            raise CaptureError(f"{path.relative_to(ROOT)} expected RGB PNG without alpha, got {saved.mode}")


def capture_png(
    adb: Adb,
    path: Path,
    expected_size: tuple[int, int],
    *,
    crop_box: tuple[int, int, int, int] | None = None,
    text: str | None = None,
    desc: str | None = None,
) -> None:
    time.sleep(0.8)
    if text is not None:
        wait_for(f"text before capture {text}", lambda: find_node(adb, text_contains=text))
    if desc is not None:
        wait_for(f"description before capture {desc}", lambda: find_node(adb, desc_contains=desc))
    png = adb.adb("exec-out", "screencap", "-p", capture=True)
    image = Image.open(io.BytesIO(png)).convert("RGB")
    if image.size != expected_size:
        raise CaptureError(f"{path.relative_to(ROOT)} expected {expected_size}, got {image.size}")
    image = crop_upload_image(image, crop_box, str(path.relative_to(ROOT)))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    validate_saved_png(path, image.size)
    print(f"captured {path.relative_to(ROOT)} {image.size[0]}x{image.size[1]} {path.stat().st_size}")


def capture_set(
    adb: Adb,
    target_dir: Path,
    size: tuple[int, int],
    *,
    crop_box: tuple[int, int, int, int] | None = None,
) -> None:
    tap_points = fixed_tap_points(size)
    start_fresh(adb)
    capture_png(adb, target_dir / "01_onboarding.png", size, crop_box=crop_box, text="Линия 56")
    tap_text(adb, "Начать", fallback=tap_points["onboarding_start"])
    wait_for("home progress", lambda: find_node(adb, text="Прогресс"))
    capture_png(adb, target_dir / "02_home.png", size, crop_box=crop_box, text="Прогресс")
    tap_text(adb, "Начать", fallback=tap_points["home_start"])
    wait_for(
        "game board",
        lambda: len([item for item in all_nodes(adb) if "Клетка" in item.attrib.get("content-desc", "")]) >= 25,
    )
    capture_png(adb, target_dir / "03_game_start.png", size, crop_box=crop_box, text="Сумма")
    for _ in range(3):
        tap_text(adb, "Подсказка", fallback=tap_points["hint"])
        tap_first_hint_cell(adb)
    wait_for("selected gameplay line", lambda: find_node(adb, desc_contains="выбрана"))
    capture_png(adb, target_dir / "04_game_line.png", size, crop_box=crop_box, desc="выбрана")
    tap_desc(adb, "Назад")
    wait_for("home after game back", lambda: find_node(adb, text="Прогресс"))
    tap_desc(adb, "Настройки")
    wait_for("settings screen", lambda: find_node(adb, text="Тактильный отклик"))
    capture_png(adb, target_dir / "05_settings.png", size, crop_box=crop_box, text="Тактильный отклик")


def rebuild_feature_graphic() -> None:
    background_path = ROOT / "play_store/source_assets/feature_background_imagegen.png"
    screenshot_path = ROOT / "play_store/screenshots/phone/04_game_line.png"
    out_path = ROOT / "play_store/feature_graphic.png"

    background = Image.open(background_path).convert("RGB")
    scale = max(FEATURE_GRAPHIC_SIZE[0] / background.width, FEATURE_GRAPHIC_SIZE[1] / background.height)
    resized = background.resize(
        (round(background.width * scale), round(background.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - FEATURE_GRAPHIC_SIZE[0]) // 2
    top = (resized.height - FEATURE_GRAPHIC_SIZE[1]) // 2
    canvas = crop_upload_image(
        resized,
        (left, top, left + FEATURE_GRAPHIC_SIZE[0], top + FEATURE_GRAPHIC_SIZE[1]),
        str(background_path.relative_to(ROOT)),
    ).convert("RGBA")

    screenshot = Image.open(screenshot_path).convert("RGB")
    crop = crop_upload_image(screenshot, FEATURE_GAMEPLAY_CROP_BOX, str(screenshot_path.relative_to(ROOT)))
    if crop.size != FEATURE_GAMEPLAY_CROP_SIZE:
        raise CaptureError(f"{screenshot_path.relative_to(ROOT)} expected feature crop {FEATURE_GAMEPLAY_CROP_SIZE}, got {crop.size}")
    panel = crop.resize(FEATURE_PANEL_SIZE, Image.Resampling.LANCZOS).convert("RGBA")

    radius = 24
    mask = Image.new("L", FEATURE_PANEL_SIZE, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, FEATURE_PANEL_SIZE[0] - 1, FEATURE_PANEL_SIZE[1] - 1), radius=radius, fill=255)

    x, y = FEATURE_PANEL_POSITION
    shadow = Image.new("RGBA", FEATURE_GRAPHIC_SIZE, (0, 0, 0, 0))
    shadow_mask = Image.new("L", FEATURE_PANEL_SIZE, 0)
    shadow_draw = ImageDraw.Draw(shadow_mask)
    shadow_draw.rounded_rectangle((0, 0, FEATURE_PANEL_SIZE[0] - 1, FEATURE_PANEL_SIZE[1] - 1), radius=radius, fill=145)
    shadow_layer = Image.new("RGBA", FEATURE_PANEL_SIZE, (21, 55, 45, 110))
    shadow.paste(shadow_layer, (x + 8, y + 10), shadow_mask)
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)))
    canvas.paste(panel, (x, y), mask)

    border = Image.new("RGBA", FEATURE_GRAPHIC_SIZE, (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle(
        (x, y, x + FEATURE_PANEL_SIZE[0] - 1, y + FEATURE_PANEL_SIZE[1] - 1),
        radius=radius,
        outline=(193, 213, 205, 255),
        width=2,
    )
    canvas.alpha_composite(border)
    canvas.convert("RGB").save(out_path, format="PNG", optimize=True)
    validate_saved_png(out_path, FEATURE_GRAPHIC_SIZE)
    print(f"rebuilt {out_path.relative_to(ROOT)} {out_path.stat().st_size}")


def checksum_row(path: str) -> str:
    file_path = ROOT / path
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return f"| `{path}` | {file_path.stat().st_size} | `{digest}` |"


def parse_checksum_path_from_row(line: str) -> str | None:
    if not line.startswith("| `"):
        return None
    match = re.match(r"\| `([^`]+)` \|", line)
    if match is None:
        raise CaptureError(f"Bad upload checksum row: {line}")
    return match.group(1)


def validate_upload_checksum_paths(paths: list[str]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for path in paths:
        if path in seen:
            duplicates.append(path)
        seen.add(path)
    if duplicates:
        raise CaptureError(f"upload_checksums.md has duplicate rows for: {', '.join(sorted(set(duplicates)))}")
    missing = [path for path in UPLOAD_CHECKSUM_PATHS if path not in seen]
    if missing:
        raise CaptureError(f"upload_checksums.md is missing rows for: {', '.join(missing)}")
    unexpected = sorted(seen - UPLOAD_CHECKSUM_PATH_SET)
    if unexpected:
        raise CaptureError(f"upload_checksums.md has unexpected upload rows: {', '.join(unexpected)}")
    if tuple(paths) != tuple(UPLOAD_CHECKSUM_PATHS):
        raise CaptureError("upload_checksums.md row order must match the Play upload packet order")


def update_upload_checksums() -> None:
    checksum_path = ROOT / "play_store/upload_checksums.md"
    text = checksum_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    updated_rows = {path: checksum_row(path) for path in UPLOAD_CHECKSUM_PATHS}
    checksum_paths = [path for line in lines if (path := parse_checksum_path_from_row(line)) is not None]
    validate_upload_checksum_paths(checksum_paths)
    result: list[str] = []
    for line in lines:
        path = parse_checksum_path_from_row(line)
        if path in updated_rows:
            result.append(updated_rows[path])
            continue
        result.append(line)
    checksum_path.write_text("\n".join(result) + "\n", encoding="utf-8")
    print(f"updated {checksum_path.relative_to(ROOT)}")


def print_checksum_rows() -> None:
    print("\nCurrent checksum rows:")
    for path in UPLOAD_CHECKSUM_PATHS:
        print(checksum_row(path))


def install_release(serial: str) -> None:
    env = os.environ.copy()
    env["ANDROID_SERIAL"] = serial
    run(["./gradlew", "installRelease"], env=env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture Play Store screenshots from the release Android app.")
    parser.add_argument(
        "--serial",
        default=os.environ.get("ANDROID_SERIAL"),
        help="ADB serial. Defaults to ANDROID_SERIAL.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Do not run ./gradlew installRelease before capture.",
    )
    parser.add_argument(
        "--no-update-checksums",
        action="store_true",
        help="Print checksum rows without editing play_store/upload_checksums.md.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.serial:
        raise SystemExit("Pass --serial or set ANDROID_SERIAL to the target emulator/device.")

    adb = Adb(args.serial)
    adb.adb("wait-for-device")
    if not args.skip_install:
        install_release(args.serial)

    try:
        configure_display(adb, *PHONE_CAPTURE_SIZE, density=None)
        capture_set(adb, ROOT / "play_store/screenshots/phone", PHONE_CAPTURE_SIZE, crop_box=PHONE_UPLOAD_CROP_BOX)
        configure_display(adb, *TABLET_SIZE, density=320)
        capture_set(adb, ROOT / "play_store/screenshots/tablet", TABLET_SIZE, crop_box=TABLET_UPLOAD_CROP_BOX)
        rebuild_feature_graphic()
        if not args.no_update_checksums:
            update_upload_checksums()
        print_checksum_rows()
    finally:
        configure_display(adb, *PHONE_CAPTURE_SIZE, density=None)
        adb.shell("am", "force-stop", PACKAGE)


if __name__ == "__main__":
    main()
