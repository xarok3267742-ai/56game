# Closed Testing Handoff - RU

Этот файл помогает владельцу провести Google Play closed testing для `Линия 56` без записи персональных данных тестеров в репозиторий. Он не доказывает прохождение closed testing локально и не заменяет факты в Play Console.

Источник: Google Play Console Help `App testing requirements for new personal developer accounts` (`https://support.google.com/googleplay/android-developer/answer/14151465?hl=en`). По этой справке для применимых новых personal developer accounts production access требует closed test with at least 12 testers who have been opted-in for at least the last 14 days continuously before applying for production access. Страница также рекомендует начинать с internal testing, давать тестерам clear instructions, просить использовать как можно больше функций и собирать feedback through Play Console or a private owner channel.

Не записывать сюда tester names, email addresses, invite links, private tester URLs, Play account tokens, screenshots with account data, passwords, keystore contents or private keys.

## Fixed App Facts

- App name: `Линия 56`.
- Package: `com.qgrid.mobile`.
- Version: versionCode `1`, versionName `1.0.0`.
- Category: Game / Puzzle.
- Monetization: free, no ads, no in-app purchases.
- Accounts/login: none.
- Network/data posture: offline-first, no `INTERNET`, no `ACCESS_NETWORK_STATE`, no user data collected or shared.

## Owner Closed-Test Setup

- Run `./tools/run_final_local_gate.py --include-hosted-privacy` and require `final_local_gate_ok` immediately before upload-day setup.
- Upload the signed AAB to internal testing first.
- Inspect Play-generated artifacts before inviting external testers; use `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` when a Play-generated APK is available.
- If the publisher account requires closed testing, create a closed testing track after the app setup is complete.
- Manage tester access outside this repository. A private Play Console opt-in link, Google Group, tester email list or support channel must not be committed.
- Keep at least 12 opted-in testers for at least 14 continuous days before applying for production access.
- Track tester count, opt-in continuity and feedback only in Play Console or an owner-controlled tracker.
- Record only aggregate safe evidence in `play_store/play_console_post_upload_evidence_ru.md`.

## Tester Task Script

Send testers a short private note outside the repository. Keep it factual and avoid collecting unnecessary personal data:

```text
Please stay opted in to the closed test for at least 14 continuous days.
Install the current Google Play test build of Линия 56.
Launch the app, finish onboarding, open level selection, play several levels, use hint, undo, reset, settings, background/return and relaunch.
Please report crashes, confusing rules, unreadable numbers, uncomfortable controls, difficulty spikes, accessibility issues or store-listing problems through the agreed private feedback channel or Play testing feedback.
```

## Feedback Topics

Ask for aggregate feedback on:

- Onboarding clarity: whether the goal `sum exactly 56` is understood.
- Number readability: tile contrast, font size and selection state.
- Controls: tap comfort, adjacency rule clarity, undo/reset/hint behavior.
- Difficulty: first five levels, later levels, any impossible-looking board.
- Stability: crashes, freezes, bad relaunch state or lost progress.
- Accessibility: high contrast, reduced motion, text size, TalkBack basics if available.
- Store listing preview: icon, feature graphic, phone screenshots and tablet screenshots have no damaging crops.

## Safe Feedback Summary Template

Record only aggregate notes in the owner tracker, then copy only safe summary lines to `play_store/production_access_answers_ru.md` and `play_store/play_console_post_upload_evidence_ru.md` when needed:

```text
Closed-test engagement summary: testers used onboarding, level selection, gameplay, hints, undo/reset, settings and relaunch flows.
Closed-test feedback themes: [aggregate themes only].
Closed-test changes made: [owner summary of actual changes or "no code changes were required after the closed test"].
No tester names, email addresses, invite links or private tester URLs are recorded.
```

## Evidence Phrases Accepted By Local Gate

Use these wording patterns after the real Play Console facts exist:

- `Closed testing required for this account: yes.`
- `Closed testing status if required: completed required closed testing with 12 opted-in testers for 14 continuous days.`
- `Production access status if required: Play Console production access granted.`

If Play Console does not require closed testing for this account:

- `Closed testing required for this account: no.`
- `Closed testing status if required: not required for this account.`
- `Production access status if required: not required for this account.`

## Stop Conditions

Do not apply for production access or promote to production if:

- fewer than 12 testers are opted in when Play Console requires the closed-test gate;
- the 14-day continuity window is not complete;
- tester evidence contains emails, private links, invite links, screenshots with account data or other personal data;
- Play-generated APK review has not passed;
- Play pre-launch report has reproducible crashes or unresolved policy warnings;
- feedback reveals a blocker in onboarding, level completion, settings, persistence or store asset preview.
