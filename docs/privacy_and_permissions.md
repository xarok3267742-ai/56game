# Privacy And Permissions

## Данные

Приложение не собирает персональные данные.

Локально сохраняются только:

- факт прохождения onboarding;
- список пройденных уровней;
- последний уровень;
- настройки haptics/high contrast/reduce motion.

Android backup отключён в manifest через `android:allowBackup="false"`, поэтому локальный progress/settings не включаются в Google cloud backup или device-to-device restore.

## Permissions

Manifest не запрашивает dangerous/platform runtime permissions. Location, camera, microphone, contacts, storage permissions не используются. `INTERNET` и `ACCESS_NETWORK_STATE` также не запрашиваются, поэтому приложение не имеет сетевой зависимости на уровне manifest. Android backup отключён. APK содержит только app-private AndroidX dynamic receiver permission, который не даёт доступ к пользовательским данным.

`tools/verify_release.py` проверяет source manifest, merged debug/release manifests and debug APK permissions. Текущий binary permission gate проходит: unexpected platform/runtime permissions отсутствуют, а единственный `uses-permission` в debug APK - generated `com.qgrid.mobile.debug.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`.

## Third-party Services

- Analytics: нет.
- Crash logs: нет.
- Ads: нет.
- Payments/IAP: нет.
- Accounts: нет.
- Device identifiers: нет.
- User-generated content: нет.

## Google Play Data Safety

Можно указать: данные не собираются и не передаются третьим лицам. Локальный progress/settings не покидают устройство; Android backup/restore для приложения отключён. Manifest не содержит `INTERNET`, поэтому сетевой передачи пользовательских данных в приложении нет.

## Privacy Policy Notes

Готовый текст policy создан: `play_store/privacy_policy_ru.md`; HTML-версия лежит в `play_store/privacy_policy_ru.html`, hosted URL уже recorded as `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`, and the policy uses the Google Play listing support contact as the privacy inquiry mechanism. Перед публикацией владелец должен ввести verified hosted URL в Play Console and заполнить рабочий support contact в Play Console.

In-app About/privacy copy also states the local privacy posture in short scannable points: no personal data collection, local-only progress/settings, no ads/analytics/accounts/payments/internet permissions, Android backup disabled and deletion through Android app data clearing or uninstall. `tools/verify_release.py` gates these key Android string markers.

## Secret Hygiene

`tools/verify_release.py` scans release-facing text files for common API key/token prefixes, private-key blocks, hardcoded bearer tokens, suspicious secret assignments and local/private dev URLs. Signing passwords and the upload keystore remain only in ignored local files or owner-controlled environment variables.

The verifier also gates dependency surface in `app/build.gradle.kts`: ads, analytics, crash SDKs, billing, auth/location Play Services, backend/network clients and image-loading SDKs are blocked so the no-data/no-network posture cannot quietly regress through dependencies.
