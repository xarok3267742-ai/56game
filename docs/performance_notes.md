# Performance Notes

## Product Posture

«Линия 56» is intentionally lightweight: no backend, network requests, image loading in-app, audio, video, 3D, heavy lists, ads, analytics or account flows. The runtime work is a small Compose UI, deterministic board generation and DataStore reads/writes for local progress/settings.

## Current Artifact Sizes

Measured and re-verified on 6 June 2026:

- Signed release AAB: `2,931,129` bytes, about 2.8 MB.
- Debug APK: `20,050,164` bytes, about 19.1 MB.
- Google Play feature graphic: `410,321` bytes.
- Google Play store icon: `274,405` bytes.
- Largest phone screenshot: `133,859` bytes.
- Largest large/tablet screenshot: `98,888` bytes.
- ImageGen source background: `1,577,241` bytes, source-only and not a Play upload asset.
- ImageGen source icon: `1,474,693` bytes, source-only and not a Play upload asset.
- `play_store` directory total: `6,111` KiB by file bytes, about 6.0 MB.

## Size Budgets

`tools/verify_release.py` enforces conservative local budgets:

- Release AAB <= 6 MB.
- Debug APK <= 30 MB.
- Feature graphic <= 1 MB.
- Each phone or large/tablet screenshot <= 1 MB.
- Source background <= 3 MB.
- Full `play_store` directory <= 7 MB.

These budgets are intentionally above current size so normal code changes do not fail the gate, but accidental large assets or heavy dependencies are caught before handoff.

## Build Artifact Freshness

`tools/verify_release.py` checks Debug APK and release AAB freshness. `app-debug.apk` must be newer than app source, Gradle build inputs and the local SDK input (`local.properties` when present); `app-release.aab` must additionally be newer than ProGuard and local signing inputs (`keystore.properties` and `private/signing/qgrid-upload.p12`). This prevents a valid checksum from masking a stale build artifact after source, build, SDK path or signing changes.

## Runtime Expectations

- Cold start should be dominated by Compose startup and one DataStore read.
- Level generation creates 36 small boards in memory.
- `LevelSolver` is used for unit reachability checks and on explicit hint requests. Boards are small, hints are user-triggered, and the search is bounded by the 4x4-6x6 released level sizes.
- The game board renders with Compose tiles and a lightweight Canvas line overlay.
- No images, audio or network resources are loaded during gameplay.
- Settings writes are small DataStore updates and should not affect frame pacing.
- Cell state transitions are limited to short color/elevation animations; reduced motion changes them to zero-duration updates.
- Current-line hint search is not run during every tap or frame; it runs only when the player taps `Подсказка`.

## Optimizations Already In Place

- Release build uses R8 minify and resource shrink.
- In-app assets are vector/color resources.
- Store screenshots and feature graphic are compressed PNGs.
- Android backup is disabled, avoiding unnecessary progress/settings cloud transfer.
- No crash/analytics/ad SDKs are included.
- `tools/verify_release.py` now blocks ads, analytics, billing, backend/network clients and image-loading SDK markers in `app/build.gradle.kts`, keeping the dependency surface lightweight.
- `tools/verify_release.py` gates the cell animation/reduced-motion source markers so motion polish cannot regress into an inert setting.

## Remaining Performance Checks

- Review generated APK download size in Play Console after upload.
- If future art/audio assets are added, re-check file sizes and update budgets intentionally.
- If future gameplay animation becomes more complex, run emulator FPS/performance profiling before production rollout.
