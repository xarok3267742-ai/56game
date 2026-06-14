# Google Play Upload Checksums

Verified for the current local release candidate after the 14 June 2026 distinctive UI/UX refresh, Play screenshot recapture, feature graphic rebuild and git/VCS metadata refresh. Rebuild or recapture any upload artifact only if this file is updated and `./tools/verify_release.py` passes again.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `app/build/outputs/bundle/release/app-release.aab` | 2956105 | `f69f0f6d8efbaf31ac624d507e43ed7c700a36c420a5e3c480edb7d7f0bebe95` |
| `play_store/icon/play_icon_512.png` | 274405 | `d9272798e3241fd1bc05f71620ed297a45ccbeb3691eb8a7184eb5d7a948f27c` |
| `play_store/feature_graphic.png` | 420032 | `b79e7721f6d93d5556bf9cf940e2ee8db8f6dee04116992b282c37c41883ffc7` |
| `play_store/screenshots/phone/01_onboarding.png` | 310727 | `44d166684371a4c13cf395054594e0e0be90fca85d08b6279b361cc1a78e1ae0` |
| `play_store/screenshots/phone/02_home.png` | 241444 | `ff7606742e74225e77d56abaed59309c991b99eeccdc50b545ddf1ec98d3cf3a` |
| `play_store/screenshots/phone/03_game_start.png` | 228401 | `41c198a9dc9e574fd47ea528f41ae0cf4ddb10d93c17b0b9a7c561bd1c53ebf6` |
| `play_store/screenshots/phone/04_game_line.png` | 236432 | `6b360dd33470f3c8310718f0bc4afbc2b6cf0f0c4fdda93ea02064fa166f8b38` |
| `play_store/screenshots/phone/05_settings.png` | 225071 | `02a051466ca12c0741e7359b0dd0bd2403ed78a7633406d1d71be375425e9d20` |
| `play_store/screenshots/tablet/01_onboarding.png` | 205730 | `d00fe634633eed892fd0eb3554bef8c4b51e5f21d70cf47e34051b13d367f4e4` |
| `play_store/screenshots/tablet/02_home.png` | 171591 | `f75405e03e5158672eb5a270961adfa33ff2c3949db2c00f89db382f7bb54519` |
| `play_store/screenshots/tablet/03_game_start.png` | 188686 | `2ac0e0aa5eea1cc776efbcaf89fd6ba79fab457787991827f9d38ad2ad07bd4f` |
| `play_store/screenshots/tablet/04_game_line.png` | 193515 | `0d923afd1ea2e16fe0c6afba9f15e8996f8c2126322928e5014e3c25d175c3c2` |
| `play_store/screenshots/tablet/05_settings.png` | 140500 | `169064f905f19df0da1e03f8aa6b41cac286a7698684010a094a56f10dc0bae2` |

Do not upload release APK outputs, debug APKs, androidTest APKs, source-only images, rejected assets, local mask previews, keystore files or local property files.
