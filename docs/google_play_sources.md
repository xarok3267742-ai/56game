# Google Play Sources

Checked on 12 June 2026 against official Google Play / Android Developers sources.

Latest source spot-check on 6 June 2026 after the ImageGen icon replacement and final local continuation audit: target API, Android App Bundle upload format, personal-account closed testing, preview assets, Google Play icon design specifications, Data Safety, User Data/privacy policy, content rating and target audience pages were rechecked against the local release candidate.

Continuation source spot-check on 6 June 2026: official Google Play / Android Developers pages were rechecked again for target API 35+ submission posture, Android App Bundle upload/use in Play Console, public non-PDF privacy-policy URL requirements, Data Safety disclosure requirements and the personal-account closed-testing owner gate. No local release-candidate change was required because this project already targets SDK 36, builds a signed AAB, documents no-data/no-ads/no-permission posture and keeps privacy URL, Play Console forms and testing tracks as owner-controlled external gates.

Latest source spot-check on 11 June 2026: official Google Play / Android Developers pages were rechecked for target API 35+ submission posture, Android App Bundle upload/use in Play Console, Android 15+ 16 KB page-size compatibility, preview asset dimensions/format, Google Play icon requirements, Data Safety, User Data/privacy policy, content rating, target audience and personal-account closed-testing owner gates. The Google Play policy announcement page was also checked for the 15 April 2026 update set; no local product change was required because this project has no Contacts data access, no Location data access, no Health apps scope, no prediction market feature and no News app scope.

Latest source spot-check on 12 June 2026: official Google Play / Android Developers pages were rechecked for target API level, 16 KB page-size compatibility, Data Safety, personal-account testing, Developer Program Policy effective 27 May 2026, Play Console developer account required information and Android developer verification/package-name registration rollout. Local code did not require changes, but the owner handoff now explicitly treats Play Console developer identity/profile completion and package-name registration for `com.qgrid.mobile` as external owner evidence before production rollout.

- Target API level requirements: https://support.google.com/googleplay/android-developer/answer/11926878?hl=en
- Target API policy summary: https://support.google.com/googleplay/android-developer/answer/11917020?hl=en
- Android 15+ 16 KB page-size compatibility: https://developer.android.com/guide/practices/page-sizes
- Android App Bundle format: https://developer.android.com/guide/app-bundle/app-bundle-format
- Android App Bundle FAQ: https://developer.android.com/guide/app-bundle/faq?hl=en
- Personal developer account testing requirements: https://support.google.com/googleplay/android-developer/answer/14151465?hl=en
- Internal/closed/open testing setup: https://support.google.com/googleplay/android-developer/answer/9845334?hl=en
- Store listing app icon, short description, screenshots and feature graphic requirements: https://support.google.com/googleplay/android-developer/answer/9866151?hl=en
- Google Play icon design specifications: https://developer.android.com/distribute/google-play/resources/icon-design-specifications
- Preview assets requirements and recommendations: https://support.google.com/googleplay/android-developer/answer/1078870?hl=en
- Store listing metadata policy: https://support.google.com/googleplay/android-developer/answer/9898842?hl=en
- Data Safety form requirements: https://support.google.com/googleplay/android-developer/answer/10787469?hl=en
- User Data / privacy policy requirements: https://support.google.com/googleplay/android-developer/answer/9888076
- User Data policy detail: https://support.google.com/googleplay/android-developer/answer/10144311?hl=en
- Content Ratings: https://support.google.com/googleplay/android-developer/answer/9898843?hl=en
- Target audience and app content settings: https://support.google.com/googleplay/android-developer/answer/9867159?hl=en
- Google Play policy announcements: https://support.google.com/googleplay/android-developer/answer/16926792?hl=en
- Google Play Developer Program Policy: https://support.google.com/googleplay/android-developer/answer/17105854?hl=en
- Required information to create a Play Console developer account: https://support.google.com/googleplay/android-developer/answer/13628312?hl=en
- Android developer verification/package-name registration walkthrough: https://support.google.com/googleplay/android-developer/answer/16471116?hl=en

Current official requirements used for the release-candidate audit:

- New apps and app updates must target Android 15/API 35 or higher from 31 August 2025; this project uses `targetSdk = 36`.
- Starting 1 November 2025, new apps and updates submitted to Google Play and targeting Android 15/API 35+ devices must support 16 KB page sizes on 64-bit devices; the current signed AAB contains 8 native `.so` files and every ELF `PT_LOAD` segment has alignment `0x4000` / 16,384 bytes, while the local release APK packages those libraries uncompressed at 16 KB ZIP data offsets with `extractNativeLibs=false`.
- Google Play upload format is Android App Bundle; the current release artifact is a signed `.aab`.
- Feature graphic requirement is JPEG or 24-bit PNG without alpha at 1024x500; the current feature graphic is 1024x500 24-bit PNG without alpha.
- Screenshot requirement is JPEG or 24-bit PNG without alpha, 320-3840 px per side, with the long side no more than 2x the short side; current upload screenshots are 24-bit PNGs without alpha and satisfy that ratio.
- Play preview assets include screenshots and feature graphic; current upload set includes five phone screenshots and five large/tablet screenshots captured from the real release app.
- Data Safety must be completed for Play tracks beyond internal-only use, and even no-data apps must complete the form and provide a privacy policy link.
- User Data policy requires a privacy policy link in Play Console plus an in-app link or text. The policy must include developer/contact mechanism and be hosted on an active, publicly accessible, non-geofenced, non-PDF, non-editable URL; apps that do not access personal and sensitive user data still must submit a privacy policy.
- Content rating questionnaire is required for each new app submitted to Play Console.
- Target audience/app content declarations are required for new apps, and selecting child age groups triggers additional Families-policy duties.
- For a newly created personal developer account, production access requires a closed test with at least 12 opted-in testers for 14 continuous days before applying.
- Play Console developer account/profile information and identity verification are owner-controlled external setup requirements. Google's Android developer verification rollout also requires verified developers and registered package names, with regional enforcement starting in late 2026; the owner handoff now records package-name registration for `com.qgrid.mobile` without storing private account values.

Current project alignment:

- `targetSdk = 36`, which is above the Android 15/API 35 requirement for new apps and updates.
- Native library 16 KB page-size posture is locally verifier-gated: `tools/verify_release.py` inspects every `.so` in the signed AAB and requires `PT_LOAD` alignment at least 16,384 bytes; `tools/verify_play_generated_apk.py` performs the same ELF check for a downloaded Play-generated APK and also requires uncompressed native libraries, 16 KB ZIP data alignment and `extractNativeLibs=false`.
- Release artifact is a signed `.aab`, which is the Google Play publishing format.
- App name `Линия 56` is 8 characters, under the 30-character metadata limit.
- Short description `Соединяйте числа и соберите сумму ровно 56.` is 43 characters, under the 80-character limit.
- Store icon is 512x512 32-bit PNG with alpha and under 1024KB; it is full-square with no transparent pixels or baked-in masking, because Google Play dynamically applies its own rounded mask and shadow.
- Feature graphic is 1024x500 24-bit PNG without alpha and was rebuilt after rejecting the previous text-heavy concept.
- Phone screenshots are 1080x2064 24-bit PNGs without alpha, cropped from real 1080x2400 app captures to remove system bars and satisfy Play's 2:1 side-ratio rule.
- Phone screenshot set has 5 screenshots, exceeding the minimum of 2 screenshots; for games it also exceeds the highly recommended 3 portrait screenshots with at least 1080x1920 resolution.
- Large/tablet screenshots are 1600x2336 24-bit PNGs without alpha, cropped from real 1600x2560 app captures to remove system bars, with 5 screenshots in `play_store/screenshots/tablet`.
- Preview asset alt text is prepared in `play_store/asset_alt_text_ru.md`.
- TalkBack exploratory pass is complete locally on an API 36 Play Store AVD with Android Accessibility Suite; artifacts are under `docs/qa_artifacts`.
- Data Safety handoff says no user data is collected or shared; the app has no ads, analytics, crash reporting SDK, accounts, payments, network permission or device identifier collection.
- Privacy policy source and HTML are prepared with a Google Play listing support-contact inquiry mechanism, but populated Play Console support/contact fields and a public non-PDF HTTPS URL remain required external inputs.
- Play Console developer account/profile verification and package-name registration for `com.qgrid.mobile` remain external owner-controlled inputs and must be recorded only through safe evidence wording.
- Content rating posture is Games / Puzzle with no violence, fear, sexual content, language, drugs, gambling, purchases, user-generated content, online interaction or location sharing.
- Target audience handoff recommends a non-child-directed 13+ posture unless the publisher intentionally chooses a child-directed/Families release path.
- If the Play Console account is a personal account created after 13 November 2023, closed testing with at least 12 opted-in testers for 14 continuous days is expected before production availability.
