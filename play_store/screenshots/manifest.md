# Screenshot Manifest

Phone device: Medium Phone API 35 emulator, captured at 1080x2400 and exported as 1080x2064, release variant `com.qgrid.mobile`.
Large/tablet capture: same API 35 emulator with `wm size 1600x2560`, density `320`, exported as 1600x2336, release variant `com.qgrid.mobile`.
Format: 24-bit PNG without alpha; Play screenshot long side is no more than 2x the short side; system status/navigation bars are cropped out of upload images.
Latest recapture: 6 June 2026 after ImageGen icon/onboarding brand-mark alignment, portrait onboarding spacing polish and launcher/theme resource changes, followed by Play screenshot aspect-ratio normalization and system-bar crop. Phone and large/tablet files are newer than the key UI/string/theme inputs, and the feature graphic was rebuilt from the refreshed gameplay screenshot crop.
Capture command: `ANDROID_SERIAL=emulator-5562 ./tools/capture_store_screenshots.py --serial emulator-5562` against a booted `Medium_Phone_API_35_Default` emulator. The script installs the release app, captures phone files from the 1080x2400 app viewport, crops them to 1080x2064 Play-compliant PNGs, captures large/tablet files and crops them to 1600x2336, rebuilds `play_store/feature_graphic.png` and updates `play_store/upload_checksums.md`. During the latest run the AVD exited after `tablet/04_game_line.png`; `tablet/05_settings.png`, feature graphic rebuild and checksum refresh were completed immediately afterward through the same capture helper functions on the restarted `emulator-5562`.

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
