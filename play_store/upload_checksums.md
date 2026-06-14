# Google Play Upload Checksums

Verified for the current local release candidate after the 14 June 2026 distinctive UI/UX refresh, Play screenshot recapture, feature graphic rebuild and git/VCS metadata refresh. Rebuild or recapture any upload artifact only if this file is updated and `./tools/verify_release.py` passes again.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `app/build/outputs/bundle/release/app-release.aab` | 2984214 | `0af8449f4da9fbf8933d5e77445f8725d42deb43eda4b059ac8eacb42cc1d9d0` |
| `play_store/icon/play_icon_512.png` | 274405 | `d9272798e3241fd1bc05f71620ed297a45ccbeb3691eb8a7184eb5d7a948f27c` |
| `play_store/feature_graphic.png` | 459388 | `649e8d4ff7d5a6bdb0697f0e39d55243d91c88d87485218b0ffa25a9e803f477` |
| `play_store/screenshots/phone/01_onboarding.png` | 274755 | `9a443d0816e3cb3b79de0054b16ed10115a5206cc1b41fa44f29eb468f6082fa` |
| `play_store/screenshots/phone/02_home.png` | 249907 | `5f650e791ea6a0fecdab1164c8e88deb3b193bffa522f36314c7def4e33f5e55` |
| `play_store/screenshots/phone/03_game_start.png` | 274129 | `299a9daa58568aff4faa616f60b057e24c312f1886408ec0a0e10cf60db2d415` |
| `play_store/screenshots/phone/04_game_line.png` | 282683 | `87f3d96dd77fdee52af346ba2970de5f4dfcb82e47ecf1998934a05e940c1066` |
| `play_store/screenshots/phone/05_settings.png` | 182092 | `12a1f1f7c37ffad24f779cc126684865aba87a0fabc8bb20f369d510d5ec49c5` |
| `play_store/screenshots/tablet/01_onboarding.png` | 213235 | `89d751b1ac02b3e16ee65829f6032461cb5a669c26a96d75d64f9ef29e368941` |
| `play_store/screenshots/tablet/02_home.png` | 198806 | `9414fd0bc3cf14134179bdd70495fe09749258693ad7416e2e71e155fed3811a` |
| `play_store/screenshots/tablet/03_game_start.png` | 277962 | `a218ae1c36e322527ee16d68e194c0c32a592a320153965f0df87df177e1e1b7` |
| `play_store/screenshots/tablet/04_game_line.png` | 281653 | `0426426c591e4aa31b9034dbdfaa5bd10dfd3c3b4f4dd7786807d07ef4002be3` |
| `play_store/screenshots/tablet/05_settings.png` | 144436 | `de42bf34d7b88a61f88bee727bd2320af830c1cb7292e6acb7999f8dc30a1e5d` |

Do not upload release APK outputs, debug APKs, androidTest APKs, source-only images, rejected assets, local mask previews, keystore files or local property files.
