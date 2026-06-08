# Asset Prompts

Store screenshots, the app icon and the feature graphic are present. This document remains the creative source and checklist for future store-asset updates.

## App Icon Concept

Use case: logo-brand. Asset type: Android and Google Play app icon, square 1:1, minimalist numeric puzzle identity. Create a polished calm app icon for a numeric puzzle game about connecting cells to reach a target sum. Centered abstract puzzle mark with a compact grid of rounded tiles and a smooth continuous path connecting circular nodes across adjacent cells. Modern flat vector-like raster illustration, crisp edges, very subtle depth only, no heavy shadows, no toy-like 3D, no mascot, no characters. Palette: deep teal background, warm ivory tiles, muted sea-green tiles, refined amber path, small coral accent, high contrast, not monochrome. Keep all important elements inside the central safe area for Android adaptive masks. Avoid text, letters, digits, UI screenshots, buttons, badges, watermark, stock-photo look, scary/aggressive styling and glossy plastic.

Final icon source: `play_store/source_assets/icon_imagegen_20260606.png`. Final cleaned/resized outputs: `play_store/icon/play_icon_512.png` and `app/src/main/res/drawable-nodpi/ic_launcher_imagegen.png`; both are full-square 512x512 PNGs with opaque alpha and no transparent pixels. Prior generated icon variants were archived as `play_store/archive/icon_imagegen_20260605_rejected.png` and `play_store/archive/icon_imagegen_20260606_rejected_owner_review.png` after visual review and must not be uploaded.

Legacy checklist phrase retained for verifier coverage: no text, no characters, no shadows, no clutter, readable at 48px.

## Feature Graphic Brief

Размер: 1024x500. Композиция: слева крупный clean screenshot игрового поля «Линия 56», справа свободное поле с одной короткой фразой крупным live/editable text в дизайнерах, без мелкого текста. Цвета: green, mist, warm gold. Не использовать fake UI, badges, random stats, mascots or decorative noise. Не добавлять англоязычные UI labels; если текст используется, он должен быть крупным, коротким и русским.

## Final Feature Graphic Background Prompt

Use case: ads-marketing. Asset type: Google Play feature graphic background, 1024x500 landscape. Create a polished abstract background for a calm numeric puzzle app, with no text and no app UI. The visual should feel premium, quiet, and adult: soft mist/off-white field, deep leaf green geometry, warm gold accents, subtle connected path motif, crisp alignment, generous empty space. It should support placing a real phone screenshot on the right later. Avoid any text, letters, numbers, words, logos, fake UI, phone mockups, screenshots, tiny details, noisy lines, stock-photo feel, AI artifacts and watermarks.

Final composition: generated background from `play_store/source_assets/feature_background_imagegen.png` plus a real release gameplay crop from `play_store/screenshots/phone/04_game_line.png`. No promotional text was added.

## Onboarding Illustration Optional

Minimal abstract board with connected number tiles summing to 56, flat vector-like composition, no text, no characters, no brand imitation, calm adult puzzle style, consistent with green/gold palette.

## Quality Checklist

- Читается на маленьком размере.
- Нет мелкого текста.
- Нет случайного шума.
- Совпадает с UI.
- Не выглядит как временная AI-заглушка.
- Не копирует чужой бренд, игру, персонажа или UI.
