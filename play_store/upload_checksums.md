# Google Play Upload Checksums

Verified for the current local release candidate after the ImageGen icon/onboarding brand-mark alignment, Play screenshot aspect-ratio normalization, system-bar crop and git/VCS metadata refresh. Rebuild or recapture any upload artifact only if this file is updated and `./tools/verify_release.py` passes again.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `app/build/outputs/bundle/release/app-release.aab` | 2930928 | `3affd5cc6de7735d7cb9cc4f381e114caa0b20d6bfa933621d596d24dc2e3043` |
| `play_store/icon/play_icon_512.png` | 274405 | `d9272798e3241fd1bc05f71620ed297a45ccbeb3691eb8a7184eb5d7a948f27c` |
| `play_store/feature_graphic.png` | 410321 | `f6fb4bce8dea5e687b141ce1bf38e9df0f5ce1d8fd35a7dd3420d1d100fb71da` |
| `play_store/screenshots/phone/01_onboarding.png` | 133859 | `601df1b615497e558beb527ba347107891c26cafe44206e0792cba9487e2a198` |
| `play_store/screenshots/phone/02_home.png` | 79029 | `12994544ba37303d1f22035618e92e5f219c335a18c9ad98f17da714315b2fbc` |
| `play_store/screenshots/phone/03_game_start.png` | 101380 | `e309ee6f61a4271d22517f3b8c3cb373348393390f13e331a1ea3f420d31f231` |
| `play_store/screenshots/phone/04_game_line.png` | 105842 | `46e0a988f2afb7e97ef180b369e68e780205ae3b5baef4249a3c2ab722be0832` |
| `play_store/screenshots/phone/05_settings.png` | 64334 | `d0ed2741d12bbbe01c2e0f0ba30ee79260c835b22c734ea7da0ac9029eccf0db` |
| `play_store/screenshots/tablet/01_onboarding.png` | 98888 | `bcf0029d9144ccb3669a68d964136a105e7d542e4a6492e5b13c1f1a1283de01` |
| `play_store/screenshots/tablet/02_home.png` | 65962 | `c279bb65d5451d113dc3718fb4b70874d2fa451439254cedadda60bd2a4c93b5` |
| `play_store/screenshots/tablet/03_game_start.png` | 86340 | `62c43735e2444bfca497c81b3a8cc02aa43a75385df6d3fef70fcaaa8edcd27a` |
| `play_store/screenshots/tablet/04_game_line.png` | 89284 | `b25dd2c29a28190801e11533d86a8a579b983b4fa906688118a7ac97ed0e8d8e` |
| `play_store/screenshots/tablet/05_settings.png` | 56800 | `aa2398c675aab27f941c99b3eef97227dff11bd39345ebbb6c02c31d65c11a3a` |

Do not upload release APK outputs, debug APKs, androidTest APKs, source-only images, rejected assets, local mask previews, keystore files or local property files.
