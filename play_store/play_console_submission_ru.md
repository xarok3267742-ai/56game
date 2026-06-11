# Play Console Submission Fields - RU

Этот файл нужен как copy-ready handoff для публикации. Он не заменяет проверку в Play Console: финальные ответы зависят от аккаунта издателя, публичного privacy URL и результатов тестового трека.

Для App content / policy forms use the field-by-field answer sheet in `play_store/app_content_answers_ru.md`. External owner-controlled inputs are isolated in `play_store/owner_release_inputs.md`.

Use `play_store/upload_runbook_ru.md` for the final manual upload sequence, including preflight commands, exact assets, Do Not Upload list, release-track order and stop conditions.

## App Identity

- Package name: `com.qgrid.mobile`
- Version code: `1`
- Version name: `1.0.0`
- App name: `Линия 56`
- Default language: Russian (`ru-RU`)
- App or game: Game
- Category: Puzzle
- Monetization: free, no ads, no in-app purchases

## Store Listing

### App Name

Линия 56

### Short Description

Соединяйте числа и соберите сумму ровно 56.

### Full Description

«Линия 56» - спокойная числовая головоломка для коротких сессий без интернета.

Выбирайте соседние клетки, стройте непрерывную линию и следите за суммой. Цель простая: остановиться ровно на 56. Если сумма стала больше, отмените ход или начните линию заново.

Что внутри:

- 36 коротких уровней;
- движение по горизонтали, вертикали и диагонали;
- подсказка, отмена хода и сброс линии;
- сохранение прогресса на устройстве;
- настройки тактильного отклика, контраста и уменьшения движения;
- без рекламы, аккаунтов, платежей и обязательного интернета.

Игра подходит для спокойной тренировки внимания, счёта и аккуратного планирования на несколько минут в день.

### Release Notes

Первый релиз: 36 уровней, подсказки, отмена хода, сброс линии, сохранение прогресса и настройки доступности.

## Upload Assets

- App bundle: `app/build/outputs/bundle/release/app-release.aab`
- Release package/version: `com.qgrid.mobile`, versionCode `1`, versionName `1.0.0`
- Store icon: `play_store/icon/play_icon_512.png`
- Feature graphic: `play_store/feature_graphic.png`
- Phone screenshots:
  - `play_store/screenshots/phone/01_onboarding.png`
  - `play_store/screenshots/phone/02_home.png`
  - `play_store/screenshots/phone/03_game_start.png`
  - `play_store/screenshots/phone/04_game_line.png`
  - `play_store/screenshots/phone/05_settings.png`
- Large/tablet screenshots:
  - `play_store/screenshots/tablet/01_onboarding.png`
  - `play_store/screenshots/tablet/02_home.png`
  - `play_store/screenshots/tablet/03_game_start.png`
  - `play_store/screenshots/tablet/04_game_line.png`
  - `play_store/screenshots/tablet/05_settings.png`

## App Content

- App access: no restricted sections, no login, no account.
- Ads: no.
- Privacy policy: required. Enter `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` after filling the Play Console support/contact fields used by the policy inquiry mechanism and rechecking the URL with `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.
- Data collection: no collected user data.
- Data sharing: no shared user data.
- Analytics: none.
- Crash reporting: none.
- Encryption in transit: no user data is transmitted by the app.
- Account deletion: not applicable, app has no accounts.
- Financial features: none.
- Health features: none.
- Government features: none.
- AI-generated content disclosure: not applicable to in-app user experience; generated store background asset is documented as a static creative source only.
- Field-by-field source: `play_store/app_content_answers_ru.md`.

## Content Rating Posture

- Category: Games / Puzzle.
- Violence: none.
- Fear or shock: none.
- Sexual content: none.
- Language: none.
- Drugs, alcohol or tobacco: none.
- Gambling or simulated gambling: none.
- Real-money purchases: none.
- User-generated content: none.
- Online interaction: none.
- Location sharing: none.

## Target Audience Decision

The app is a simple numeric puzzle, but the publisher must choose target age groups in Play Console. If the publisher does not intend to market to children or enter Google Play Families, use an age target that matches that policy decision and keep store copy/screenshots neutral.

## Final Manual Gates

- Resolve owner inputs from `play_store/owner_release_inputs.md`.
- Fill the Play Console support/contact fields used by the privacy policy inquiry mechanism.
- Publish the privacy policy on a public HTTPS URL.
- Back up `private/signing/qgrid-upload.p12` and `keystore.properties` before upload.
- Run required internal/closed testing tracks for the publisher account type.
- Re-run `./tools/run_final_local_gate.py` and require `final_local_gate_ok` immediately before uploading.
