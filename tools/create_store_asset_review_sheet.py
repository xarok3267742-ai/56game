#!/usr/bin/env python3
"""Create a local Google Play store-asset review sheet.

The generated PNG is an internal owner-review artifact and must not be uploaded to Play Console.
Use it to inspect icon, feature graphic and screenshot crops side by side before the external Play Console preview review.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "play_store/store_asset_review_sheet.png"
CANVAS_SIZE = (1800, 2050)

EXPECTED_IMAGES: tuple[tuple[str, tuple[int, int]], ...] = (
    ("play_store/icon/play_icon_512.png", (512, 512)),
    ("play_store/feature_graphic.png", (1024, 500)),
    ("play_store/screenshots/phone/01_onboarding.png", (1080, 2064)),
    ("play_store/screenshots/phone/02_home.png", (1080, 2064)),
    ("play_store/screenshots/phone/03_game_start.png", (1080, 2064)),
    ("play_store/screenshots/phone/04_game_line.png", (1080, 2064)),
    ("play_store/screenshots/phone/05_settings.png", (1080, 2064)),
    ("play_store/screenshots/tablet/01_onboarding.png", (1600, 2336)),
    ("play_store/screenshots/tablet/02_home.png", (1600, 2336)),
    ("play_store/screenshots/tablet/03_game_start.png", (1600, 2336)),
    ("play_store/screenshots/tablet/04_game_line.png", (1600, 2336)),
    ("play_store/screenshots/tablet/05_settings.png", (1600, 2336)),
)


class ReviewSheetError(RuntimeError):
    pass


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def validate_images(
    images: tuple[tuple[str, tuple[int, int]], ...] = EXPECTED_IMAGES,
    root: Path = ROOT,
) -> None:
    for relative_path, expected_size in images:
        path = root / relative_path
        if not path.is_file():
            raise ReviewSheetError(f"Missing store asset: {relative_path}")
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ReviewSheetError(f"{relative_path}: expected PNG, got {image.format}")
            if image.size != expected_size:
                raise ReviewSheetError(f"{relative_path}: expected {expected_size}, got {image.size}")
            if image.mode not in {"RGB", "RGBA"}:
                raise ReviewSheetError(f"{relative_path}: expected RGB/RGBA PNG, got {image.mode}")


def open_rgb(relative_path: str) -> Image.Image:
    return Image.open(ROOT / relative_path).convert("RGB")


def fit(image: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(max_size, Image.Resampling.LANCZOS)
    return copy


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont) -> None:
    draw.text(xy, text, fill="#21302f", font=font)


def draw_thumb(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    relative_path: str,
    xy: tuple[int, int],
    max_size: tuple[int, int],
    label: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int]:
    image = fit(open_rgb(relative_path), max_size)
    x, y = xy
    border = 2
    shadow = 5
    draw.rounded_rectangle(
        [x + shadow, y + shadow, x + image.width + shadow + border * 2, y + image.height + shadow + border * 2],
        radius=10,
        fill="#d5ddd8",
    )
    draw.rounded_rectangle(
        [x, y, x + image.width + border * 2, y + image.height + border * 2],
        radius=10,
        fill="#ffffff",
        outline="#8aa197",
        width=2,
    )
    sheet.paste(image, (x + border, y + border))
    draw_label(draw, (x, y + image.height + 12), label, font)
    return image.size


def build_sheet(output: Path) -> None:
    validate_images()
    output.parent.mkdir(parents=True, exist_ok=True)

    sheet = Image.new("RGB", CANVAS_SIZE, "#f4f7f2")
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(42, bold=True)
    section_font = load_font(28, bold=True)
    label_font = load_font(18)
    note_font = load_font(22)

    draw.text((64, 46), "Line 56 - Google Play Asset Review Sheet", fill="#172421", font=title_font)
    draw.text((64, 104), "Internal owner review only. Do not upload this sheet to Play Console.", fill="#52645f", font=note_font)

    draw.rounded_rectangle([48, 150, 1752, 760], radius=14, fill="#ffffff", outline="#d7e0dc", width=2)
    draw.text((72, 178), "Primary store assets", fill="#172421", font=section_font)
    draw_thumb(sheet, draw, "play_store/icon/play_icon_512.png", (86, 238), (236, 236), "Store icon 512x512", label_font)
    draw_thumb(sheet, draw, "play_store/feature_graphic.png", (390, 226), (980, 478), "Feature graphic 1024x500", label_font)

    draw.rounded_rectangle([48, 790, 1752, 1395], radius=14, fill="#ffffff", outline="#d7e0dc", width=2)
    draw.text((72, 818), "Phone screenshots - upload PNGs cropped without system bars", fill="#172421", font=section_font)
    phone_files = [
        ("play_store/screenshots/phone/01_onboarding.png", "01 onboarding"),
        ("play_store/screenshots/phone/02_home.png", "02 home"),
        ("play_store/screenshots/phone/03_game_start.png", "03 game start"),
        ("play_store/screenshots/phone/04_game_line.png", "04 game line"),
        ("play_store/screenshots/phone/05_settings.png", "05 settings"),
    ]
    x = 84
    for relative_path, label in phone_files:
        draw_thumb(sheet, draw, relative_path, (x, 860), (245, 468), label, label_font)
        x += 328

    draw.rounded_rectangle([48, 1425, 1752, 1935], radius=14, fill="#ffffff", outline="#d7e0dc", width=2)
    draw.text((72, 1453), "Large/tablet screenshots - upload PNGs cropped without system bars", fill="#172421", font=section_font)
    tablet_files = [
        ("play_store/screenshots/tablet/01_onboarding.png", "01 onboarding"),
        ("play_store/screenshots/tablet/02_home.png", "02 home"),
        ("play_store/screenshots/tablet/03_game_start.png", "03 game start"),
        ("play_store/screenshots/tablet/04_game_line.png", "04 game line"),
        ("play_store/screenshots/tablet/05_settings.png", "05 settings"),
    ]
    x = 84
    for relative_path, label in tablet_files:
        draw_thumb(sheet, draw, relative_path, (x, 1505), (250, 365), label, label_font)
        x += 328

    draw.text(
        (64, 1970),
        "Review focus: no damaging crop, no rejected/source assets, no debug/test/signing files, no fake UI.",
        fill="#52645f",
        font=note_font,
    )
    sheet.save(output, format="PNG", optimize=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the Line 56 store asset review sheet.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print the planned output without writing.")
    parser.add_argument("--write", action="store_true", help="Write the review sheet PNG.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output PNG path for --write.")
    args = parser.parse_args()
    if args.dry_run and args.write:
        parser.error("--dry-run and --write are mutually exclusive")
    if not args.dry_run and not args.write:
        args.dry_run = True
    return args


def main() -> int:
    args = parse_args()
    try:
        validate_images()
        output = args.output if args.output.is_absolute() else ROOT / args.output
        if args.write:
            build_sheet(output)
            print("Store asset review sheet")
            print("========================")
            print(f"- output: {output.relative_to(ROOT)}")
            print(f"- size: {CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}")
            print(f"- bytes: {output.stat().st_size}")
            print("- reviewed assets:")
        else:
            print("Store asset review sheet dry run")
            print("================================")
            print(f"- planned output: {output.relative_to(ROOT)}")
            print(f"- planned size: {CANVAS_SIZE[0]}x{CANVAS_SIZE[1]}")
            print("- would review:")
        for relative_path, expected_size in EXPECTED_IMAGES:
            print(f"  - {relative_path} ({expected_size[0]}x{expected_size[1]})")
        print()
        print("store_asset_review_sheet_ok" if args.write else "store_asset_review_sheet_dry_run_ok")
        return 0
    except (OSError, ReviewSheetError) as exc:
        print(f"store_asset_review_sheet_error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
