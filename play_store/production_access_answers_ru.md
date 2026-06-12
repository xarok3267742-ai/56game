# Production Access Answers - RU

Этот файл помогает владельцу подготовить безопасные ответы для Play Console `Apply for production access`, если аккаунт требует closed testing перед production. Он не заменяет реальные данные тестирования и не доказывает production access локально.

Источник: Google Play Console Help `App testing requirements for new personal developer accounts` (`https://support.google.com/googleplay/android-developer/answer/14151465?hl=en`). По этой справке после выполнения closed-testing критериев Play Console может попросить ответы в трёх блоках: about your closed test, about your app/game и production readiness.

Не записывать сюда персональные данные тестеров, email addresses, invite links, private tester URLs, Play account tokens, screenshots with account data, passwords, keystore contents or private keys.

## Fixed App Facts

- App name: `Линия 56`.
- Package: `com.qgrid.mobile`.
- Category: Game / Puzzle.
- Version: versionCode `1`, versionName `1.0.0`.
- Monetization: free, no ads, no in-app purchases.
- Accounts/login: none.
- Network/data posture: offline-first, no `INTERNET`, no `ACCESS_NETWORK_STATE`, no user data collected or shared.
- Core value: calm numeric puzzle where the player connects neighboring numbers until the selected path sums exactly to 56.

## About Your Closed Test

Owner-only fields to fill after the real closed test:

- Tester recruitment difficulty: not yet available locally.
- Tester engagement summary: not yet available locally.
- Tester feedback summary: not yet available locally.
- Feedback collection method: not yet available locally.

Safe answer guidance:

- Mention tester count and duration only as aggregate facts, for example `at least 12 opted-in testers for at least 14 continuous days`, after Play Console shows that this is true.
- Summarize engagement without private identities: which flows testers used, whether they completed onboarding, played levels, used hints/undo/reset/settings and restarted the app.
- Summarize feedback themes without personal data: clarity of rules, readability of numbers, difficulty curve, control comfort, crashes or no crashes, confusing states and any accessibility comments.
- State how feedback was collected without private links or emails: Play testing feedback, owner tracker, support channel or direct tester notes, but do not record the actual private channel URL.

Draft structure:

```text
Recruiting testers was [easy / moderate / difficult] because [safe aggregate reason].
During the closed test, testers used the main game loop: onboarding, level selection, selecting neighboring numbers to reach 56, hints, undo/reset, settings and relaunch.
Feedback themes were: [safe aggregate feedback themes]. No tester names, email addresses or invite links are included here.
Feedback was collected through [safe channel type], then summarized in the owner tracker without personal data.
```

## About Your App Or Game

Copy-safe draft answer for intended audience:

```text
The intended audience is general puzzle players age 13+ who want a short offline numeric logic game. The app is not child-directed and does not include ads, purchases, accounts, online interaction, gambling, user-generated content or data collection.
```

Copy-safe draft answer for what makes the game stand out:

```text
Линия 56 is focused on one clear rule: connect neighboring numbered cells until the path sum is exactly 56. It is designed for short calm sessions, uses deterministic solver-verified levels, supports undo/reset/hints and works offline without accounts, ads or analytics.
```

Expected first-year installs:

- Owner must choose the nearest Play Console range. For a first release with no paid marketing committed in this repository, use the lowest realistic range unless the publisher has an external launch plan.

## Production Readiness

Owner-only fields to fill after the real closed test:

- Changes made from closed-test feedback: not yet available locally.
- Production readiness decision summary: not yet available locally.

Local evidence available before upload:

- `./tools/run_final_local_gate.py --include-hosted-privacy` returns `final_local_gate_ok`.
- `./tools/verify_release.py` returns `release_verification_ok`.
- `./tools/print_publication_readiness.py --check-recorded-privacy-url` returns `publication_readiness_local_ready_external_pending` until external evidence is recorded.
- Play-generated APK review must pass `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` after upload.
- Production-ready owner confirmation requires `./tools/print_publication_readiness.py --check-recorded-privacy-url --require-production-ready`.

Copy-safe draft answer for changes made from testing:

```text
Based on closed-test feedback, we reviewed the core puzzle flow, onboarding clarity, number readability, hint/undo/reset behavior, settings and relaunch behavior. Changes made before production were: [owner summary of actual changes or "no code changes were required after the closed test; tester feedback confirmed the release candidate was understandable and stable"]. No tester personal data is included.
```

Copy-safe draft answer for why it is ready:

```text
The app is ready for production because the release candidate has passed local unit/lint/build/release verification, has a signed AAB, verified Play assets, no ads, no accounts, no user data collection, no network permissions, disabled Android backup and a hosted privacy policy. The closed test completed the required account-specific tester/time gate, Play-generated artifact review passed, pre-launch report has no blocking issues and no unresolved Play policy warnings remain.
```

## Evidence To Record Elsewhere

Record final external facts in `play_store/play_console_post_upload_evidence_ru.md`, not in this draft sheet:

- Closed testing required for this account.
- Closed testing status if required.
- Production access status if required.
- Pre-launch report result.
- Reproducible crashes in pre-launch report.
- Play policy warnings.

The production-access application is not complete until Play Console production access is granted or approved, or owner evidence safely records that it is not required for this account.
