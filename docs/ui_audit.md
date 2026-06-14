# UI Audit

## Design System

- Colors: leaf green primary, warm gold accent, blue tertiary, clay secondary, mist background.
- Typography: sans-serif, compact mobile hierarchy, no negative letter spacing.
- Spacing: 6/8/12/14/16/20/24/28dp.
- Radii: 8dp-or-less tiles/panels with Material full-width action buttons; no nested decorative cards.
- Elevation: light 1-3dp only for panels/tiles.
- Buttons: icon + text for primary actions, icon buttons for navigation/settings.
- States: selected, hinted, exceeded, disabled undo, completed level.

## Проверено

- First launch: onboarding visible, no text clipping on 1080x2400 API 35.
- Home: progress, start, levels, settings/about visible.
- Game: score panel, 5x5 board, controls visible; cell content descriptions present; the target metric uses `Цель` as the label and `56` as the value without duplicating `56` in both places.
- Hint: message changes to «Начните с подсвеченной клетки.»
- Hint repair state: if the selected line cannot still reach 56, no stale cell is highlighted and the message says to undo or reset the line.
- Cell tap: sum changes from 0 to 14, remaining changes to 42, undo becomes enabled.
- Exceeded state: reducer and UI now keep the state recoverable by blocking additional board input and hint until undo/reset.
- Result state: after win the panel always exposes an explicit action; it shows `Следующий уровень` only when a higher available level id exists and otherwise shows `К уровням`.
- Game back route: when a game is opened from the home CTA, back returns home; when opened from level selection, back returns to the level list, while the result action `К уровням` always opens the level list.
- Result replay: the win panel now includes `Повторить`, so a completed level can be replayed immediately from a clean board without leaving the result screen.
- Motion polish: cell selected/hint/exceeded states use short color/elevation transitions; `Меньше движения` switches those transitions to zero-duration state changes.
- Haptics polish: tactile feedback now follows accepted game-state changes, so rejected repeat/non-adjacent taps do not produce a misleading selection vibration.
- Store screenshot pass: action buttons no longer clip after shortening `Отменить`/`Сбросить` to `Отмена`/`Сброс`.
- Responsive action bar pass: on compact widths the gameplay controls split into two rows, preserving visible labels for `Отмена`, `Подсказка` and `Сброс`; the landscape control column can scroll instead of clipping controls.
- Distinctive UI refresh pass on 14 June 2026: coordinate-grid background, home/onboarding route panels, progress rail, board route overlay, level grid panel and refreshed phone/tablet screenshots make the app visually recognizable without fake UI, mascots or decorative noise.
- Stronger route-map UX pass on 14 June 2026: home now reads as a route cockpit with milestone strip, the level picker is a snake-map instead of a plain grid, selected gameplay cells show waypoint order badges, the score uses a custom route-meter rail, and the warm coordinate-paper background replaces the previous flatter mist surface while preserving 8dp-or-less radii and readable tap targets.
- Gameplay cockpit pass on 14 June 2026: the old three-number score card was replaced with a darker route dashboard, animated target rail and a live line trace that shows the selected values leading toward 56. Idle tiles now carry subtle value-weight bars and palette-coded route accents, so the board reads as a distinctive path-planning surface rather than a generic number grid.
- Adaptive onboarding pass: normal 1080x2400 viewport centers the first-run screen; compact 720x1280 with `font_scale=1.3` keeps the button fully visible above system navigation.
- Compact About/privacy pass: 720x1280, density 320, `font_scale=1.3`; top and scrolled-bottom screenshots show the privacy heading, local-data/no-services/backup/delete copy without relying on one long paragraph.
- Wide/large pass: 2400x1080 landscape override uses a dedicated compact onboarding row layout; 1600x2560 tall override keeps onboarding readable with no overlap.
- Crash buffer after manual flow: empty.

## Оставшиеся UI/Asset Риски

- Store icon is present and Play-format verified.
- Feature graphic was rebuilt after rejecting the previous text-heavy concept. The final `play_store/feature_graphic.png` uses a generated no-text background plus a real gameplay crop, with no fake UI or promotional badge labels.
- Dedicated large/tablet Play screenshots were captured at 1600x2560 from the real release app and exported as 1600x2336 after removing system bars; phone screenshots remain the primary phone set and are exported as 1080x2064.
- The gameplay cockpit pass is reflected in the current phone and large/tablet Play screenshots captured from clean `Medium_Phone_API_35_Default`; feature graphic, upload checksums and the internal store asset review sheet were refreshed afterward.
- Store asset review sheet generated at `play_store/store_asset_review_sheet.png` shows the current Play icon, feature graphic, phone screenshots and large/tablet screenshots side by side for local crop review. It is internal evidence only and must not be uploaded to Play Console.
Latest home progress visual polish: the home progress bar disables the Material3 stop indicator so `0 / 36` does not show a dark end dot that can read as completed progress. The bar still exposes localized progress semantics through `ProgressBarRangeInfo` and `Прогресс: 0 из 36 уровней.`.
