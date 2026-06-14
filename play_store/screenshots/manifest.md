# Screenshot Manifest

Phone device: Medium_Phone_API_35_Default emulator, captured at 1080x2400 and exported as 1080x2064, release variant `com.qgrid.mobile`.
Large/tablet capture: same API 35 default emulator with `wm size 1600x2560`, density `320`, exported as 1600x2336, release variant `com.qgrid.mobile`.
Format: 24-bit PNG without alpha; Play screenshot long side is no more than 2x the short side; system status/navigation bars are cropped out of upload images.
Latest recapture: 14 June 2026 after the gameplay cockpit pass, live selected-value trace, darker route dashboard, animated target rail, value-weight tile marks and capture-helper package re-enable hardening. Phone and large/tablet files are newer than the key UI/string/theme inputs, and the feature graphic was rebuilt from the refreshed gameplay screenshot crop.
Capture command: `PYTHONUNBUFFERED=1 ./tools/capture_store_screenshots.py --serial emulator-5560` against a booted clean non-PlayStore `Medium_Phone_API_35_Default` emulator. The script installs the release app, captures phone files from the 1080x2400 app viewport, crops them to 1080x2064 Play-compliant PNGs, captures large/tablet files and crops them to 1600x2336, runs `./gradlew bundleRelease`, rebuilds `play_store/feature_graphic.png` and updates `play_store/upload_checksums.md`.

| File | Purpose | Status |
|---|---|---|
| `phone/01_onboarding.png` | First-launch rules and value proposition | RELEASE_READY |
| `phone/02_home.png` | Home/progress/primary actions | RELEASE_READY |
| `phone/03_game_start.png` | Clean game board before input | RELEASE_READY |
| `phone/04_game_line.png` | Active gameplay with selected line | RELEASE_READY |
| `phone/05_settings.png` | Accessibility/settings screen | RELEASE_READY |
| `tablet/01_onboarding.png` | Large-screen first-launch rules and value proposition | RELEASE_READY |
| `tablet/02_home.png` | Large-screen home/progress/primary actions | RELEASE_READY |
| `tablet/03_game_start.png` | Large-screen clean game board before input | RELEASE_READY |
| `tablet/04_game_line.png` | Large-screen active gameplay with selected line | RELEASE_READY |
| `tablet/05_settings.png` | Large-screen accessibility/settings screen | RELEASE_READY |

Screenshots are real app captures, not fake UI. They should be re-captured after any visual polish, icon replacement, or Play Console screenshot-size decision.
