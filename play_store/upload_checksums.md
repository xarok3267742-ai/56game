# Google Play Upload Checksums

Verified for the current local release candidate after the 14 June 2026 distinctive UI/UX refresh, Play screenshot recapture, feature graphic rebuild and git/VCS metadata refresh. Rebuild or recapture any upload artifact only if this file is updated and `./tools/verify_release.py` passes again.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `app/build/outputs/bundle/release/app-release.aab` | 2969759 | `e5e1744a2c304cc42e960ba2bb9693cb8671fe47e1231f384c101cea4b90060d` |
| `play_store/icon/play_icon_512.png` | 274405 | `d9272798e3241fd1bc05f71620ed297a45ccbeb3691eb8a7184eb5d7a948f27c` |
| `play_store/feature_graphic.png` | 430476 | `06eb4500eeb1df355544a6dec29b143aa199dba1ca73f78de37ac5b52b9cf963` |
| `play_store/screenshots/phone/01_onboarding.png` | 274755 | `9a443d0816e3cb3b79de0054b16ed10115a5206cc1b41fa44f29eb468f6082fa` |
| `play_store/screenshots/phone/02_home.png` | 249907 | `5f650e791ea6a0fecdab1164c8e88deb3b193bffa522f36314c7def4e33f5e55` |
| `play_store/screenshots/phone/03_game_start.png` | 223565 | `9ed6ffcbfc889ee60c24f2f982d8ae502c19e0093811dc77c508eb23b6db49d6` |
| `play_store/screenshots/phone/04_game_line.png` | 235731 | `d896c3ae0ee1cc6622e5a12aa16d5abbacf456743ff55fa6ac1b354fa6867cd7` |
| `play_store/screenshots/phone/05_settings.png` | 182092 | `12a1f1f7c37ffad24f779cc126684865aba87a0fabc8bb20f369d510d5ec49c5` |
| `play_store/screenshots/tablet/01_onboarding.png` | 213235 | `89d751b1ac02b3e16ee65829f6032461cb5a669c26a96d75d64f9ef29e368941` |
| `play_store/screenshots/tablet/02_home.png` | 198806 | `9414fd0bc3cf14134179bdd70495fe09749258693ad7416e2e71e155fed3811a` |
| `play_store/screenshots/tablet/03_game_start.png` | 217578 | `6bfccc0f66ebcccc71cc04e2a5cf0c8f640792d2820d0d00c9558985916768d9` |
| `play_store/screenshots/tablet/04_game_line.png` | 222841 | `27d996b18691c919894b87ca6058b02c45a33577c11154f7a2ebf79f96ada45c` |
| `play_store/screenshots/tablet/05_settings.png` | 144436 | `de42bf34d7b88a61f88bee727bd2320af830c1cb7292e6acb7999f8dc30a1e5d` |

Do not upload release APK outputs, debug APKs, androidTest APKs, source-only images, rejected assets, local mask previews, keystore files or local property files.
