# Tech Stack Decision

## Выбранный стек

Kotlin + Jetpack Compose + Material 3 в нативном Android project.

## Зафиксированные версии

- Android Gradle Plugin: 8.11.1.
- Gradle wrapper: 8.14.5, with `validateDistributionUrl=true`.
- Kotlin Gradle plugin: 2.2.20.
- Compose BOM: 2026.05.01.
- `compileSdk = 36`, `targetSdk = 36`, `minSdk = 24`.
- `versionCode = 1`, `versionName = 1.0.0`.
- JVM target/source compatibility: 17.

## Package And Build Identity

- Production namespace and `applicationId`: `com.qgrid.mobile`.
- Debug package suffix: `.debug`, so debug installs as `com.qgrid.mobile.debug`.
- App label remains `Линия 56`; the package id stays neutral and does not include personal or obvious app-name identifiers.
- Release build uses R8 minification and resource shrinking.

## Почему

- Пустой workspace и локально доступный Android SDK.
- Compose позволяет быстро сделать polish UI без XML-layout boilerplate.
- Чистая Kotlin-логика легко тестируется unit-тестами.
- DataStore подходит для локального progress/settings без Room.
- Нативный Android проще подготовить к Google Play, чем web-wrapper.

## Architecture Boundary

- `app/src/main/java/com/qgrid/mobile/game`: deterministic pure Kotlin game logic, level generation, solver and reducer; no Android dependency.
- `app/src/main/java/com/qgrid/mobile/data`: DataStore Preferences persistence for onboarding/progress/settings.
- `app/src/main/java/com/qgrid/mobile/ui`: Compose screens, app state and ViewModel.
- UI strings are Android resources, not user-visible Russian literals in Kotlin.
- The dependency surface is intentionally small: Activity Compose, Compose Foundation/UI/Material 3, Core, SplashScreen, DataStore, Lifecycle, JUnit and AndroidX/Compose test libraries.

## Privacy And Dependency Constraints

- No backend, accounts, ads, analytics, crash SDK, payments, billing, UGC, location/auth Play Services, image loading SDK or network client dependency.
- No `INTERNET` or `ACCESS_NETWORK_STATE` permission.
- Android backup is disabled in the manifest through `android:allowBackup="false"`.
- Local progress/settings only: onboarding flag, completed levels, last level and haptics/high-contrast/reduce-motion settings.

## Альтернативы

- Flutter: подходит, но в репозитории нет Flutter-проекта, а нативный Android tooling уже доступен.
- React Native/Expo: лишняя runtime/dependency сложность для простой offline puzzle.
- Godot: уместен для более игровых сцен, но здесь Compose достаточно.

## Команды

```bash
./gradlew test
./gradlew assembleDebug
./gradlew lint
./gradlew assembleRelease
./gradlew connectedDebugAndroidTest
./gradlew bundleRelease
./tools/verify_release.py
```

## Ограничения окружения

- `local.properties` нужен для `sdk.dir`; он локальный, игнорируется git and must stay owner-only readable when present.
- Локальный upload keystore создан в ignored `private/signing/qgrid-upload.p12`, credentials в ignored `keystore.properties`.
- Release signing can also use `QGRID_STORE_FILE`, `QGRID_STORE_PASSWORD`, `QGRID_KEY_ALIAS` and `QGRID_KEY_PASSWORD`.
- Signing files, passwords, private keys, `local.properties`, APKs, AABs and generated build outputs must not be committed.
- Lint после обновления Gradle/dependencies: `No issues found`.

## Release Gate

`tools/verify_release.py` checks this stack decision against the current build files, dependency surface, manifest privacy state, signing-file hygiene and release artifacts. If the stack changes, update this document and the verifier together.
