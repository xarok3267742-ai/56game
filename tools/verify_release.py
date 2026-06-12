#!/usr/bin/env python3
"""Project-local release candidate verifier for Line 56.

The script intentionally checks facts that are easy to regress:
- neutral package/build config;
- Android backup disabled;
- no platform/runtime permissions or internet dependency;
- no ads/analytics/payments/backend/network dependency surface;
- upload artifact/signature presence;
- native library 16 KB page-size alignment;
- release signing certificate/report consistency;
- no debug/test package leakage in production AAB;
- mandatory fresh debug APK and release AAB build artifacts;
- lightweight artifact and asset size budgets;
- Play store asset dimensions/alpha;
- upload manifest paths;
- upload-packet helper consistency;
- store asset review sheet helper consistency;
- Play upload archive helper consistency;
- Play Console packet helper consistency;
- signing-backup input helper consistency;
- upload artifact checksums and byte sizes, including phone/tablet screenshots;
- store metadata lengths and Play Console handoff consistency;
- privacy, data-safety and content-rating handoff consistency;
- Russian Android string resources without placeholders;
- no committed API keys, tokens, private keys or local/dev URLs in release-facing files;
- required project and Play handoff docs;
- current Google Play source-audit markers;
- mandatory fresh generated connected-test report consistency;
- no old personal/package identifiers in release-facing files.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import zlib
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_NATIVE_LOAD_ALIGNMENT = 16 * 1024


class CheckFailure(Exception):
    pass


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def require_file(path: str) -> Path:
    file_path = ROOT / path
    require(file_path.is_file(), f"missing file: {path}")
    return file_path


def elf_load_alignments(entry_name: str, data: bytes) -> list[int]:
    require(data[:4] == b"\x7fELF", f"native library is not an ELF file: {entry_name}")
    require(len(data) >= 64, f"native library ELF header is truncated: {entry_name}")

    elf_class = data[4]
    endian = data[5]
    require(endian in {1, 2}, f"native library has unsupported ELF endianness: {entry_name}")
    prefix = "<" if endian == 1 else ">"

    if elf_class == 2:
        e_phoff = struct.unpack_from(prefix + "Q", data, 32)[0]
        e_phentsize = struct.unpack_from(prefix + "H", data, 54)[0]
        e_phnum = struct.unpack_from(prefix + "H", data, 56)[0]
        align_offset = 48
        align_format = prefix + "Q"
    elif elf_class == 1:
        e_phoff = struct.unpack_from(prefix + "I", data, 28)[0]
        e_phentsize = struct.unpack_from(prefix + "H", data, 42)[0]
        e_phnum = struct.unpack_from(prefix + "H", data, 44)[0]
        align_offset = 28
        align_format = prefix + "I"
    else:
        raise CheckFailure(f"native library has unsupported ELF class: {entry_name}")

    require(e_phnum > 0, f"native library has no ELF program headers: {entry_name}")
    require(e_phentsize >= align_offset + struct.calcsize(align_format), f"native library program header is too small: {entry_name}")
    table_end = e_phoff + e_phentsize * e_phnum
    require(table_end <= len(data), f"native library program header table is truncated: {entry_name}")

    alignments: list[int] = []
    for index in range(e_phnum):
        offset = e_phoff + index * e_phentsize
        p_type = struct.unpack_from(prefix + "I", data, offset)[0]
        if p_type == 1:  # PT_LOAD
            alignments.append(struct.unpack_from(align_format, data, offset + align_offset)[0])
    require(alignments, f"native library has no PT_LOAD program headers: {entry_name}")
    return alignments


def native_library_alignment_summary(archive_path: Path) -> tuple[list[str], int | None]:
    native_library_names: list[str] = []
    minimum_alignment: int | None = None
    with zipfile.ZipFile(archive_path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".so"):
                continue
            native_library_names.append(name)
            alignments = elf_load_alignments(name, archive.read(name))
            for alignment in alignments:
                if minimum_alignment is None or alignment < minimum_alignment:
                    minimum_alignment = alignment
    return native_library_names, minimum_alignment


def unique_existing_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        normalized = path.expanduser()
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized.exists():
            result.append(normalized)
    return result


def local_properties_value(key: str) -> str | None:
    path = ROOT / "local.properties"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        item_key, item_value = stripped.split("=", 1)
        if item_key.strip() == key:
            return item_value.strip().replace("\\:", ":")
    return None


def resolve_jarsigner() -> Path:
    candidates: list[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin" / "jarsigner")
    candidates.append(Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/jarsigner"))
    path_jarsigner = shutil.which("jarsigner")
    if path_jarsigner:
        candidates.append(Path(path_jarsigner))

    existing = unique_existing_paths(candidates)
    if existing:
        return existing[0]
    raise CheckFailure("missing jarsigner; set JAVA_HOME or install Android Studio/JDK")


def resolve_keytool() -> Path:
    candidates: list[Path] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(Path(java_home) / "bin" / "keytool")
    candidates.append(Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/keytool"))
    path_keytool = shutil.which("keytool")
    if path_keytool:
        candidates.append(Path(path_keytool))

    existing = unique_existing_paths(candidates)
    if existing:
        return existing[0]
    raise CheckFailure("missing keytool; set JAVA_HOME or install Android Studio/JDK")


def sdk_roots() -> list[Path]:
    candidates: list[Path] = []
    for env_name in ["ANDROID_HOME", "ANDROID_SDK_ROOT"]:
        env_value = os.environ.get(env_name)
        if env_value:
            candidates.append(Path(env_value))
    sdk_dir = local_properties_value("sdk.dir")
    if sdk_dir:
        candidates.append(Path(sdk_dir))
    candidates.append(Path.home() / "Library" / "Android" / "sdk")
    return unique_existing_paths(candidates)


def build_tools_sort_key(path: Path) -> tuple[int, ...]:
    numbers = [int(part) for part in re.findall(r"\d+", path.name)]
    return tuple(numbers)


def resolve_aapt() -> Path:
    candidates: list[Path] = []
    for sdk_root in sdk_roots():
        build_tools = sdk_root / "build-tools"
        if not build_tools.exists():
            continue
        versions = sorted(
            [path for path in build_tools.iterdir() if path.is_dir() and (path / "aapt").exists()],
            key=build_tools_sort_key,
            reverse=True,
        )
        candidates.extend(path / "aapt" for path in versions)

    path_aapt = shutil.which("aapt")
    if path_aapt:
        candidates.append(Path(path_aapt))

    existing = unique_existing_paths(candidates)
    if existing:
        return existing[0]
    raise CheckFailure("missing Android build-tools aapt; set sdk.dir, ANDROID_HOME or ANDROID_SDK_ROOT")


def png_info(path: str) -> tuple[int, int, int, int]:
    file_path = require_file(path)
    data = file_path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"not a PNG: {path}")
    require(data[12:16] == b"IHDR", f"missing IHDR: {path}")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, bit_depth, color_type


def png_non_opaque_alpha_pixels(path: str) -> int:
    file_path = require_file(path)
    data = file_path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"not a PNG: {path}")

    offset = 8
    width = height = bit_depth = color_type = interlace = None
    idat_parts: list[bytes] = []
    while offset < len(data):
        require(offset + 8 <= len(data), f"truncated PNG chunk header: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data_start = offset + 8
        chunk_data_end = chunk_data_start + length
        require(chunk_data_end + 4 <= len(data), f"truncated PNG chunk data: {path}")
        chunk_data = data[chunk_data_start:chunk_data_end]
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break
        offset = chunk_data_end + 4

    require(width is not None and height is not None and bit_depth is not None and color_type is not None, f"missing IHDR: {path}")
    require(bit_depth == 8, f"{path}: alpha scan expects 8-bit PNG")
    require(color_type in {4, 6}, f"{path}: alpha scan expects PNG color type 4 or 6, got {color_type}")
    require(interlace == 0, f"{path}: alpha scan expects non-interlaced PNG")
    bytes_per_pixel = 2 if color_type == 4 else 4
    row_length = width * bytes_per_pixel
    raw = zlib.decompress(b"".join(idat_parts))
    require(len(raw) == height * (row_length + 1), f"{path}: unexpected decompressed PNG length")

    def paeth(a: int, b: int, c: int) -> int:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    previous = bytearray(row_length)
    non_opaque = 0
    index = 0
    for _row in range(height):
        filter_type = raw[index]
        index += 1
        filtered = raw[index : index + row_length]
        index += row_length
        current = bytearray(row_length)
        for i, value in enumerate(filtered):
            left = current[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            up = previous[i]
            up_left = previous[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            if filter_type == 0:
                recon = value
            elif filter_type == 1:
                recon = value + left
            elif filter_type == 2:
                recon = value + up
            elif filter_type == 3:
                recon = value + ((left + up) // 2)
            elif filter_type == 4:
                recon = value + paeth(left, up, up_left)
            else:
                raise CheckFailure(f"{path}: unsupported PNG filter type {filter_type}")
            current[i] = recon & 0xFF
        alpha_offset = 1 if color_type == 4 else 3
        non_opaque += sum(1 for i in range(alpha_offset, row_length, bytes_per_pixel) if current[i] != 255)
        previous = current
    return non_opaque


def latest_file_mtime(paths: list[str]) -> float:
    file_paths: list[Path] = []
    for path_text in paths:
        path = ROOT / path_text
        require(path.exists(), f"freshness path does not exist: {path_text}")
        if path.is_file():
            file_paths.append(path)
        else:
            file_paths.extend(file_path for file_path in path.rglob("*") if file_path.is_file())
    require(bool(file_paths), f"freshness paths contain no files: {paths}")
    return max(file_path.stat().st_mtime for file_path in file_paths)


def existing_local_inputs(paths: list[str]) -> list[str]:
    return [path for path in paths if (ROOT / path).exists()]


def check_png(path: str, width: int, height: int, alpha: bool, max_bytes: int | None = None) -> None:
    actual_width, actual_height, bit_depth, color_type = png_info(path)
    require((actual_width, actual_height) == (width, height), f"{path}: expected {width}x{height}, got {actual_width}x{actual_height}")
    require(bit_depth == 8, f"{path}: expected 8-bit PNG, got bit depth {bit_depth}")
    has_alpha = color_type in {4, 6}
    require(has_alpha == alpha, f"{path}: expected alpha={alpha}, got alpha={has_alpha}")
    if max_bytes is not None:
        size = (ROOT / path).stat().st_size
        require(size <= max_bytes, f"{path}: expected <= {max_bytes} bytes, got {size}")


def check_play_screenshot_png(path: str, width: int, height: int) -> None:
    check_png(path, width, height, alpha=False)
    min_side = min(width, height)
    max_side = max(width, height)
    require(320 <= min_side <= 3840, f"{path}: shortest side must be within Google Play's 320-3840 px screenshot range")
    require(320 <= max_side <= 3840, f"{path}: longest side must be within Google Play's 320-3840 px screenshot range")
    require(max_side <= min_side * 2, f"{path}: Google Play screenshot longest side must be no more than 2x shortest side")


def check_build_config() -> None:
    text = read("app/build.gradle.kts")
    expected = {
        'namespace = "com.qgrid.mobile"',
        'applicationId = "com.qgrid.mobile"',
        "compileSdk = 36",
        "minSdk = 24",
        "targetSdk = 36",
        "versionCode = 1",
        'versionName = "1.0.0"',
        'applicationIdSuffix = ".debug"',
        'versionNameSuffix = "-debug"',
        "isMinifyEnabled = true",
        "isShrinkResources = true",
        'getDefaultProguardFile("proguard-android-optimize.txt")',
        '"proguard-rules.pro"',
        'tasks.matching { it.name == "extractReleaseVersionControlInfo" }.configureEach',
        "enabled = false",
    }
    for needle in expected:
        require(needle in text, f"missing build config: {needle}")

    root_build = read("build.gradle.kts")
    for needle in [
        'id("com.android.application") version "8.11.1" apply false',
        'id("org.jetbrains.kotlin.android") version "2.2.20" apply false',
        'id("org.jetbrains.kotlin.plugin.compose") version "2.2.20" apply false',
    ]:
        require(needle in root_build, f"missing root build plugin config: {needle}")

    wrapper = read("gradle/wrapper/gradle-wrapper.properties")
    require(
        "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.14.5-bin.zip" in wrapper,
        "Gradle wrapper must use 8.14.5",
    )
    require("validateDistributionUrl=true" in wrapper, "Gradle wrapper must validate distribution URL")

    settings = read("settings.gradle.kts")
    require('rootProject.name = "Line56"' in settings, "settings.gradle.kts must keep project name Line56")
    require('include(":app")' in settings, "settings.gradle.kts must include :app")


def check_tech_stack_handoff() -> None:
    require_text_markers(
        "docs/tech_stack_decision.md",
        [
            "Kotlin + Jetpack Compose + Material 3 в нативном Android project.",
            "Android Gradle Plugin: 8.11.1.",
            "Gradle wrapper: 8.14.5, with `validateDistributionUrl=true`.",
            "Kotlin Gradle plugin: 2.2.20.",
            "Compose BOM: 2026.05.01.",
            "`compileSdk = 36`, `targetSdk = 36`, `minSdk = 24`.",
            "`versionCode = 1`, `versionName = 1.0.0`.",
            "JVM target/source compatibility: 17.",
            "Production namespace and `applicationId`: `com.qgrid.mobile`.",
            "Debug package suffix: `.debug`, so debug installs as `com.qgrid.mobile.debug`.",
            "the package id stays neutral and does not include personal or obvious app-name identifiers.",
            "Release build uses R8 minification and resource shrinking.",
            "`app/src/main/java/com/qgrid/mobile/game`: deterministic pure Kotlin game logic",
            "`app/src/main/java/com/qgrid/mobile/data`: DataStore Preferences persistence",
            "`app/src/main/java/com/qgrid/mobile/ui`: Compose screens, app state and ViewModel.",
            "UI strings are Android resources, not user-visible Russian literals in Kotlin.",
            "Activity Compose, Compose Foundation/UI/Material 3, Core, SplashScreen, DataStore, Lifecycle, JUnit and AndroidX/Compose test libraries.",
            "No backend, accounts, ads, analytics, crash SDK, payments, billing, UGC, location/auth Play Services, image loading SDK or network client dependency.",
            "No `INTERNET` or `ACCESS_NETWORK_STATE` permission.",
            "Android backup is disabled in the manifest through `android:allowBackup=\"false\"`.",
            "Local progress/settings only: onboarding flag, completed levels, last level and haptics/high-contrast/reduce-motion settings.",
            "./gradlew test",
            "./gradlew assembleDebug",
            "./gradlew assembleRelease",
            "./gradlew lint",
            "./gradlew connectedDebugAndroidTest",
            "./gradlew bundleRelease",
            "./tools/verify_release.py",
            "`local.properties` нужен для `sdk.dir`; он локальный, игнорируется git and must stay owner-only readable when present.",
            "ignored `private/signing/qgrid-upload.p12`",
            "ignored `keystore.properties`",
            "QGRID_STORE_FILE",
            "QGRID_STORE_PASSWORD",
            "QGRID_KEY_ALIAS",
            "QGRID_KEY_PASSWORD",
            "Signing files, passwords, private keys, `local.properties`, APKs, AABs and generated build outputs must not be committed.",
            "`tools/verify_release.py` checks this stack decision against the current build files",
        ],
    )


def check_discreet_package_identity() -> None:
    build = read("app/build.gradle.kts")
    identity_lines = [
        line.strip()
        for line in build.splitlines()
        if line.strip().startswith(("namespace =", "applicationId ="))
    ]
    require('namespace = "com.qgrid.mobile"' in identity_lines, "namespace must stay neutral: com.qgrid.mobile")
    require('applicationId = "com.qgrid.mobile"' in identity_lines, "applicationId must stay neutral: com.qgrid.mobile")

    forbidden_identity_markers = [
        "com.ivliev",
        "ivliev",
        "andrej",
        "line56",
        "line_56",
        "line-56",
        "56game",
        "numberpath",
        "quietgrid",
    ]
    for line in identity_lines:
        lowered = line.lower()
        for marker in forbidden_identity_markers:
            require(marker not in lowered, f"package identity line contains obvious/old marker {marker!r}: {line}")

    expected_dirs = [
        "app/src/main/java/com/qgrid/mobile",
        "app/src/test/java/com/qgrid/mobile",
        "app/src/androidTest/java/com/qgrid/mobile",
    ]
    for path in expected_dirs:
        require((ROOT / path).is_dir(), f"missing neutral package source path: {path}")

    kotlin_roots = ["app/src/main/java", "app/src/test/java", "app/src/androidTest/java"]
    for root in kotlin_roots:
        for file_path in (ROOT / root).rglob("*.kt"):
            text = file_path.read_text(encoding="utf-8")
            match = re.search(r"^\s*package\s+([A-Za-z0-9_.]+)\s*$", text, re.MULTILINE)
            require(match is not None, f"missing Kotlin package declaration: {file_path.relative_to(ROOT)}")
            package_name = match.group(1)
            require(
                package_name == "com.qgrid.mobile" or package_name.startswith("com.qgrid.mobile."),
                f"Kotlin package must stay under com.qgrid.mobile: {file_path.relative_to(ROOT)}",
            )
            lowered = package_name.lower()
            for marker in forbidden_identity_markers:
                require(marker not in lowered, f"Kotlin package contains obvious/old marker {marker!r}: {file_path.relative_to(ROOT)}")

    generated_manifests = {
        "app/build/intermediates/merged_manifest/release/processReleaseMainManifest/AndroidManifest.xml": 'package="com.qgrid.mobile"',
        "app/build/intermediates/merged_manifest/debug/processDebugMainManifest/AndroidManifest.xml": 'package="com.qgrid.mobile.debug"',
    }
    forbidden_manifest_markers = ["com.ivliev", "ivliev", "andrej", "com.quietgrid", "numberpath"]
    for path, expected_package in generated_manifests.items():
        manifest_path = ROOT / path
        require(manifest_path.is_file(), f"missing generated manifest for package identity check: {path}")
        manifest_text = manifest_path.read_text(encoding="utf-8", errors="ignore")
        require(expected_package in manifest_text, f"generated manifest must contain {expected_package}: {path}")
        for marker in forbidden_manifest_markers:
            require(marker not in manifest_text.lower(), f"generated manifest contains obvious/old marker {marker!r}: {path}")


def check_required_documents() -> None:
    required_files = [
        "README.md",
        "AGENTS.md",
        "docs/product_decision.md",
        "docs/product_spec.md",
        "docs/tech_stack_decision.md",
        "docs/requirements_traceability.md",
        "docs/release_plan.md",
        "docs/release_report.md",
        "docs/google_play_sources.md",
        "docs/google_play_checklist.md",
        "docs/ui_audit.md",
        "docs/qa_test_plan.md",
        "docs/performance_notes.md",
        "docs/privacy_and_permissions.md",
        "docs/art_direction.md",
        "docs/asset_manifest.md",
        "docs/asset_prompts.md",
        "docs/content_audit.md",
        "docs/accessibility_notes.md",
        "docs/completion_audit.md",
        "docs/rejected_assets.md",
        "play_store/listing_ru.md",
        "play_store/data_safety_ru.md",
        "play_store/content_rating_notes.md",
        "play_store/app_content_answers_ru.md",
        "play_store/owner_release_inputs.md",
        "play_store/privacy_policy_ru.md",
        "play_store/privacy_policy_ru.html",
        "play_store/privacy_policy_hosting_checklist.md",
        "play_store/upload_manifest.md",
        "play_store/upload_runbook_ru.md",
        "play_store/publication_readiness_owner_actions_ru.md",
        "play_store/play_console_post_upload_evidence_ru.md",
        "play_store/signing_backup_evidence_ru.md",
        "play_store/upload_checksums.md",
        "play_store/play_console_submission_ru.md",
        "play_store/signing_certificate_report.md",
        "play_store/asset_alt_text_ru.md",
        "play_store/screenshots/manifest.md",
    ]
    for path in required_files:
        file_path = require_file(path)
        require(file_path.stat().st_size > 0, f"required document is empty: {path}")

    product_spec = read("docs/product_spec.md")
    require("Story campaign" in product_spec, "product_spec must document story mode as a non-goal")
    agents = read("AGENTS.md")
    require("Done Criteria" in agents, "AGENTS.md must include Done Criteria")
    require("Release Verifier" in agents, "AGENTS.md must describe the release verifier")


def check_agents_handoff() -> None:
    require_text_markers(
        "AGENTS.md",
        [
            "«Линия 56» is an offline-first Android numeric puzzle.",
            "Kotlin + Jetpack Compose + Material 3.",
            "Android Gradle Plugin 8.11.1.",
            "Gradle wrapper 8.14.5.",
            "`compileSdk = 36`, `targetSdk = 36`, `minSdk = 24`.",
            "Production `applicationId = com.qgrid.mobile`.",
            "Debug package suffix: `.debug`.",
            "DataStore Preferences for local onboarding/progress/settings.",
            "No backend, no accounts, no ads, no analytics, no IAP, no `INTERNET` permission.",
            "QGRID_STORE_FILE=/absolute/path/upload-keystore.p12",
            "Never commit signing files, passwords, private keys, `local.properties`, APKs, AABs or generated build outputs.",
            "./gradlew test",
            "./gradlew assembleDebug",
            "./gradlew assembleRelease",
            "./gradlew lint",
            "./gradlew connectedDebugAndroidTest",
            "./gradlew bundleRelease",
            "./tools/run_final_local_gate.py",
            "./tools/run_final_local_gate.py --include-hosted-privacy",
            "./tools/run_final_local_gate.py --include-connected --connected-serial <serial>",
            "./tools/run_final_local_gate.py --include-connected --connected-serial <serial> --include-hosted-privacy",
            "./tools/run_api36_connected_gate.py",
            "./tools/run_api36_connected_gate.py --include-hosted-privacy",
            "./tools/verify_release.py",
            "./tools/print_upload_packet.py",
            "./tools/create_store_asset_review_sheet.py --dry-run",
            "./tools/create_store_asset_review_sheet.py --write",
            "./tools/prepare_play_upload_archive.py --dry-run",
            "./tools/prepare_play_upload_archive.py --verify-existing",
            "./tools/print_play_console_packet.py",
            "./tools/print_publication_readiness.py",
            "./tools/verify_play_generated_apk.py --dry-run",
            "./tools/check_privacy_policy_url.py --local",
            "./tools/check_signing_backup_inputs.py",
            "./tools/verify_remote_release.py",
            "Run `connectedDebugAndroidTest` when an emulator/device is available.",
            "`app/src/main/java/com/qgrid/mobile/game`: pure Kotlin models, level generation, solver and reducer. No Android dependencies here.",
            "`app/src/main/java/com/qgrid/mobile/data`: DataStore progress/settings persistence.",
            "`app/src/main/java/com/qgrid/mobile/ui`: Compose screens, app state and ViewModel.",
            "Keep game logic deterministic and testable in pure Kotlin.",
            "runtime hints must be current-selection aware through `LevelSolver`.",
            "Do not add backend, network calls, accounts, ads, analytics, crash SDKs, IAP, UGC or dangerous permissions without a new documented product decision.",
            "Do not introduce `INTERNET` or `ACCESS_NETWORK_STATE`; offline-first is a release invariant.",
            "Do not put user-visible Russian text in Kotlin code; use `app/src/main/res/values/strings.xml`.",
            "Release AAB must not contain project `.debug`, androidTest, JUnit, Espresso or Compose UI-test leakage.",
            "Preserve neutral identifiers: no personal names in `applicationId`, namespace, signing aliases or store-facing docs.",
            "tap targets at least 48dp.",
            "Support small, tall and landscape layouts without clipped controls.",
            "Keep high contrast and reduced motion settings functional.",
            "Do not upload rejected/source assets to Play Console.",
            "Verify Play asset dimensions/alpha through `tools/verify_release.py`.",
            "`docs/google_play_sources.md`",
            "`docs/completion_audit.md`",
            "`docs/rejected_assets.md`",
            "`play_store/app_content_answers_ru.md`",
            "`play_store/upload_runbook_ru.md`",
            "`play_store/publication_readiness_owner_actions_ru.md`",
            "`play_store/play_console_post_upload_evidence_ru.md`",
            "`play_store/signing_backup_evidence_ru.md`",
            "`play_store/screenshots/manifest.md`",
            "`./tools/verify_release.py` is the project-local release gate.",
            "AAB native `.so` 16 KB page-size alignment",
            "`./tools/run_final_local_gate.py` is the owner-facing final local gate runner.",
            "supports optional `--include-hosted-privacy` recorded hosted privacy URL validation",
            "supports optional `--include-connected --connected-serial <serial>` connected evidence refresh",
            "force-stops/kills the current production package `com.qgrid.mobile` plus known stale local package processes",
            "uninstalls known stale local debug/test packages on the selected serial, including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`, before that optional connected run",
            "prints `final_local_gate_ok` only after every command succeeds.",
            "`./tools/run_api36_connected_gate.py` is the managed API 36 connected gate helper.",
            "can pass through `--include-hosted-privacy` for the networked upload-day preflight",
            "wipes that project-owned AVD data on managed start to avoid stale debug/test APK interference",
            "refuses to touch a different AVD on that serial.",
            "`./tools/print_upload_packet.py` is the read-only owner helper for upload day.",
            "requires the exact ordered upload path set and prints the Google Play upload packet plus the Do Not Upload list.",
            "`./tools/create_store_asset_review_sheet.py` is the local visual asset review helper.",
            "The sheet is internal evidence only and must not be uploaded to Play Console.",
            "`./tools/prepare_play_upload_archive.py` is the generated owner handoff archive helper.",
            "In `--verify-existing` mode it verifies the generated ZIP exactly matches current upload assets and handoff notes.",
            "The ZIP is not a Play Console upload artifact; unpack it and upload the individual files.",
            "`./tools/print_play_console_packet.py` is the read-only owner helper for Play Console forms.",
            "prints the copy-ready store listing, policy posture and manual owner gates.",
            "`./tools/print_publication_readiness.py` is the read-only owner helper for publication status.",
            "can validate the recorded hosted privacy policy URL with `--check-recorded-privacy-url`",
            "groups unresolved owner actions by evidence file and required command",
            "publication_readiness_local_ready_external_pending",
            "`./tools/verify_play_generated_apk.py` is the owner helper for Play-generated APK review after upload.",
            "with `--apk <path>` it verifies the APK package, version, label, SDK levels, APK signature, signer certificate SHA-256, no Android Debug certificate, no forbidden permissions, `allowBackup=false`, no debuggable release manifest, `extractNativeLibs=false`, native `.so` `PT_LOAD` alignment, uncompressed 16 KB ZIP-aligned native libraries, no debug/test leakage, a 512x512 icon candidate whose pixels match `play_store/icon/play_icon_512.png`, an application icon reference linked to that matching PNG and a round icon reference linked to that same PNG.",
            "`./tools/check_privacy_policy_url.py --local` validates the local ready-to-host privacy HTML.",
            "`./tools/check_privacy_policy_url.py --url <https-url>` before entering the URL in Play Console.",
            "`./tools/check_signing_backup_inputs.py` validates the ignored local signing inputs before backup without printing password values.",
            "Use `play_store/signing_backup_evidence_ru.md` to record only safe owner-side backup evidence.",
            "`./tools/verify_remote_release.py` is the networked post-push GitHub release helper.",
            "requires the remote release branch to match local `HEAD`",
            "can verify an explicit `--tag <release-tag>` is an annotated tag and peels to local `HEAD`",
            "verifies every remote upload asset bytes/SHA-256 from `play_store/upload_checksums.md`",
            "rejects any extra remote `.aab` files outside `app/build/outputs/bundle/release/app-release.aab`",
            "scans remote trees case-insensitively for signing/install artifacts including `.p12`, `.jks`, `.keystore`, `.pem`, `.pk8`, `.key`, APK/APKS/IDSIG and private directories",
            "When changing release-facing behavior, update the verifier if the new invariant can be checked locally.",
            "Core loop works and all 36 levels are independently solver-verified.",
            "UI looks like a finished mobile product, not a prototype.",
            "No placeholder user-facing content remains.",
            "Store assets are present and verifier-approved.",
            "`./tools/run_final_local_gate.py` passes and prints `final_local_gate_ok`",
            "this covers `./gradlew test`, `./gradlew lint`, `./gradlew assembleDebug`, `./gradlew assembleRelease`, `./gradlew bundleRelease`, `./tools/verify_release.py`, `./tools/print_upload_packet.py`, `./tools/create_store_asset_review_sheet.py --dry-run`, `./tools/prepare_play_upload_archive.py --dry-run`, `./tools/prepare_play_upload_archive.py --verify-existing`, `./tools/print_play_console_packet.py`, `./tools/print_publication_readiness.py`, `./tools/verify_play_generated_apk.py --dry-run`, `./tools/check_privacy_policy_url.py --local` and `./tools/check_signing_backup_inputs.py`.",
            "preferably through `./tools/run_api36_connected_gate.py` or `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` on an API 36 device",
            "Google Play checklist, release report and upload handoff are current.",
            "The full publication goal is not complete until manual external gates are done",
            "entering the verified hosted privacy-policy URL in Play Console, populated Play Console support/contact fields for privacy inquiries, secure keystore backup, Play Console forms and required testing tracks.",
        ],
    )
    agents = read("AGENTS.md")
    require("Final local gate before handoff:" in agents, "AGENTS.md missing final local gate section")
    final_gate = agents.split("Final local gate before handoff:", 1)[1].split("Run `connectedDebugAndroidTest`", 1)[0]
    require("./tools/run_final_local_gate.py" in final_gate, "AGENTS.md final local gate must use run_final_local_gate.py")
    require(
        "The runner executes `./gradlew test lint assembleDebug assembleRelease bundleRelease`, `./tools/verify_release.py`, `./tools/print_upload_packet.py`, `./tools/create_store_asset_review_sheet.py --dry-run`, `./tools/prepare_play_upload_archive.py --dry-run`, `./tools/prepare_play_upload_archive.py --verify-existing`, `./tools/print_play_console_packet.py`, `./tools/print_publication_readiness.py`, `./tools/verify_play_generated_apk.py --dry-run`, `./tools/check_privacy_policy_url.py --local` and `./tools/check_signing_backup_inputs.py` in order."
        in final_gate,
        "AGENTS.md final local gate must document the runner command expansion",
    )
    for command in [
        "./gradlew test lint assembleDebug assembleRelease bundleRelease",
        "./tools/verify_release.py",
        "./tools/print_upload_packet.py",
        "./tools/create_store_asset_review_sheet.py --dry-run",
        "./tools/prepare_play_upload_archive.py --dry-run",
        "./tools/prepare_play_upload_archive.py --verify-existing",
        "./tools/print_play_console_packet.py",
        "./tools/print_publication_readiness.py",
        "./tools/verify_play_generated_apk.py --dry-run",
        "./tools/check_privacy_policy_url.py --local",
        "./tools/check_signing_backup_inputs.py",
    ]:
        require(command in final_gate, f"AGENTS.md final local gate missing command: {command}")


def check_readme_handoff() -> None:
    require_text_markers(
        "README.md",
        [
            "Нативная Android-first числовая головоломка",
            "`applicationId`: `com.qgrid.mobile`",
            "./gradlew test",
            "./gradlew assembleDebug",
            "./gradlew assembleRelease",
            "./gradlew lint",
            "./gradlew connectedDebugAndroidTest",
            "./gradlew bundleRelease",
            "./tools/run_final_local_gate.py",
            "./tools/run_final_local_gate.py --include-hosted-privacy",
            "./tools/run_final_local_gate.py --include-connected --connected-serial <serial>",
            "./tools/run_final_local_gate.py --include-connected --connected-serial <serial> --include-hosted-privacy",
            "./tools/run_api36_connected_gate.py",
            "./tools/run_api36_connected_gate.py --include-hosted-privacy",
            "./tools/verify_release.py",
            "./tools/print_upload_packet.py",
            "./tools/create_store_asset_review_sheet.py --dry-run",
            "./tools/create_store_asset_review_sheet.py --write",
            "./tools/prepare_play_upload_archive.py --dry-run",
            "./tools/prepare_play_upload_archive.py --verify-existing",
            "./tools/prepare_play_upload_archive.py --write",
            "./tools/print_play_console_packet.py",
            "./tools/print_publication_readiness.py",
            "./tools/verify_play_generated_apk.py --dry-run",
            "./tools/check_privacy_policy_url.py --local",
            "./tools/check_signing_backup_inputs.py",
            "./tools/verify_remote_release.py",
            "Release AAB собран: `app/build/outputs/bundle/release/app-release.aab`",
            "Production package остаётся нейтральным: `com.qgrid.mobile`; debug package: `com.qgrid.mobile.debug`.",
            "Version identity for this upload candidate: `versionCode = 1`, `versionName = 1.0.0`.",
            "Текущий release AAB: `2,930,928` bytes",
            "`3affd5cc6de7735d7cb9cc4f381e114caa0b20d6bfa933621d596d24dc2e3043`",
            "For Google Play, the signed AAB is the only binary upload artifact.",
            "Generated release APK outputs under `app/build/outputs/apk/release` are install/testing artifacts only and must not be uploaded to Play.",
            "Последняя asset-правка на 6 июня 2026",
            "`app/src/main/res/drawable-nodpi/ic_launcher_imagegen.png`",
            "`play_store/icon/play_icon_preview_masked.png` is a local mask preview only",
            "upload the full-square `play_store/icon/play_icon_512.png` because Google Play applies its own mask",
            "Последняя локальная проверка на 6 июня 2026",
            "Google Play sources",
            "product decision",
            "performance notes",
            "fresh debug/release artifact evidence",
            "mandatory fresh connected XML evidence",
            "owner-controlled release inputs",
            "owner-action breakdown - в `play_store/publication_readiness_owner_actions_ru.md`",
            "upload runbook - в `play_store/upload_runbook_ru.md`",
            "post-upload evidence template - в `play_store/play_console_post_upload_evidence_ru.md`",
            "signing backup evidence and owner template - в `play_store/signing_backup_evidence_ru.md`",
            "`./tools/run_final_local_gate.py` runs the complete final local gate and prints `final_local_gate_ok` only after build/test/verifier/handoff helpers pass.",
            "Add `--include-hosted-privacy` for a networked pre-upload run that also revalidates the recorded hosted privacy policy URL.",
            "force-stops/kills the current production package `com.qgrid.mobile` plus known stale local package processes",
            "uninstalls known stale local debug/test packages on the selected serial, including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`",
            "old instrumentation packages cannot pollute verifier evidence or steal focus",
            "When an API 36 emulator/device is available, `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` refreshes `connectedDebugAndroidTest` evidence before the verifier.",
            "`./tools/run_api36_connected_gate.py` boots the project-owned `Medium_Phone_API_36` AVD on `emulator-5560` with `-wipe-data`, retries the cleaned AVD once without `-wipe-data` if the emulator exits after the wipe reset before boot, runs that connected final gate",
            "can pass through `--include-hosted-privacy` for the networked upload-day preflight",
            "and stops only the emulator it started",
            "`--preserve-avd-data` is for diagnostics only",
            "`./tools/print_upload_packet.py` prints and verifies the exact ordered upload packet",
            "`./tools/create_store_asset_review_sheet.py --write` regenerates the internal visual review sheet",
            "Store asset review sheet лежит в `play_store/store_asset_review_sheet.png` and is internal review evidence only",
            "`./tools/prepare_play_upload_archive.py --write` creates a generated owner handoff ZIP under `build/play_upload`",
            "`./tools/prepare_play_upload_archive.py --verify-existing` verifies that ZIP against current upload assets and handoff notes",
            "unpack it for upload day and do not upload the ZIP itself to Play Console",
            "`./tools/print_play_console_packet.py` prints and verifies the copy-ready Play Console listing/App content packet and manual owner gates.",
            "`./tools/print_publication_readiness.py` prints `publication_readiness_local_ready_external_pending`",
            "while external Play Console URL-entry, support contact, signing backup and testing-track evidence is unresolved",
            "groups unresolved owner actions by evidence file and required command",
            "`./tools/verify_play_generated_apk.py --dry-run` documents the Play-generated APK review posture",
            "run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` before rollout",
            "`./tools/check_signing_backup_inputs.py` verifies the active ignored signing inputs without printing password values.",
            "After pushing, `./tools/verify_remote_release.py --tag <release-tag>` verifies `origin/main`, the annotated remote release tag, every remote upload asset checksum from `play_store/upload_checksums.md`, rejects extra remote `.aab` files outside `app/build/outputs/bundle/release/app-release.aab`, checks case-insensitive remote signing/install artifact hygiene, verifies `origin/gh-pages` privacy-policy presence and validates the recorded hosted privacy URL.",
            "10/10 тестов",
            "replay результата через `Повторить`",
            "Medium_Phone_API_36(AVD) - 16",
            "Offline release smoke passed on API 35 with airplane mode enabled and Wi-Fi disabled",
            "`docs/qa_artifacts/offline_release_smoke_onboarding.png`",
            "`docs/qa_artifacts/offline_release_smoke_game.png`",
            "`currentGameNextLevelId`",
            "`gameState.level`",
            "TalkBack exploratory pass",
            "Перед публикацией",
            "ввести проверенный hosted privacy URL `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` в Play Console",
            "`./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`",
            "signing_backup_input_ok",
            "Play Console forms",
            "required testing tracks",
        ],
    )


def check_google_play_sources() -> None:
    require_text_markers(
        "docs/google_play_sources.md",
        [
            "Checked on 11 June 2026",
            "Latest source spot-check on 6 June 2026 after the ImageGen icon replacement",
            "Latest source spot-check on 11 June 2026",
            "https://support.google.com/googleplay/android-developer/answer/16926792?hl=en",
            "https://support.google.com/googleplay/android-developer/answer/11926878?hl=en",
            "https://developer.android.com/guide/practices/page-sizes",
            "https://developer.android.com/guide/app-bundle/app-bundle-format",
            "https://support.google.com/googleplay/android-developer/answer/14151465?hl=en",
            "https://developer.android.com/distribute/google-play/resources/icon-design-specifications",
            "https://support.google.com/googleplay/android-developer/answer/10787469?hl=en",
            "https://support.google.com/googleplay/android-developer/answer/9888076",
            "https://support.google.com/googleplay/android-developer/answer/10144311?hl=en",
            "`targetSdk = 36`",
            "Android 15/API 35",
            "signed `.aab`",
            "16 KB page sizes",
            "ELF `PT_LOAD` segment has alignment `0x4000`",
            "1024x500 24-bit PNG without alpha",
            "full-square with no transparent pixels",
            "Screenshot requirement is JPEG or 24-bit PNG without alpha, 320-3840 px per side, with the long side no more than 2x the short side",
            "Phone screenshots are 1080x2064",
            "Large/tablet screenshots are 1600x2336",
            "TalkBack exploratory pass",
            "public non-PDF HTTPS URL",
            "Google Play dynamically applies its own rounded mask and shadow",
            "apps that do not access personal and sensitive user data still must submit a privacy policy",
            "at least 12 opted-in testers for 14 continuous days",
            "no Contacts data access, no Location data access, no Health apps scope, no prediction market feature and no News app scope",
        ],
    )


def check_google_play_checklist_handoff() -> None:
    require_text_markers(
        "docs/google_play_checklist.md",
        [
            "App name: `Линия 56`",
            "Short description: `Соединяйте числа и соберите сумму ровно 56.`",
            "Copy-ready Play Console fields: `play_store/play_console_submission_ru.md`",
            "Field-by-field App content answers: `play_store/app_content_answers_ru.md`",
            "Owner-controlled release inputs: `play_store/owner_release_inputs.md`",
            "Publication readiness owner actions: `play_store/publication_readiness_owner_actions_ru.md`",
            "Upload runbook: `play_store/upload_runbook_ru.md`",
            "Post-upload evidence template: `play_store/play_console_post_upload_evidence_ru.md`",
            "Signing backup evidence and owner template: `play_store/signing_backup_evidence_ru.md`",
            "`applicationId`: `com.qgrid.mobile`",
            "Debug package: `com.qgrid.mobile.debug`",
            "`targetSdk`: 36",
            "Native 16 KB page-size posture: current signed AAB has 8 packaged `.so` files",
            "Official source audit: rechecked on 11 June 2026 in `docs/google_play_sources.md`",
            "Format: Android App Bundle",
            "Signed AAB path: `app/build/outputs/bundle/release/app-release.aab`",
            "Current local upload keystore: `private/signing/qgrid-upload.p12`",
            "common signing-key extensions (`*.jks`, `*.keystore`, `*.pem`, `*.pk8`, `*.key`) and Android upload/install artifact extensions (`*.apk`, `*.aab`, `*.apks`, `*.idsig`) are intentionally ignored case-insensitively",
            "`tools/verify_release.py` verifies these `.gitignore` patterns with `git check-ignore`",
            "fails if forbidden sensitive/install paths are tracked in Git",
            "Before Play upload, run `./tools/check_signing_backup_inputs.py` and require `signing_backup_input_ok`.",
            "Before Play upload, back up the keystore and credentials in secure owner-controlled storage, keep at least two owner-controlled secure copies, test recovery without exposing secrets and record only safe evidence in `play_store/signing_backup_evidence_ru.md`.",
            "./tools/run_final_local_gate.py",
            "./gradlew test",
            "./gradlew assembleDebug",
            "./gradlew lint",
            "./gradlew bundleRelease",
            "./tools/verify_release.py",
            "./tools/print_upload_packet.py",
            "./tools/create_store_asset_review_sheet.py --dry-run",
            "./tools/prepare_play_upload_archive.py --dry-run",
            "./tools/prepare_play_upload_archive.py --verify-existing",
            "./tools/print_play_console_packet.py",
            "./tools/print_publication_readiness.py",
            "./tools/verify_play_generated_apk.py --dry-run",
            "./tools/check_privacy_policy_url.py --local",
            "./tools/check_signing_backup_inputs.py",
            "./gradlew connectedDebugAndroidTest",
            "Latest local status on 6 June 2026",
            "store screenshot recapture passed after the ImageGen icon replacement",
            "10/10 tests on `Medium_Phone_API_36(AVD) - 16`",
            "replay from the result panel with `Повторить`",
            "Store icon: `play_store/icon/play_icon_512.png`",
            "full-square with no transparent pixels",
            "Feature graphic: `play_store/feature_graphic.png`",
            "Phone screenshots: `play_store/screenshots/phone`",
            "Large/tablet screenshots: `play_store/screenshots/tablet`",
            "Store asset review sheet: `play_store/store_asset_review_sheet.png`",
            "internal owner crop-review evidence only; do not upload it to Play Console.",
            "Preview asset alt text: `play_store/asset_alt_text_ru.md`",
            "Ready-to-host HTML: `play_store/privacy_policy_ru.html`",
            "Before entering the URL, run `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` and require `privacy_policy_url_ok`",
            "no credentials/query/fragments",
            "free of script/tracker/widget markers and text-identical to the current local `play_store/privacy_policy_ru.html`",
            "Manual gate: populate the Play Console support/contact fields because the policy uses the Google Play listing support contact as its privacy inquiry mechanism.",
            "Hosted public HTTPS URL: `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.",
            "Manual gate: enter the hosted URL in Play Console and keep the Play Console support/contact fields populated with a real support contact.",
            "Data collection: none.",
            "Data sharing: none.",
            "No `INTERNET` or `ACCESS_NETWORK_STATE` permission.",
            "Expected category: Games / Puzzle.",
            "Recommended non-child-directed answer is documented in `play_store/app_content_answers_ru.md`",
            "Upload the signed AAB to internal testing first.",
            "For applicable personal developer accounts, run the required closed testing track before production.",
            "Privacy policy is not publication-complete until the verified hosted URL is entered in Play Console and real Play Console support/contact fields are set.",
            "Owner release inputs are isolated in `play_store/owner_release_inputs.md`.",
            "Create app in Play Console.",
            "Confirm package name: `com.qgrid.mobile`.",
            "Confirm version code `1` and version name `1.0.0` in the uploaded artifact.",
            "Do not upload generated release APK outputs from app/build/outputs/apk/release; the Play upload artifact for this project is the signed AAB.",
            "Resolve owner inputs from `play_store/owner_release_inputs.md`.",
            "Compare AAB and asset bytes/SHA-256 against `play_store/upload_checksums.md` after the final local build.",
            "Run `./tools/run_final_local_gate.py` and require `final_local_gate_ok` before starting the Play Console upload.",
            "When network is available before upload, run `./tools/run_final_local_gate.py --include-hosted-privacy` and require `final_local_gate_ok`",
            "When an API 36 emulator/device is available, prefer `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` so connected evidence is refreshed before the verifier",
            "force-stops/kills the current production package `com.qgrid.mobile` plus known stale local package processes",
            "uninstalls known stale local debug/test packages on the selected serial, including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`, before instrumentation starts",
            "To have the project manage the API 36 emulator itself, run `./tools/run_api36_connected_gate.py` and require `api36_connected_gate_ok`",
            "add `--include-hosted-privacy` when network is available before upload",
            "Run `./tools/print_upload_packet.py` and require `upload_packet_ok` before uploading assets.",
            "Run `./tools/create_store_asset_review_sheet.py --dry-run` and review `play_store/store_asset_review_sheet.png` before upload",
            "Run `./tools/print_play_console_packet.py` and require `play_console_packet_ok` before filling Play Console listing/App content forms.",
            "Use `play_store/publication_readiness_owner_actions_ru.md` to resolve the external owner-action groups before production rollout.",
            "After Play Console creates downloadable APK artifacts from the uploaded AAB, run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` and require `play_generated_apk_verify_ok`, `signer certificate SHA-256: ...`, `store icon pixel matches: ...`, `application icon linked store icon: ...`, `round icon linked store icon: ...`, `allowBackup: false` and `debuggable: absent` or `debuggable: false`.",
            "Run `./tools/check_signing_backup_inputs.py` and require `signing_backup_input_ok` before backing up signing files and uploading the AAB.",
            "After pushing the release handoff to GitHub, run `./tools/verify_remote_release.py --tag <release-tag>` and require `remote_release_ok`",
            "annotated remote release tag",
            "rejects extra remote `.aab` files outside `app/build/outputs/bundle/release/app-release.aab`",
            "validates the recorded hosted privacy URL",
            "Record safe signing-backup evidence in `play_store/signing_backup_evidence_ru.md`.",
            "Record safe post-upload evidence in `play_store/play_console_post_upload_evidence_ru.md`.",
            "Promote to production only after manual gates are complete.",
        ],
    )


def check_product_decision() -> None:
    require_text_markers(
        "docs/product_decision.md",
        [
            "Checked on 4 June 2026",
            "Observed references, rechecked on 4 June 2026",
            "Number Match - Number Games",
            "2248",
            "Make Ten",
            "Match Ten - Number Puzzle",
            "Take Ten: Match Numbers",
            "does not copy competitor names, brands, UI, rules, art, characters or store copy",
            "Selected: «Линия 56»",
            "fixed target 56",
            "no ads, no IAP, no accounts, no UGC, no backend and no dangerous permissions",
            "MVP Scope",
            "Out Of Scope For V1",
        ],
    )


def check_product_spec_handoff() -> None:
    require_text_markers(
        "docs/product_spec.md",
        [
            "Native Android game. Casual numeric puzzle for short offline sessions.",
            "Соединяйте соседние числа и соберите непрерывную линию ровно на 56.",
            "Игрок выбирает соседние клетки на компактном поле",
            "без повторного использования клеток",
            "Если это первый запуск, видит короткий onboarding из трёх правил.",
            "Приложение постоянно показывает текущую сумму, остаток до 56 и состояние линии.",
            "Если сумма ровно 56, уровень засчитывается и прогресс сохраняется.",
            "Levels: список 36 уровней с состоянием прохождения и сложностью.",
            "36 deterministic уровней.",
            "Гарантированное решение каждого уровня на сумму 56.",
            "Независимый solver проверяет достижимость цели по самой доске",
            "current-line hint repair checks",
            "Выбор соседних клеток по горизонтали, вертикали и диагонали.",
            "Подсказка стартовой или следующей клетки от текущей линии",
            "сообщение предлагает отменить ход или сбросить линию",
            "No ads, no analytics, no accounts, no payments, no backend, no dangerous permissions.",
            "Пока сумма превышена, новые клетки и подсказка недоступны",
            "Все уровни доступны из списка; прогресс показывает, что уже пройдено.",
            "Passing the highest-numbered level alone is not treated as full completion",
            "Result action: after win the primary result action is «Следующий уровень» only when a higher available level id exists",
            "Continue routing: the primary home action resumes the last selected incomplete level",
            "DataStore I/O fallback",
            "No personal data collection.",
            "No network dependency.",
            "Android backup disabled",
            "Story campaign.",
            "Все 36 уровней имеют гарантированное решение.",
            "Unit tests prove every generated board is independently solvable by `LevelSolver`.",
            "Debug, unit, lint, release bundle and connected smoke checks pass where environment allows.",
        ],
    )


def check_content_audit_handoff() -> None:
    require_text_markers(
        "docs/content_audit.md",
        [
            "Onboarding rules: done.",
            "Home copy: done.",
            "Game status messages: done.",
            "Settings labels/descriptions: done.",
            "About/privacy text: done",
            "local-only progress/settings",
            "no ads/analytics/accounts/payments/internet permissions",
            "Android backup disabled",
            "local deletion through Android app data clearing or uninstall",
            "Level titles: deterministic `Уровень N`",
            "level tile status copy uses `Пройден` or `Доступен`",
            "no locked-level wording",
            "Store listing, data safety notes and privacy policy draft: done in `play_store`.",
            "Видимый UI на русском.",
            "Lorem ipsum отсутствует.",
            "Английские placeholder-строки в пользовательском UI отсутствуют.",
            "Main UI display strings are centralized in `app/src/main/res/values/strings.xml`",
            "`rg` found no Russian string literals in `app/src/main/java`",
            "Android string resources are release-gated by `tools/verify_release.py`",
            "Ошибки, подсказки и score labels понятны: соседняя клетка, повтор, превышение суммы, `Сумма`, `Цель`, `Осталось`.",
            "Button labels checked in screenshots; shortened labels avoid clipping in gameplay action bar.",
            "Store listing copy готова в checklist, но её нужно финально проверить владельцу продукта перед публикацией.",
        ],
    )


def check_ui_audit_handoff() -> None:
    require_text_markers(
        "docs/ui_audit.md",
        [
            "Colors: leaf green primary, warm gold accent, blue tertiary, clay secondary, mist background.",
            "Typography: sans-serif, compact mobile hierarchy, no negative letter spacing.",
            "Radii: 4-8dp, no pill-heavy style.",
            "States: selected, hinted, exceeded, disabled undo, completed level.",
            "First launch: onboarding visible, no text clipping on 1080x2400 API 35.",
            "Home: progress, start, levels, settings/about visible.",
            "Game: score panel, 5x5 board, controls visible; cell content descriptions present; the target metric uses `Цель` as the label and `56` as the value without duplicating `56` in both places.",
            "Hint repair state: if the selected line cannot still reach 56, no stale cell is highlighted",
            "Exceeded state: reducer and UI now keep the state recoverable by blocking additional board input and hint until undo/reset.",
            "Result state: after win the panel always exposes an explicit action",
            "Game back route: when a game is opened from the home CTA, back returns home",
            "Motion polish: cell selected/hint/exceeded states use short color/elevation transitions",
            "Haptics polish: tactile feedback now follows accepted game-state changes",
            "Store screenshot pass: action buttons no longer clip",
            "Responsive action bar pass: on compact widths the gameplay controls split into two rows",
            "Adaptive onboarding pass: normal 1080x2400 viewport centers the first-run screen",
            "compact 720x1280 with `font_scale=1.3` keeps the button fully visible",
            "Compact About/privacy pass: 720x1280, density 320, `font_scale=1.3`",
            "Wide/large pass: 2400x1080 landscape override uses a dedicated compact onboarding row layout",
            "Store icon is present and Play-format verified.",
            "Feature graphic was rebuilt after rejecting the previous text-heavy concept.",
            "Dedicated large/tablet Play screenshots were captured at 1600x2560 from the real release app",
        ],
    )


def check_accessibility_notes_handoff() -> None:
    require_text_markers(
        "docs/accessibility_notes.md",
        [
            "Tap targets для кнопок и клеток больше 48dp.",
            "Важные состояния не зависят только от цвета",
            "У клеток есть content descriptions",
            "Есть high contrast setting.",
            "Undo disabled state видим и семантически disabled.",
            "Reduced motion setting is functional",
            "Haptics setting is precise",
            "Compact landscape game layout keeps score, status text, action controls and the full 5x5 board",
            "720x1280 override, density 320, `font_scale=1.3`",
            "compact About/privacy pass",
            "docs/qa_artifacts/compact_about_top.png",
            "docs/qa_artifacts/compact_about_bottom.png",
            "Large/wide exploratory pass on API 35",
            "Compose instrumentation now checks accessible cell descriptions",
            "latest API 36 connected run passed 10 tests",
            "result-panel replay with `Повторить`",
            "Manual game landscape pass on API 35",
            "all 25 cells and `Отмена`/`Подсказка`/`Сброс` were visible",
            "Force-stop/relaunch after completion showed home progress and continue action",
            "UIAutomator accessibility-tree audit on API 35 with `font_scale=1.3`",
            "The game tree exposed 25 cell descriptions",
            "TalkBack exploratory pass completed on `Medium_Phone_API_36`",
            "touchExplorationEnabled=true",
            "docs/qa_artifacts/talkback_state.txt",
            "docs/qa_artifacts/talkback_onboarding.png",
            "docs/qa_artifacts/talkback_home.png",
            "docs/qa_artifacts/talkback_game.png",
            "docs/qa_artifacts/talkback_settings.png",
            "docs/qa_artifacts/talkback_about.png",
            "Optional physical-device TalkBack audio/speech review",
        ],
    )


def check_requirements_traceability() -> None:
    text = read("docs/requirements_traceability.md")
    for number in range(1, 17):
        require(f"Phase {number}" in text, f"requirements traceability missing Phase {number}")
    required_markers = [
        "Checked against the original RTF instruction and current local release candidate on 6 June 2026.",
        "Product discovery",
        "Product concept/spec",
        "Stack decision",
        "AGENTS handoff",
        "Architecture/code",
        "UI/UX",
        "Art direction and assets",
        "Content audit",
        "Localization",
        "Accessibility",
        "Performance",
        "Privacy, permissions and security",
        "Google Play readiness",
        "Testing and QA",
        "Documentation package",
        "Release report",
        "External Manual Gates",
        "play_store/owner_release_inputs.md",
        "verified hosted privacy-policy URL",
        "Play Console",
        "TalkBack",
    ]
    for marker in required_markers:
        require(marker in text, f"requirements traceability missing marker: {marker}")


def check_release_plan_handoff() -> None:
    require_text_markers(
        "docs/release_plan.md",
        [
            "Keep code frozen except bug fixes.",
            "Back up the generated upload keystore and credentials.",
            "Upload AAB to internal testing.",
            "Resolve `play_store/owner_release_inputs.md` and complete Play Console policy/listing forms.",
            "Run closed testing if account type requires it.",
            "`play_store/upload_manifest.md`",
            "`play_store/upload_runbook_ru.md`",
            "`play_store/play_console_post_upload_evidence_ru.md`",
            "`play_store/signing_backup_evidence_ru.md` as the safe signing-backup evidence and owner template",
            "`play_store/play_console_submission_ru.md`",
            "`play_store/app_content_answers_ru.md`",
            "`play_store/owner_release_inputs.md`",
            "`play_store/publication_readiness_owner_actions_ru.md` as the external owner-action breakdown",
            "`play_store/privacy_policy_ru.md`",
            "`play_store/privacy_policy_ru.html`",
            "host the HTML on a public HTTPS URL",
            "Keystore: `private/signing/qgrid-upload.p12`",
            "Credentials: `keystore.properties`",
            "Back them up securely before any Play Console upload.",
            "`./tools/check_signing_backup_inputs.py`",
            "`signing_backup_input_ok`",
            "`play_store/signing_backup_evidence_ru.md`",
            "`play_store/signing_certificate_report.md`",
            "QGRID_STORE_FILE",
            "QGRID_STORE_PASSWORD",
            "QGRID_KEY_ALIAS",
            "QGRID_KEY_PASSWORD",
            "Preferred single command:",
            "./tools/run_final_local_gate.py",
            "Equivalent expanded sequence:",
            "./tools/print_upload_packet.py",
            "./tools/create_store_asset_review_sheet.py --dry-run",
            "./tools/print_play_console_packet.py",
            "./tools/verify_play_generated_apk.py --dry-run",
            "./tools/check_privacy_policy_url.py --local",
            "./tools/check_signing_backup_inputs.py",
            "./gradlew clean",
            "./gradlew test",
            "./gradlew assembleDebug",
            "./gradlew lint",
            "./gradlew connectedDebugAndroidTest",
            "./gradlew bundleRelease",
            "./tools/verify_release.py",
        ],
    )


def check_release_report_handoff() -> None:
    require_text_markers(
        "docs/release_report.md",
        [
            "«Линия 56» - offline-first числовая головоломка",
            "Нейтральный `applicationId`: `com.qgrid.mobile`.",
            "36 deterministic уровней с гарантированным решением на сумму 56",
            "current-selection-aware hint with repair feedback",
            "no ads, no analytics, no payments, no `INTERNET`",
            "Android backup disabled with `android:allowBackup=\"false\"`",
            "Google Play upload manifest created at `play_store/upload_manifest.md`.",
            "Latest upload-runbook handoff hardening",
            "Latest final local gate runner hardening",
            "Latest final local gate execution",
            "`./gradlew test lint assembleDebug assembleRelease bundleRelease`",
            "play_upload_archive_existing_ok",
            "play_generated_apk_verify_dry_run_ok",
            "Latest upload-packet helper hardening",
            "Latest upload-packet negative-regression gate",
            "Latest store asset review sheet hardening",
            "Latest store asset review sheet negative-regression gate",
            "Latest masked icon preview freshness gate",
            "Latest Play upload archive helper hardening",
            "Latest Play upload archive negative-regression gate",
            "Latest generated upload archive freshness gate",
            "Latest Play upload archive generation",
            "Latest generated upload archive existing-verification hardening",
            "Latest signing handoff archive inclusion",
            "Latest Play Console packet helper hardening",
            "Latest Play Console packet negative-regression gate",
            "Latest Play-generated APK verification helper hardening",
            "Latest Play-generated APK verification negative-regression gate",
            "Latest Play-generated icon pixel-match helper hardening",
            "Latest owner evidence validation hardening",
            "Latest publication-readiness negative-regression gate",
            "Latest positive owner-gate evidence hardening",
            "Latest signing preflight evidence validation hardening",
            "Latest non-empty owner evidence hardening",
            "Latest owner date evidence hardening",
            "Latest testing-first release-track evidence hardening",
            "Latest closed-testing evidence consistency hardening",
            "Latest owner evidence secret-pattern hardening",
            "Latest post-upload evidence handoff hardening",
            "Latest owner backup-evidence specificity hardening",
            "Latest publication-readiness owner-action breakdown",
            "Latest owner-action handoff archive inclusion",
            "Latest owner-action handoff synchronization gate",
            "Latest final local gate after owner-action sync",
            "Latest completed owner-evidence fixture gate",
            "Latest privacy-policy URL helper hardening",
            "Latest hosted privacy policy exact-content hardening",
            "Latest hosted privacy owner-gate wording alignment",
            "Latest Play Console policy-form evidence hardening",
            "Latest Play support/contact evidence hardening",
            "Latest Play-generated version owner-evidence hardening",
            "Latest privacy helper negative-regression gate",
            "Latest signing-backup evidence hardening",
            "Latest signing-backup negative-regression gate",
            "Latest active-keystore backup evidence hardening",
            "Latest privacy URL query-parameter hardening",
            "Latest connected start-state isolation hardening",
            "Latest post-upload signing-evidence alignment",
            "Google Play upload checksum manifest created at `play_store/upload_checksums.md`.",
            "Copy-ready Play Console field handoff created at `play_store/play_console_submission_ru.md`.",
            "Field-by-field Play Console App content answer sheet created at `play_store/app_content_answers_ru.md`.",
            "Owner-controlled release-input checklist created at `play_store/owner_release_inputs.md`.",
            "Ready-to-host privacy policy HTML created at `play_store/privacy_policy_ru.html`",
            "Release phone and large/tablet screenshots captured from the real release app.",
            "Official Google Play source refresh",
            "Latest Google Play source spot-check on 6 June 2026",
            "Latest official source spot-check on 11 June 2026",
            "Latest final local gate after 11 June source audit",
            "Latest annotated remote tag handoff hardening",
            "Latest remote signing-artifact extension hardening",
            "Latest remote unexpected-AAB hardening",
            "Latest native 16 KB page-size verifier hardening",
            "Latest Play-generated native owner-evidence hardening",
            "Latest local signing-ignore extension hardening",
            "Latest case-insensitive signing-artifact hygiene hardening",
            "Latest local install-artifact ignore case hardening",
            "Latest semantic git-ignore verification hardening",
            "Latest local tracked forbidden-path hardening",
            "Latest current-package connected cleanup hardening",
            "Latest production-package connected focus cleanup hardening",
            "Latest privacy/signing handoff date refresh",
            "Latest completion/traceability date refresh",
            "Current API 36 connected check",
            "passed 10/10 tests on `Medium_Phone_API_36(AVD) - 16`",
            "Latest final release smoke check after onboarding/store screenshot polish",
            "docs/qa_artifacts/release_smoke_onboarding.png",
            "Latest release relaunch smoke check",
            "docs/qa_artifacts/release_relaunch_home.png",
            "docs/qa_artifacts/release_relaunch_state.txt",
            "Latest offline release smoke check",
            "docs/qa_artifacts/offline_release_smoke_onboarding.png",
            "docs/qa_artifacts/offline_release_smoke_game.png",
            "airplane_mode_on=1",
            "Wi-Fi is disabled",
            "Цель",
            "Клетка",
            "Latest release-level content gate",
            "Latest result replay hardening",
            "hint repair feedback for a dead-end line",
            "Latest AGENTS handoff hardening",
            "Latest signing-file hygiene hardening",
            "Latest optimistic completion progress hardening",
            "Latest owner-input handoff hardening",
            "Latest release-plan handoff hardening",
            "Latest tech-stack handoff hardening",
            "Latest Play app-content/content-rating handoff hardening",
            "Latest completion-audit handoff hardening",
            "Latest product-spec/content-audit handoff hardening",
            "Latest UI/accessibility/privacy handoff hardening",
            "Latest asset/art-direction handoff hardening",
            "Latest screenshot-manifest handoff hardening",
            "Latest responsive action bar hardening",
            "Latest neutral package and navigation evidence refresh",
            "LevelNavigation` plus `AppUiState` now de-duplicate available ids",
            "Latest empty-level UI-state guard",
            "Latest instrumentation state isolation hardening",
            "Latest connected start-state isolation hardening",
            "Latest home progress accessibility hardening",
            "Latest launcher ImageGen cleanup hardening",
            "Latest packaged launcher asset gate hardening",
            "Latest store screenshot automation hardening",
            "Latest store screenshot crop-validation hardening",
            "Latest saved store screenshot PNG validation hardening",
            "Latest feature graphic rebuild validation hardening",
            "Latest home progress visual polish",
            "Latest optional connected final-gate hardening",
            "Latest dirty-emulator connected cleanup hardening",
            "Latest optional connected final-gate execution",
            "`./tools/run_final_local_gate.py --include-connected --connected-serial emulator-5560` passed on `Medium_Phone_API_36(AVD) - 16`",
            "Latest managed API 36 connected-gate helper hardening",
            "Debug APK: `app/build/outputs/apk/debug/app-debug.apk`, package `com.qgrid.mobile.debug`, 19,833,279 bytes.",
            "Signed Release AAB: `app/build/outputs/bundle/release/app-release.aab`, 2,930,928 bytes.",
            "Upload runbook: `play_store/upload_runbook_ru.md`.",
            "Post-upload evidence template: `play_store/play_console_post_upload_evidence_ru.md`.",
            "Signing backup evidence and owner template: `play_store/signing_backup_evidence_ru.md`.",
            "Owner release inputs: `play_store/owner_release_inputs.md`.",
            "Release verifier: `tools/verify_release.py`.",
            "Final local gate runner: `tools/run_final_local_gate.py`.",
            "Managed API 36 connected gate helper: `tools/run_api36_connected_gate.py`.",
            "Upload packet helper: `tools/print_upload_packet.py`.",
            "Play Console packet helper: `tools/print_play_console_packet.py`.",
            "Privacy policy URL helper: `tools/check_privacy_policy_url.py`.",
            "Signing backup input helper: `tools/check_signing_backup_inputs.py`.",
            "Latest privacy-policy placeholder-removal hardening",
            "Need manual Play Console forms, owner inputs, entering the verified privacy policy URL in Play Console and populated Play Console support/contact fields.",
            "Публикация в Google Play still requires entering the verified privacy URL in Play Console, populated Play Console support/contact fields, keystore backup and Play Console forms.",
        ],
    )


def check_completion_audit_handoff() -> None:
    require_text_markers(
        "docs/completion_audit.md",
        [
            "Checked on 6 June 2026 against the original instruction and the current local release candidate.",
            "## Proven Complete",
            "Idea selected and documented with expanded product discovery",
            "MVP spec documented and expanded against the original RTF structure",
            "Native Android project implemented: Kotlin + Compose + Material 3.",
            "Neutral package id: `com.qgrid.mobile`.",
            "Core loop works: deterministic levels, independently solver-verified reachability",
            "current-selection-aware hint with repair feedback",
            "Game model validation rejects inconsistent board cell positions",
            "Russian UI strings: `app/src/main/res/values/strings.xml`",
            "Local progress/settings: DataStore Preferences",
            "No `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous/platform runtime permissions",
            "Android backup is disabled",
            "No backend, ads, analytics, payments, accounts or UGC.",
            "Unit tests pass: `./gradlew test`.",
            "Debug build passes: `./gradlew assembleDebug`.",
            "Lint passes with no issues: `./gradlew lint`.",
            "Signed release AAB builds: `./gradlew bundleRelease`.",
            "Production AAB cleanliness is checked by `tools/verify_release.py`",
            "current release AAB is 2,930,928 bytes and current debug APK is 19,833,279 bytes.",
            "latest connected run finished 10 tests covering product name",
            "Latest result replay hardening",
            "Release APK installed on API 35 emulator: `./gradlew installRelease`.",
            "Latest final release smoke check after onboarding/store screenshot polish",
            "docs/qa_artifacts/release_smoke_onboarding.png",
            "Latest release relaunch smoke check",
            "docs/qa_artifacts/release_relaunch_home.png",
            "docs/qa_artifacts/release_relaunch_state.txt",
            "Latest offline release smoke check",
            "docs/qa_artifacts/offline_release_smoke_onboarding.png",
            "docs/qa_artifacts/offline_release_smoke_game.png",
            "airplane_mode_on=1",
            "Wi-Fi is disabled",
            "Phone screenshots captured from real release app",
            "Large/tablet screenshots captured from real release app",
            "Google Play store icon created and verified",
            "Replacement feature graphic created and verified",
            "TalkBack exploratory pass completed on `Medium_Phone_API_36`",
            "Google Play listing/data-safety/privacy-policy drafts created",
            "Google Play upload manifest, upload checksums, Play Console field handoff, App content answer sheet, owner-input checklist, privacy hosting checklist and ready-to-host privacy policy HTML created",
            "Latest upload-runbook handoff hardening",
            "Latest upload-packet helper hardening",
            "Latest upload-packet negative-regression gate",
            "Latest store asset review sheet hardening",
            "Latest store asset review sheet negative-regression gate",
            "Latest masked icon preview freshness gate",
            "Latest Play upload archive helper hardening",
            "Latest Play upload archive negative-regression gate",
            "Latest generated upload archive freshness gate",
            "Latest Play upload archive generation",
            "Latest generated upload archive existing-verification hardening",
            "Latest signing handoff archive inclusion",
            "Latest Play Console packet helper hardening",
            "Latest Play Console packet negative-regression gate",
            "Latest Play-generated APK verification helper hardening",
            "Latest Play-generated APK verification negative-regression gate",
            "Latest Play-generated icon pixel-match helper hardening",
            "Latest owner evidence validation hardening",
            "Latest positive owner-gate evidence hardening",
            "Latest signing preflight evidence validation hardening",
            "Latest non-empty owner evidence hardening",
            "Latest owner date evidence hardening",
            "Latest testing-first release-track evidence hardening",
            "Latest owner evidence secret-pattern hardening",
            "Latest post-upload evidence handoff hardening",
            "Latest owner backup-evidence specificity hardening",
            "Latest publication-readiness owner-action breakdown",
            "Latest owner-action handoff archive inclusion",
            "Latest owner-action handoff synchronization gate",
            "Latest final local gate after owner-action sync",
            "Latest completed owner-evidence fixture gate",
            "Latest privacy-policy URL helper hardening",
            "Latest hosted privacy policy exact-content hardening",
            "Latest hosted privacy owner-gate wording alignment",
            "Latest Play Console policy-form evidence hardening",
            "Latest Play support/contact evidence hardening",
            "Latest Play-generated version owner-evidence hardening",
            "Latest privacy helper negative-regression gate",
            "Latest signing-backup evidence hardening",
            "Latest signing-backup negative-regression gate",
            "Latest active-keystore backup evidence hardening",
            "Latest privacy URL query-parameter hardening",
            "Latest post-upload signing-evidence alignment",
            "Latest final local gate runner hardening",
            "Latest final local gate execution",
            "play_upload_archive_existing_ok",
            "play_generated_apk_verify_dry_run_ok",
            "Store metadata is verifier-checked",
            "Privacy/data-safety/content-rating handoff is verifier-checked",
            "App content answer sheet is verifier-checked",
            "Public signing certificate handoff created",
            "Secret hygiene is verifier-checked",
            "Google Play official source check documented: `docs/google_play_sources.md`.",
            "Latest Google Play source spot-check on 6 June 2026",
            "Latest Google Play source spot-check on 11 June 2026",
            "Latest final local gate after 11 June source audit",
            "Latest annotated remote tag handoff hardening",
            "Latest remote signing-artifact extension hardening",
            "Latest remote unexpected-AAB hardening",
            "Latest native 16 KB page-size verifier hardening",
            "Latest Play-generated native owner-evidence hardening",
            "Latest local signing-ignore extension hardening",
            "Latest case-insensitive signing-artifact hygiene hardening",
            "Latest local install-artifact ignore case hardening",
            "Latest semantic git-ignore verification hardening",
            "Latest local tracked forbidden-path hardening",
            "Latest current-package connected cleanup hardening",
            "Latest production-package connected focus cleanup hardening",
            "Latest privacy/signing handoff date refresh",
            "Latest completion/traceability date refresh",
            "Requirements traceability matrix created and verifier-gated",
            "Release verifier created and passing: `tools/verify_release.py`",
            "Latest AGENTS handoff hardening",
            "Latest signing-file hygiene hardening",
            "Latest owner-input handoff hardening",
            "Latest release-plan handoff hardening",
            "Latest tech-stack handoff hardening",
            "Latest Play app-content/content-rating handoff hardening",
            "Latest release-report handoff hardening",
            "Latest Google Play checklist handoff hardening",
            "Latest QA test-plan handoff hardening",
            "Latest discreet package gate hardening",
            "Latest neutral package and navigation evidence refresh",
            "LevelNavigation` plus `AppUiState` now de-duplicate available ids",
            "Latest product-spec/content-audit handoff hardening",
            "Latest UI/accessibility/privacy handoff hardening",
            "Latest asset/art-direction handoff hardening",
            "Latest screenshot-manifest handoff hardening",
            "Latest completion-audit handoff hardening",
            "## Not Yet Fully Proven Final",
            "Latest privacy-policy placeholder-removal hardening",
            "Latest empty-level UI-state guard",
            "Latest release-level content gate",
            "Latest instrumentation state isolation hardening",
            "Latest home progress accessibility hardening",
            "Latest launcher ImageGen cleanup hardening",
            "Latest packaged launcher asset gate hardening",
            "Latest store screenshot automation hardening",
            "Latest store screenshot crop-validation hardening",
            "Latest saved store screenshot PNG validation hardening",
            "Latest feature graphic rebuild validation hardening",
            "Latest home progress visual polish",
            "Latest optional connected final-gate hardening",
            "Latest dirty-emulator connected cleanup hardening",
            "Latest optional connected final-gate execution",
            "`./tools/run_final_local_gate.py --include-connected --connected-serial emulator-5560` passed on `Medium_Phone_API_36(AVD) - 16`",
            "Latest managed API 36 connected-gate helper hardening",
            "Latest publication-readiness negative-regression gate",
            "Latest closed-testing evidence consistency hardening",
            "Privacy policy text and HTML are hosted at `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` and passed `privacy_policy_url_ok`, but final publication still needs that URL entered in Play Console plus populated Play Console support/contact fields.",
            "Play Console forms are not completed because they require account access.",
            "Closed testing cannot be completed locally; account type and testers are external.",
            "Owner release inputs in `play_store/owner_release_inputs.md` require real owner decisions before upload.",
            "Signing backup local inputs are preflight-checked and safely recorded",
            "## Current Verdict",
            "strong signed code release candidate",
            "not yet a fully publication-complete Google Play product",
            "Play Console privacy URL entry, Play Console support/contact fields, signing backup and Play Console/account actions remain outside the local codebase",
        ],
    )


def check_qa_test_plan_handoff() -> None:
    require_text_markers(
        "docs/qa_test_plan.md",
        [
            "Unit tests: level generation, canonical solution sum, adjacency, independent solver reachability, reducer, undo/reset, progress defaults and corrupted progress normalization.",
            "Unit tests also cover model validation",
            "current-selection-aware hints",
            "exceeded-state lock",
            "reducer input hardening",
            "immutable win state",
            "continue routing",
            "level navigation boundaries",
            "final result copy",
            "final result action fallback",
            "Instrumentation: Compose tests reset local DataStore state before each test",
            "About/privacy policy text",
            "three-level progression",
            "highest-level result fallback to `К уровням`",
            "result replay after win with `Повторить`",
            "game-back return to the entry screen",
            "home progress semantics",
            "DataStore progress write and Activity recreation after win",
            "Small-screen/font-scale pass: `wm size 720x1280`, density `320`, `font_scale=1.3`",
            "Large/tablet store screenshot pass",
            "Game landscape pass",
            "Non-TalkBack accessibility audit",
            "TalkBack exploratory pass",
            "`play_store/screenshots/phone/01_onboarding.png`",
            "`play_store/screenshots/phone/05_settings.png`",
            "`docs/qa_artifacts/compact_about_top.png`",
            "`docs/qa_artifacts/talkback_state.txt`",
            "Latest final release smoke check after onboarding/store screenshot polish",
            "docs/qa_artifacts/release_smoke_onboarding.png",
            "accessibility_enabled=0",
            "touch_exploration_enabled=0",
            "cold-launched in 189 ms",
            "Latest release relaunch smoke check",
            "docs/qa_artifacts/release_relaunch_home.png",
            "docs/qa_artifacts/release_relaunch_state.txt",
            "force-stop/relaunch",
            "background return",
            "Latest offline release smoke check",
            "docs/qa_artifacts/offline_release_smoke_onboarding.png",
            "docs/qa_artifacts/offline_release_smoke_game.png",
            "airplane-mode enabled",
            "airplane_mode_on=1",
            "Wi-Fi is disabled",
            "cold-launched in 202 ms",
            "Прогресс",
            "Цель",
            "Клетка",
            "Latest permissions gate",
            "Latest release AAB cleanliness gate",
            "Current API 36 connected smoke test",
            "passed 10/10 tests on `Medium_Phone_API_36(AVD) - 16`",
            "portrait onboarding spacing polish and Play screenshot recapture",
            "Latest result replay hardening",
            "completedResultCanReplayCurrentLevel",
            "hint repair UI coverage",
            "duplicate-level navigation evidence refresh",
            "duplicate level lists",
            "Latest empty-level UI-state regression guard",
            "Latest instrumentation state isolation hardening",
            "Latest home progress accessibility hardening",
            "Latest hint logic hardening",
            "Latest instrumentation order-independent hardening",
            "Latest connected start-state isolation hardening",
            "Latest release relaunch smoke check",
            "Latest compact About/privacy artifact gate",
            "Latest TalkBack artifact gate",
            "Earlier emulator cleanup check",
            "## Remaining Manual QA",
            "Re-capture screenshots after final icon/feature graphic art pass only if app UI changes.",
            "`ANDROID_SERIAL=<serial> ./tools/capture_store_screenshots.py --serial <serial>`",
            "the script updates `play_store/upload_checksums.md`, prints the current checksum rows",
        ],
    )


def check_sensitive_files_ignored() -> None:
    entries = {
        line.strip()
        for line in read(".gitignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    required_entries = {
        "[lL][oO][cC][aA][lL].[pP][rR][oO][pP][eE][rR][tT][iI][eE][sS]",
        "[kK][eE][yY][sS][tT][oO][rR][eE].[pP][rR][oO][pP][eE][rR][tT][iI][eE][sS]",
        "*.[jJ][kK][sS]",
        "*.[kK][eE][yY][sS][tT][oO][rR][eE]",
        "*.[pP]12",
        "*.[pP][eE][mM]",
        "*.[pP][kK]8",
        "*.[kK][eE][yY]",
        "*.[aA][pP][kK]",
        "*.[aA][aA][bB]",
        "*.[aA][pP][kK][sS]",
        "*.[iI][dD][sS][iI][gG]",
        "private/",
        "app/build/",
    }
    for entry in required_entries:
        require(entry in entries, f".gitignore must ignore {entry}")

    git_ignore_cases = [
        "local.properties",
        "LOCAL.PROPERTIES",
        "keystore.properties",
        "KEYSTORE.PROPERTIES",
        "private/signing/qgrid-upload.p12",
        "PRIVATE/SIGNING/QGRID-UPLOAD.P12",
        "release/upload.jks",
        "release/UPLOAD.JKS",
        "release/upload.keystore",
        "release/UPLOAD.KEYSTORE",
        "release/upload.pem",
        "release/UPLOAD.PEM",
        "release/upload.pk8",
        "release/UPLOAD.PK8",
        "release/upload.key",
        "release/UPLOAD.KEY",
        "app-release.apk",
        "APP-RELEASE.APK",
        "play.aab",
        "PLAY.AAB",
        "bundle.apks",
        "BUNDLE.APKS",
        "artifact.idsig",
        "ARTIFACT.IDSIG",
    ]
    for ignored_path in git_ignore_cases:
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", "--", ignored_path],
            cwd=ROOT,
            check=False,
        )
        require(ignored.returncode == 0, f".gitignore must ignore sensitive path case: {ignored_path}")

    tracked_output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    tracked_paths = [path for path in tracked_output.decode("utf-8").split("\0") if path]
    allowed_tracked_aab = "app/build/outputs/bundle/release/app-release.aab"
    forbidden_tracked_paths: list[str] = []
    for tracked_path in tracked_paths:
        lowered = tracked_path.lower()
        suffix = Path(lowered).suffix
        if lowered in {"local.properties", "keystore.properties"}:
            forbidden_tracked_paths.append(tracked_path)
        elif lowered.startswith("private/"):
            forbidden_tracked_paths.append(tracked_path)
        elif suffix in {".jks", ".keystore", ".p12", ".pem", ".pk8", ".key", ".apk", ".apks", ".idsig"}:
            forbidden_tracked_paths.append(tracked_path)
        elif suffix == ".aab" and tracked_path != allowed_tracked_aab:
            forbidden_tracked_paths.append(tracked_path)
    require(
        not forbidden_tracked_paths,
        f"git index contains forbidden sensitive/install paths: {forbidden_tracked_paths}",
    )

    sensitive_local_paths = [ROOT / "local.properties", ROOT / "keystore.properties"]
    sensitive_signing_suffixes = {".jks", ".keystore", ".p12", ".pem", ".pk8", ".key"}
    signing_dir = ROOT / "private/signing"
    if signing_dir.exists():
        sensitive_local_paths.extend(
            sorted(
                path
                for path in signing_dir.iterdir()
                if path.is_file() and path.suffix.lower() in sensitive_signing_suffixes
            )
        )

    for file_path in sensitive_local_paths:
        path = file_path.relative_to(ROOT).as_posix()
        file_path = ROOT / path
        if file_path.exists():
            mode = file_path.stat().st_mode
            require(mode & 0o077 == 0, f"{path} must not be group/world readable")

    upload_manifest = read("play_store/upload_manifest.md")
    require("## Do Not Upload" in upload_manifest, "upload manifest missing do-not-upload section for signing hygiene")
    do_not_upload_section = upload_manifest.split("## Do Not Upload", 1)[1].split("## Final Manual Gate", 1)[0]
    if signing_dir.exists():
        for file_path in sorted(signing_dir.glob("*.p12")):
            path = file_path.relative_to(ROOT).as_posix()
            require(f"`{path}`" in do_not_upload_section, f"local signing file missing from do-not-upload section: {path}")
            require(f"`{path}`" not in upload_manifest.split("## Upload To Play Console", 1)[1].split("## Release Handoff References", 1)[0], f"local signing file must not be in upload section: {path}")

    keystore_path = ROOT / "keystore.properties"
    if keystore_path.exists():
        properties: dict[str, str] = {}
        for line in keystore_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            properties[key.strip()] = value.strip()
        require(
            properties.get("storeFile", "").endswith("/private/signing/qgrid-upload.p12") or
            properties.get("storeFile", "") == "private/signing/qgrid-upload.p12",
            "keystore.properties must point to private/signing/qgrid-upload.p12",
        )
        require(properties.get("keyAlias") == "qgrid_upload", "keystore.properties must use keyAlias=qgrid_upload")
        require("line56" not in properties.get("storeFile", "").lower(), "keystore.properties must not use the old obvious signing file")


def release_facing_text_files() -> list[Path]:
    roots = [
        "README.md",
        "AGENTS.md",
        "docs",
        "play_store",
        "app/src/main",
        "app/proguard-rules.pro",
        "app/build.gradle.kts",
        "build.gradle.kts",
        "settings.gradle.kts",
        "gradle.properties",
    ]
    allowed_suffixes = {".kt", ".kts", ".xml", ".md", ".pro", ".properties", ".html", ".txt"}
    files: list[Path] = []
    for root_name in roots:
        root_path = ROOT / root_name
        candidates = [root_path] if root_path.is_file() else [path for path in root_path.rglob("*") if path.is_file()]
        for path in candidates:
            if path.suffix.lower() in allowed_suffixes:
                files.append(path)
    return files


def check_no_committed_secret_values() -> None:
    forbidden_patterns = [
        (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)?PRIVATE KEY-----"), "private key block"),
        (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
        (re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"), "Google API key"),
        (re.compile(r"\bghp_[0-9A-Za-z_]{20,}\b"), "GitHub token"),
        (re.compile(r"\bgithub_pat_[0-9A-Za-z_]+\b"), "GitHub fine-grained token"),
        (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI-style API key"),
        (re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b"), "Slack token"),
        (re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9._-]{16,}", re.I), "Bearer token"),
        (
            re.compile(r"https?://(?:localhost|127\.0\.0\.1|10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[0-1])\.)", re.I),
            "local/private URL",
        ),
    ]
    assignment_pattern = re.compile(
        r"\b(api[_-]?key|apikey|client[_-]?secret|access[_-]?token|auth[_-]?token|bearer[_-]?token|refresh[_-]?token|password|passwd)\b"
        r"\s*[:=]\s*['\"]?([^'\"\s,;]+)",
        re.I,
    )
    safe_assignment_values = {"...", "null", "false", "true"}

    for file_path in release_facing_text_files():
        relative_path = file_path.relative_to(ROOT)
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for pattern, label in forbidden_patterns:
            require(pattern.search(text) is None, f"{relative_path} contains forbidden {label}")

        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in assignment_pattern.finditer(line):
                value = match.group(2).strip()
                if value in safe_assignment_values:
                    continue
                if value.startswith("releaseSigningValue(") or value.startswith("System.getenv("):
                    continue
                if re.fullmatch(r"[A-Z][A-Z0-9_]{4,}", value):
                    continue
                require(False, f"{relative_path}:{line_number} contains suspicious secret assignment for {match.group(1)}")


def check_manifest_source() -> None:
    text = read("app/src/main/AndroidManifest.xml")
    require('android:allowBackup="false"' in text, "manifest must disable Android backup")
    require('android:label="@string/app_name"' in text, "manifest label must reference @string/app_name")
    require('android:name=".MainActivity"' in text, "manifest must expose only MainActivity as app entry point")
    require('android:exported="true"' in text, "launcher MainActivity must be exported for Android 12+")
    require('android.intent.action.MAIN' in text, "manifest must keep MAIN launcher action")
    require('android.intent.category.LAUNCHER' in text, "manifest must keep LAUNCHER category")
    require(text.count("<activity") == 1, "source manifest must declare exactly one activity")
    require("<service" not in text, "source manifest must not declare services")
    require("<receiver" not in text, "source manifest must not declare receivers")
    require("<provider" not in text, "source manifest must not declare providers")
    require("<uses-permission" not in text, "source manifest must not request permissions")
    require("dataExtractionRules" not in text, "manifest must not define dataExtractionRules")
    require("fullBackupContent" not in text, "manifest must not define fullBackupContent")
    require(not (ROOT / "app/src/main/res/xml/backup_rules.xml").exists(), "backup_rules.xml should not exist")
    require(not (ROOT / "app/src/main/res/xml/data_extraction_rules.xml").exists(), "data_extraction_rules.xml should not exist")


def check_android_string_resources() -> None:
    strings_path = "app/src/main/res/values/strings.xml"
    root = ET.parse(ROOT / strings_path).getroot()
    strings: dict[str, str] = {}
    forbidden_patterns = [
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\blorem\b",
        r"\bipsum\b",
        r"\bplaceholder\b",
        r"\bsample\b",
        r"\bexample\b",
        r"\bdebug\b",
        r"\btest\b",
        r"Line 56",
        r"Line56",
    ]
    format_only_strings = {"level_tile_description"}

    for node in root.findall("string"):
        name = node.attrib.get("name", "").strip()
        value = "".join(node.itertext()).strip()
        require(name, f"{strings_path} contains string without name")
        require(name not in strings, f"{strings_path} contains duplicate string name: {name}")
        require(value, f"{strings_path} contains empty string: {name}")
        if name not in format_only_strings:
            require(re.search(r"[\u0400-\u04ff]", value) is not None, f"{strings_path}:{name} must be Russian user-facing text")
        for pattern in forbidden_patterns:
            require(re.search(pattern, name, re.I) is None, f"{strings_path}:{name} has forbidden resource-name marker {pattern!r}")
            require(re.search(pattern, value, re.I) is None, f"{strings_path}:{name} has forbidden text marker {pattern!r}")
        strings[name] = value

    require(len(strings) >= 40, f"{strings_path} should contain the full MVP UI copy set")
    require(strings.get("app_name") == "Линия 56", "app_name must be exactly Линия 56")
    require(strings.get("target_sum") == "Цель", "target_sum must be a short score-panel label without duplicated 56")
    require(strings.get("available") == "Доступен", "available level status must be named and labeled consistently")
    require("locked" not in strings, "accessible unlocked level status must not use misleading locked resource name")
    privacy_markers = {
        "privacy_body": "не собирает персональные данные",
        "privacy_data_local": "прогресс уровней",
        "privacy_no_services": "интернет-разрешения",
        "privacy_no_backup": "Android backup отключён",
        "privacy_delete": "очистите данные приложения",
    }
    for name, marker in privacy_markers.items():
        require(marker in strings.get(name, ""), f"{strings_path}:{name} missing in-app privacy marker: {marker}")
    require(
        "Отмените ход или сбросьте линию" in strings.get("hint_repair", ""),
        f"{strings_path}:hint_repair must tell the player to undo or reset an unsalvageable line",
    )


def check_dependency_surface() -> None:
    gradle_text = read("app/build.gradle.kts")
    required_dependencies = [
        "androidx.activity:activity-compose",
        "androidx.compose.material3:material3",
        "androidx.datastore:datastore-preferences",
        "androidx.lifecycle:lifecycle-viewmodel-compose",
        "junit:junit",
        "androidx.compose.ui:ui-test-junit4",
    ]
    for dependency in required_dependencies:
        require(dependency in gradle_text, f"app build file missing expected lightweight dependency: {dependency}")

    forbidden_markers = [
        "firebase",
        "crashlytics",
        "play-services-ads",
        "play-services-analytics",
        "play-services-auth",
        "play-services-location",
        "com.android.billingclient",
        "billing-ktx",
        "appsflyer",
        "adjust",
        "amplitude",
        "segment",
        "mixpanel",
        "sentry",
        "datadog",
        "bugsnag",
        "onesignal",
        "facebook-android-sdk",
        "retrofit",
        "okhttp",
        "ktor-client",
        "coil-compose",
        "glide",
        "picasso",
        "room-runtime",
        "work-runtime",
    ]
    lowered = gradle_text.lower()
    for marker in forbidden_markers:
        require(marker not in lowered, f"unexpected dependency marker in app build file: {marker}")


def check_merged_manifests_permissions() -> None:
    for path in [
        "app/build/intermediates/merged_manifests/debug/processDebugManifest/AndroidManifest.xml",
        "app/build/intermediates/merged_manifests/release/processReleaseManifest/AndroidManifest.xml",
    ]:
        manifest = ROOT / path
        require(manifest.is_file(), f"missing merged manifest: {path}")
        text = manifest.read_text(encoding="utf-8")
        require("android.permission.INTERNET" not in text, f"{path} must not request INTERNET")
        require("android.permission.ACCESS_NETWORK_STATE" not in text, f"{path} must not request ACCESS_NETWORK_STATE")
        require("android.permission.CAMERA" not in text, f"{path} must not request CAMERA")
        require("android.permission.RECORD_AUDIO" not in text, f"{path} must not request RECORD_AUDIO")
        require("android.permission.ACCESS_FINE_LOCATION" not in text, f"{path} must not request location")
        require("android.permission.READ_EXTERNAL_STORAGE" not in text, f"{path} must not request external storage")
        require("android.permission.READ_MEDIA_IMAGES" not in text, f"{path} must not request media images")


def check_debug_apk_permissions() -> None:
    apk = require_file("app/build/outputs/apk/debug/app-debug.apk")
    aapt = resolve_aapt()
    output = subprocess.check_output(
        [str(aapt), "dump", "permissions", str(apk)],
        text=True,
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    permission_lines = [line for line in lines if line.startswith("uses-permission:")]
    allowed = {"uses-permission: name='com.qgrid.mobile.debug.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION'"}
    unexpected = [line for line in permission_lines if line not in allowed]
    require(not unexpected, f"debug APK requests unexpected permissions: {unexpected}")
    require("android.permission.INTERNET" not in output, "debug APK must not request INTERNET")
    require("android.permission.ACCESS_NETWORK_STATE" not in output, "debug APK must not request ACCESS_NETWORK_STATE")


def check_debug_manifest_binary() -> None:
    apk = require_file("app/build/outputs/apk/debug/app-debug.apk")
    aapt = resolve_aapt()
    output = subprocess.check_output(
        [str(aapt), "dump", "xmltree", str(apk), "AndroidManifest.xml"],
        text=True,
    )
    require("android:allowBackup" in output, "debug APK manifest does not expose allowBackup")
    require("android:allowBackup(0x01010280)=(type 0x12)0x0" in output, "debug APK allowBackup is not false")
    require("fullBackupContent" not in output, "debug APK still has fullBackupContent")
    require("dataExtractionRules" not in output, "debug APK still has dataExtractionRules")


def check_aab_signature() -> None:
    aab = require_file("app/build/outputs/bundle/release/app-release.aab")
    jarsigner = resolve_jarsigner()
    output = subprocess.check_output(
        [str(jarsigner), "-verify", "-verbose", "-certs", str(aab)],
        stderr=subprocess.STDOUT,
        text=True,
    )
    require("jar verified." in output, "release AAB jarsigner verification did not pass")
    require("QuietGrid Upload" in output, "release AAB signer is not QuietGrid Upload")


def check_release_aab_clean() -> None:
    aab = require_file("app/build/outputs/bundle/release/app-release.aab")
    forbidden_entry_fragments = [
        "androidTest",
        "androidx/test",
        "espresso",
        "junit",
        "org/junit",
        "ui-test",
        "Line56AppSmokeTest",
        "com/ivliev",
        "com/qgrid/mobile/debug",
        "com/quietgrid/lattice",
        "com/quietgrid/numberpath",
    ]
    forbidden_payload_needles = [
        b"com.ivliev",
        b"com/ivliev",
        b"ivliev",
        b"andrej",
        b"com.qgrid.mobile.debug",
        b"com/qgrid/mobile/debug",
        b"com.quietgrid.lattice",
        b"com/quietgrid/lattice",
        b"com.quietgrid.numberpath",
        b"com/quietgrid/numberpath",
        b"androidx.test.espresso",
        b"androidx.test.ext",
        b"androidx.compose.ui.test",
        b"org.junit",
        b"junit.framework",
        b"Line56AppSmokeTest",
    ]

    with zipfile.ZipFile(aab) as archive:
        names = archive.namelist()
        require(
            "base/root/META-INF/version-control-info.textproto" not in names,
            "release AAB must not contain Git VCS metadata that changes after each release commit",
        )
        unexpected_entries = [
            name for name in names
            if any(fragment in name for fragment in forbidden_entry_fragments)
        ]
        require(not unexpected_entries, f"release AAB contains debug/test entries: {unexpected_entries}")

        for name in names:
            data = archive.read(name)
            for needle in forbidden_payload_needles:
                require(needle not in data, f"release AAB contains forbidden payload marker {needle!r} in {name}")


def check_release_native_library_alignment() -> None:
    aab = require_file("app/build/outputs/bundle/release/app-release.aab")
    native_library_names, minimum_alignment = native_library_alignment_summary(aab)
    expected_native_libraries = [
        "base/lib/arm64-v8a/libandroidx.graphics.path.so",
        "base/lib/arm64-v8a/libdatastore_shared_counter.so",
        "base/lib/armeabi-v7a/libandroidx.graphics.path.so",
        "base/lib/armeabi-v7a/libdatastore_shared_counter.so",
        "base/lib/x86/libandroidx.graphics.path.so",
        "base/lib/x86/libdatastore_shared_counter.so",
        "base/lib/x86_64/libandroidx.graphics.path.so",
        "base/lib/x86_64/libdatastore_shared_counter.so",
    ]
    require(native_library_names == expected_native_libraries, f"unexpected release AAB native libraries: {native_library_names}")
    require(
        minimum_alignment is not None and minimum_alignment >= REQUIRED_NATIVE_LOAD_ALIGNMENT,
        f"release AAB native libraries must support 16 KB page sizes; minimum PT_LOAD alignment is {minimum_alignment}",
    )


def check_build_artifact_freshness() -> None:
    common_inputs = existing_local_inputs(
        [
            "app/src/main",
            "app/build.gradle.kts",
            "build.gradle.kts",
            "settings.gradle.kts",
            "gradle.properties",
            "gradle/wrapper/gradle-wrapper.properties",
            "local.properties",
        ],
    )
    debug_input_mtime = latest_file_mtime(common_inputs)
    release_input_mtime = latest_file_mtime(
        common_inputs + [
            "app/proguard-rules.pro",
            "keystore.properties",
            "private/signing/qgrid-upload.p12",
        ],
    )

    debug_apk = require_file("app/build/outputs/apk/debug/app-debug.apk")
    require(
        debug_apk.stat().st_mtime >= debug_input_mtime,
        "debug APK is stale; rerun assembleDebug after app/build changes",
    )
    release_aab = require_file("app/build/outputs/bundle/release/app-release.aab")
    require(
        release_aab.stat().st_mtime >= release_input_mtime,
        "release AAB is stale; rerun bundleRelease after app/build/signing changes",
    )


def directory_size(path: Path) -> int:
    return sum(file_path.stat().st_size for file_path in path.rglob("*") if file_path.is_file())


def check_size_budgets() -> None:
    budgets = {
        "app/build/outputs/bundle/release/app-release.aab": 6 * 1024 * 1024,
        "app/build/outputs/apk/debug/app-debug.apk": 30 * 1024 * 1024,
        "play_store/feature_graphic.png": 1024 * 1024,
        "play_store/source_assets/feature_background_imagegen.png": 3 * 1024 * 1024,
    }
    for path, max_bytes in budgets.items():
        file_path = require_file(path)
        require(file_path.stat().st_size <= max_bytes, f"{path}: expected <= {max_bytes} bytes, got {file_path.stat().st_size}")

    for screenshot_dir in ["play_store/screenshots/phone", "play_store/screenshots/tablet"]:
        for screenshot in (ROOT / screenshot_dir).glob("*.png"):
            require(screenshot.stat().st_size <= 1024 * 1024, f"{screenshot.relative_to(ROOT)}: expected <= 1048576 bytes")

    play_store_size = directory_size(ROOT / "play_store")
    require(play_store_size <= 7 * 1024 * 1024, f"play_store directory expected <= 7MB, got {play_store_size} bytes")


def check_performance_notes() -> None:
    require_text_markers(
        "docs/performance_notes.md",
        [
            "Measured and re-verified on 6 June 2026",
            "Signed release AAB: `2,930,928` bytes",
            "Debug APK: `19,833,279` bytes",
            "Google Play feature graphic: `410,321` bytes",
            "Google Play store icon: `274,405` bytes",
            "Largest phone screenshot: `133,859` bytes",
            "Largest large/tablet screenshot: `98,888` bytes",
            "ImageGen source background: `1,577,241` bytes",
            "ImageGen source icon: `1,474,693` bytes",
            "`play_store` directory total: `6,111` KiB",
            "Native libraries in the signed release AAB: 8 `.so` files",
            "minimum `PT_LOAD` alignment is `0x4000` / 16,384 bytes",
            "Release AAB <= 6 MB",
            "Debug APK <= 30 MB",
            "Full `play_store` directory <= 7 MB",
            "Debug APK and release AAB freshness",
            "local SDK input (`local.properties` when present)",
        ],
    )


def check_art_direction_handoff() -> None:
    require_text_markers(
        "docs/art_direction.md",
        [
            "Чистая спокойная mobile puzzle эстетика",
            "контрастные числовые плитки",
            "аккуратная линия выбора",
            "минимум декоративных элементов",
            "Primary: deep leaf green.",
            "Accent: warm gold.",
            "Background: soft mist/off-white.",
            "Не использовать случайные иллюстрации, персонажей, псевдо-3D, блики, неон и fake UI.",
            "Текст должен быть live UI text, не нарисованный в картинке.",
            "App icon должна читаться в маленьком размере и не содержать мелкий текст.",
            "Feature graphic должен строиться на реальном UI/screenshot или качественной композиции",
            "Минималистичная, взрослая, спокойная головоломка",
            "Перегруженный баннер, случайный маскот, мелкий текст, фейковые карточки",
        ],
    )
    require_text_markers(
        "docs/asset_prompts.md",
        [
            "Store screenshots, the app icon and the feature graphic are present.",
            "minimalist numeric puzzle identity",
            "no text, no characters, no shadows, no clutter",
            "readable at 48px",
            "Не использовать fake UI, badges, random stats, mascots or decorative noise.",
            "Не добавлять англоязычные UI labels",
            "Final Feature Graphic Background Prompt",
            "with no text and no app UI",
            "premium, quiet, and adult",
            "Avoid any text, letters, numbers, words, logos, fake UI, phone mockups, screenshots, tiny details, noisy lines, stock-photo feel, AI artifacts and watermarks.",
            "Final composition: generated background from `play_store/source_assets/feature_background_imagegen.png` plus a real release gameplay crop from `play_store/screenshots/phone/04_game_line.png`.",
            "No promotional text was added.",
            "Не выглядит как временная AI-заглушка.",
            "Не копирует чужой бренд, игру, персонажа или UI.",
        ],
    )


def check_store_assets() -> None:
    app_ui = read("app/src/main/java/com/qgrid/mobile/ui/Line56App.kt")
    launcher_png_path = "app/src/main/res/drawable-nodpi/ic_launcher_imagegen.png"
    store_icon_path = "play_store/icon/play_icon_512.png"
    preview_icon_path = "play_store/icon/play_icon_preview_masked.png"
    adaptive_icon = read("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml")
    adaptive_round_icon = read("app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml")
    fallback_icon = read("app/src/main/res/mipmap/ic_launcher.xml")
    fallback_round_icon = read("app/src/main/res/mipmap/ic_launcher_round.xml")
    require("painterResource(R.drawable.ic_launcher_imagegen)" in app_ui, "onboarding NumberMark must reuse the final ImageGen launcher/store icon")
    require('text = "56"' not in app_ui, "onboarding NumberMark must not regress to a hard-coded 56 tile")
    require(not (ROOT / "app/src/main/res/drawable/ic_launcher_foreground.xml").exists(), "old vector launcher foreground must not remain in app resources")
    require('android:drawable="@drawable/ic_launcher_imagegen"' in adaptive_icon, "adaptive launcher icon must use the final ImageGen raster foreground")
    require('android:drawable="@drawable/ic_launcher_imagegen"' in adaptive_round_icon, "round adaptive launcher icon must use the final ImageGen raster foreground")
    require('android:src="@drawable/ic_launcher_imagegen"' in fallback_icon, "fallback launcher icon must use the final ImageGen raster bitmap")
    require('android:src="@drawable/ic_launcher_imagegen"' in fallback_round_icon, "round fallback launcher icon must use the final ImageGen raster bitmap")
    check_png(launcher_png_path, 512, 512, alpha=True, max_bytes=1024 * 1024)
    check_png(store_icon_path, 512, 512, alpha=True, max_bytes=1024 * 1024)
    check_png(preview_icon_path, 512, 512, alpha=True, max_bytes=1024 * 1024)
    require(
        (ROOT / preview_icon_path).stat().st_mtime >= (ROOT / store_icon_path).stat().st_mtime,
        "masked Play icon preview must be regenerated after play_store/icon/play_icon_512.png changes",
    )
    require(
        png_non_opaque_alpha_pixels(preview_icon_path) > 0,
        "play_store/icon/play_icon_preview_masked.png must contain transparent mask pixels, not a duplicate full-square icon",
    )
    require(
        png_non_opaque_alpha_pixels(launcher_png_path) == 0,
        "app launcher ImageGen PNG must be full-square with no transparent/semi-transparent pixels",
    )
    require(
        png_non_opaque_alpha_pixels(store_icon_path) == 0,
        "play_store/icon/play_icon_512.png must be full-square with no transparent/semi-transparent pixels; Google Play applies masking itself",
    )
    require(
        (ROOT / launcher_png_path).read_bytes() == (ROOT / store_icon_path).read_bytes(),
        "Android launcher ImageGen PNG and Google Play icon PNG must stay byte-for-byte identical",
    )
    release_aab = require_file("app/build/outputs/bundle/release/app-release.aab")
    with zipfile.ZipFile(release_aab) as archive:
        entries = set(archive.namelist())
        require(
            "base/res/drawable-nodpi-v4/ic_launcher_imagegen.png" in entries,
            "release AAB must package the ImageGen launcher PNG",
        )
        require(
            not any("ic_launcher_foreground" in entry for entry in entries),
            "release AAB must not contain the old vector launcher foreground",
        )
        packaged_icon = archive.read("base/res/drawable-nodpi-v4/ic_launcher_imagegen.png")
        require(packaged_icon.startswith(b"\x89PNG\r\n\x1a\n"), "packaged launcher icon in release AAB must be a PNG")
        require(packaged_icon[12:16] == b"IHDR", "packaged launcher icon in release AAB must have a PNG IHDR chunk")
        width, height, bit_depth, color_type = struct.unpack(">IIBB", packaged_icon[16:26])
        require((width, height) == (512, 512), f"packaged launcher icon in release AAB expected 512x512, got {width}x{height}")
        require(bit_depth == 8, f"packaged launcher icon in release AAB expected 8-bit PNG, got bit depth {bit_depth}")
        require(color_type in {2, 6}, f"packaged launcher icon in release AAB must be RGB/RGBA PNG after resource optimization, got color type {color_type}")
    check_png("play_store/feature_graphic.png", 1024, 500, alpha=False)
    for name in [
        "01_onboarding.png",
        "02_home.png",
        "03_game_start.png",
        "04_game_line.png",
        "05_settings.png",
    ]:
        check_play_screenshot_png(f"play_store/screenshots/phone/{name}", 1080, 2064)
        check_play_screenshot_png(f"play_store/screenshots/tablet/{name}", 1600, 2336)


def check_screenshot_manifest_handoff() -> None:
    manifest_path = "play_store/screenshots/manifest.md"
    text = read(manifest_path)
    require_text_markers(
        manifest_path,
        [
            "Phone device: Medium Phone API 35 emulator, captured at 1080x2400 and exported as 1080x2064, release variant `com.qgrid.mobile`.",
            "Large/tablet capture: same API 35 emulator with `wm size 1600x2560`, density `320`, exported as 1600x2336, release variant `com.qgrid.mobile`.",
            "Format: 24-bit PNG without alpha; Play screenshot long side is no more than 2x the short side; system status/navigation bars are cropped out of upload images.",
            "Capture command: `ANDROID_SERIAL=emulator-5562 ./tools/capture_store_screenshots.py --serial emulator-5562`",
            "captures phone files from the 1080x2400 app viewport, crops them to 1080x2064 Play-compliant PNGs, captures large/tablet files and crops them to 1600x2336, rebuilds `play_store/feature_graphic.png` and updates `play_store/upload_checksums.md`",
            "completed immediately afterward through the same capture helper functions on the restarted `emulator-5562`",
            "Screenshots are real app captures, not fake UI.",
            "They should be re-captured after any visual polish, icon replacement, or Play Console screenshot-size decision.",
        ],
    )
    require_text_markers(
        "tools/capture_store_screenshots.py",
        [
            "#!/usr/bin/env python3",
            "PACKAGE = \"com.qgrid.mobile\"",
            "PHONE_CAPTURE_SIZE = (1080, 2400)",
            "PHONE_UPLOAD_SIZE = (1080, 2064)",
            "PHONE_UPLOAD_CROP_BOX = (0, 96, PHONE_UPLOAD_SIZE[0], 96 + PHONE_UPLOAD_SIZE[1])",
            "TABLET_SIZE = (1600, 2560)",
            "TABLET_UPLOAD_SIZE = (1600, 2336)",
            "TABLET_UPLOAD_CROP_BOX = (0, 64, TABLET_UPLOAD_SIZE[0], 64 + TABLET_UPLOAD_SIZE[1])",
            "FEATURE_GRAPHIC_SIZE = (1024, 500)",
            "FEATURE_GAMEPLAY_CROP_BOX = (43, 200, 1040, 1540)",
            "FEATURE_GAMEPLAY_CROP_SIZE = (997, 1340)",
            "FEATURE_PANEL_SIZE = (335, 450)",
            "def capture_set(",
            "def crop_upload_image(",
            "is outside capture image",
            "def validate_saved_png(",
            "expected RGB PNG without alpha",
            "def rebuild_feature_graphic(",
            "validate_saved_png(out_path, FEATURE_GRAPHIC_SIZE)",
            "UPLOAD_CHECKSUM_PATH_SET = set(UPLOAD_CHECKSUM_PATHS)",
            "def parse_checksum_path_from_row(",
            "Bad upload checksum row",
            "def validate_upload_checksum_paths(",
            "duplicate rows",
            "unexpected upload rows",
            "row order must match the Play upload packet order",
            "def update_upload_checksums(",
            "exec-out\", \"uiautomator\", \"dump\", \"/dev/tty\"",
            "UI dump has no complete XML",
            "def print_checksum_rows(",
            "UPLOAD_CHECKSUM_PATHS = [",
            "play_store/upload_checksums.md",
            "--no-update-checksums",
            "./gradlew\", \"installRelease\"",
            "Image.open(io.BytesIO(png)).convert(\"RGB\")",
            "image = crop_upload_image(image, crop_box",
            "return image.crop(crop_box)",
            "play_store/screenshots/phone",
            "play_store/screenshots/tablet",
            "play_store/feature_graphic.png",
            "ANDROID_SERIAL",
        ],
    )
    expected_rows = {
        "phone/01_onboarding.png",
        "phone/02_home.png",
        "phone/03_game_start.png",
        "phone/04_game_line.png",
        "phone/05_settings.png",
        "tablet/01_onboarding.png",
        "tablet/02_home.png",
        "tablet/03_game_start.png",
        "tablet/04_game_line.png",
        "tablet/05_settings.png",
    }
    rows: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        require(len(parts) == 3, f"bad screenshot manifest row: {line}")
        path = parts[0].strip("`")
        purpose = parts[1]
        status = parts[2]
        require(path not in rows, f"duplicate screenshot manifest row: {path}")
        require(purpose, f"screenshot manifest purpose is empty: {path}")
        require(status == "RELEASE_READY", f"screenshot manifest status must be RELEASE_READY for {path}")
        require((ROOT / "play_store/screenshots" / path).is_file(), f"screenshot manifest file does not exist: {path}")
        rows[path] = (purpose, status)
    require(set(rows) == expected_rows, f"screenshot manifest paths mismatch: {sorted(set(rows) ^ expected_rows)}")

    visual_input_mtime = latest_file_mtime(
        [
            "app/src/main/java/com/qgrid/mobile/ui/Line56App.kt",
            "app/src/main/java/com/qgrid/mobile/ui/theme",
            "app/src/main/res/values/strings.xml",
            "app/src/main/res/values/colors.xml",
            "app/src/main/res/values/themes.xml",
        ],
    )
    for path in expected_rows:
        screenshot_path = ROOT / "play_store/screenshots" / path
        require(
            screenshot_path.stat().st_mtime >= visual_input_mtime,
            f"store screenshot is stale after UI/theme/string changes: {screenshot_path.relative_to(ROOT)}",
        )

    feature_graphic = ROOT / "play_store/feature_graphic.png"
    gameplay_screenshot = ROOT / "play_store/screenshots/phone/04_game_line.png"
    require(
        feature_graphic.stat().st_mtime >= gameplay_screenshot.stat().st_mtime,
        "feature graphic must be rebuilt after the gameplay screenshot crop changes",
    )

    helper = require_file("tools/capture_store_screenshots.py")
    spec = importlib.util.spec_from_file_location("line56_capture_store_screenshots", helper)
    require(spec is not None and spec.loader is not None, "cannot import store screenshot capture helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_upload_checksum_paths(list(module.UPLOAD_CHECKSUM_PATHS))

    try:
        module.parse_checksum_path_from_row("| `bad checksum row without closing tick |")
    except module.CaptureError as exc:
        require("Bad upload checksum row" in str(exc), f"capture helper rejected malformed checksum row with unexpected message: {exc}")
    else:
        raise CheckFailure("capture helper must reject malformed upload checksum rows")

    checksum_path_cases = [
        (list(module.UPLOAD_CHECKSUM_PATHS) + [module.UPLOAD_CHECKSUM_PATHS[0]], "duplicate rows"),
        (list(module.UPLOAD_CHECKSUM_PATHS[:-1]), "missing rows"),
        (list(module.UPLOAD_CHECKSUM_PATHS) + ["play_store/screenshots/phone/extra.png"], "unexpected upload rows"),
        ([module.UPLOAD_CHECKSUM_PATHS[1], module.UPLOAD_CHECKSUM_PATHS[0], *module.UPLOAD_CHECKSUM_PATHS[2:]], "row order must match the Play upload packet order"),
    ]
    for paths, expected_message in checksum_path_cases:
        try:
            module.validate_upload_checksum_paths(paths)
        except module.CaptureError as exc:
            require(expected_message in str(exc), f"capture helper rejected bad checksum path set with unexpected message: {exc}")
        else:
            raise CheckFailure(f"capture helper must reject bad checksum path set: {expected_message}")

    phone_image = module.Image.new("RGB", module.PHONE_CAPTURE_SIZE, "#ffffff")
    phone_crop = module.crop_upload_image(phone_image, module.PHONE_UPLOAD_CROP_BOX, "phone")
    require(phone_crop.size == module.PHONE_UPLOAD_SIZE, "phone upload crop must produce the documented upload size")

    tablet_image = module.Image.new("RGB", module.TABLET_SIZE, "#ffffff")
    tablet_crop = module.crop_upload_image(tablet_image, module.TABLET_UPLOAD_CROP_BOX, "tablet")
    require(tablet_crop.size == module.TABLET_UPLOAD_SIZE, "large/tablet upload crop must produce the documented upload size")

    feature_source_image = module.Image.new("RGB", module.PHONE_UPLOAD_SIZE, "#ffffff")
    feature_crop = module.crop_upload_image(feature_source_image, module.FEATURE_GAMEPLAY_CROP_BOX, "feature")
    require(feature_crop.size == module.FEATURE_GAMEPLAY_CROP_SIZE, "feature graphic gameplay crop must produce the documented crop size")

    try:
        module.crop_upload_image(module.Image.new("RGB", (500, 500), "#ffffff"), module.FEATURE_GAMEPLAY_CROP_BOX, "feature too small")
    except module.CaptureError as exc:
        require("is outside capture image" in str(exc), f"capture helper rejected too-small feature source with unexpected message: {exc}")
    else:
        raise CheckFailure("capture helper must reject feature graphic crops that exceed the source image")

    bad_crop_boxes = [
        (-1, 0, 100, 100),
        (0, 0, 0, 100),
        (0, 0, 100, 0),
        (0, 0, module.PHONE_CAPTURE_SIZE[0] + 1, 100),
        (0, 0, 100, module.PHONE_CAPTURE_SIZE[1] + 1),
    ]
    for crop_box in bad_crop_boxes:
        try:
            module.crop_upload_image(phone_image, crop_box, "bad phone crop")
        except module.CaptureError as exc:
            require("is outside capture image" in str(exc), f"capture helper rejected bad crop with unexpected message: {exc}")
        else:
            raise CheckFailure(f"capture helper must reject invalid crop box: {crop_box}")

    valid_png = ROOT / "build/verification/capture_saved_valid.png"
    wrong_size_png = ROOT / "build/verification/capture_saved_wrong_size.png"
    alpha_png = ROOT / "build/verification/capture_saved_alpha.png"
    jpeg_path = ROOT / "build/verification/capture_saved_jpeg.jpg"
    try:
        valid_png.parent.mkdir(parents=True, exist_ok=True)
        module.Image.new("RGB", (24, 16), "#ffffff").save(valid_png, format="PNG")
        module.validate_saved_png(valid_png, (24, 16))

        module.Image.new("RGB", (25, 16), "#ffffff").save(wrong_size_png, format="PNG")
        try:
            module.validate_saved_png(wrong_size_png, (24, 16))
        except module.CaptureError as exc:
            require("expected saved size" in str(exc), f"capture helper rejected wrong saved size with unexpected message: {exc}")
        else:
            raise CheckFailure("capture helper must reject saved screenshots with wrong dimensions")

        module.Image.new("RGBA", (24, 16), (255, 255, 255, 200)).save(alpha_png, format="PNG")
        try:
            module.validate_saved_png(alpha_png, (24, 16))
        except module.CaptureError as exc:
            require("expected RGB PNG without alpha" in str(exc), f"capture helper rejected alpha PNG with unexpected message: {exc}")
        else:
            raise CheckFailure("capture helper must reject saved screenshots with alpha")

        module.Image.new("RGB", (24, 16), "#ffffff").save(jpeg_path, format="JPEG")
        try:
            module.validate_saved_png(jpeg_path, (24, 16))
        except module.CaptureError as exc:
            require("expected PNG, got JPEG" in str(exc), f"capture helper rejected non-PNG screenshot with unexpected message: {exc}")
        else:
            raise CheckFailure("capture helper must reject saved screenshots that are not PNG")
    finally:
        for temporary_path in [valid_png, wrong_size_png, alpha_png, jpeg_path]:
            if temporary_path.exists():
                temporary_path.unlink()


def check_asset_handoff() -> None:
    require_text_markers(
        "docs/asset_manifest.md",
        [
            "`play_store/icon/play_icon_512.png`",
            "`play_store/icon/play_icon_preview_masked.png`",
            "`play_store/feature_graphic.png`",
            "`play_store/source_assets/feature_background_imagegen.png`",
            "`play_store/source_assets/icon_imagegen_20260606.png`",
            "`play_store/archive/icon_imagegen_20260605_rejected.png`",
            "`play_store/archive/icon_imagegen_20260606_rejected_owner_review.png`",
            "`play_store/archive/feature_graphic_concept.png`",
            "`play_store/store_asset_review_sheet.png`",
            "`docs/qa_artifacts/release_smoke_onboarding.png`",
            "`docs/qa_artifacts/offline_release_smoke_onboarding.png`",
            "`docs/qa_artifacts/offline_release_smoke_game.png`",
            "SOURCE_ONLY",
            "REJECTED_FOR_RELEASE",
            "RELEASE_READY",
            "QA_EVIDENCE",
            "the masked icon preview is source-only and must not be uploaded because Google Play applies its own mask",
            "phone screenshots are 1080x2064",
            "large/tablet screenshots are 1600x2336",
            "`play_store/store_asset_review_sheet.png` is an internal 1800x2050 RGB/24-bit review sheet",
            "release-smoke and offline-smoke QA captures are internal evidence only, not Play preview assets.",
            "The archived feature graphic concept and rejected previous icons remain rejected and are not used for Play upload.",
        ],
    )
    require_text_markers(
        "docs/rejected_assets.md",
        [
            "Previous Path Before Archive",
            "`play_store/archive/feature_graphic_concept.png`",
            "`play_store/archive/icon_imagegen_20260605_rejected.png`",
            "`play_store/archive/icon_imagegen_20260606_rejected_owner_review.png`",
            "Rejected for release upload",
            "self-made store creative",
            "embedded promotional text",
            "English `undo` label",
            "too toy-like and over-rendered",
            "the rejected concept no longer lives at that upload path",
            "rejected previous icons no longer live at that upload path",
            "no promotional text, no fake UI, no badge labels and no English UI fragments",
        ],
    )
    require_text_markers(
        "play_store/screenshots/manifest.md",
        [
            "Phone device: Medium Phone API 35 emulator, captured at 1080x2400 and exported as 1080x2064",
            "Large/tablet capture",
            "Format: 24-bit PNG without alpha; Play screenshot long side is no more than 2x the short side; system status/navigation bars are cropped out of upload images.",
            "`phone/01_onboarding.png`",
            "`phone/02_home.png`",
            "`phone/03_game_start.png`",
            "`phone/04_game_line.png`",
            "`phone/05_settings.png`",
            "`tablet/01_onboarding.png`",
            "`tablet/02_home.png`",
            "`tablet/03_game_start.png`",
            "`tablet/04_game_line.png`",
            "`tablet/05_settings.png`",
            "Screenshots are real app captures, not fake UI.",
        ],
    )

    upload_manifest = read("play_store/upload_manifest.md")
    require("## Upload To Play Console" in upload_manifest, "upload manifest missing upload section")
    require("## Do Not Upload" in upload_manifest, "upload manifest missing do-not-upload section")
    upload_section = upload_manifest.split("## Upload To Play Console", 1)[1].split("## Release Handoff References", 1)[0]
    do_not_upload_section = upload_manifest.split("## Do Not Upload", 1)[1].split("## Final Manual Gate", 1)[0]

    upload_paths = [
        "app/build/outputs/bundle/release/app-release.aab",
        "play_store/icon/play_icon_512.png",
        "play_store/feature_graphic.png",
        "play_store/screenshots/phone/01_onboarding.png",
        "play_store/screenshots/phone/02_home.png",
        "play_store/screenshots/phone/03_game_start.png",
        "play_store/screenshots/phone/04_game_line.png",
        "play_store/screenshots/phone/05_settings.png",
        "play_store/screenshots/tablet/01_onboarding.png",
        "play_store/screenshots/tablet/02_home.png",
        "play_store/screenshots/tablet/03_game_start.png",
        "play_store/screenshots/tablet/04_game_line.png",
        "play_store/screenshots/tablet/05_settings.png",
    ]
    for path in upload_paths:
        require(f"`{path}`" in upload_section, f"upload manifest upload section missing {path}")
    for marker in [
        "Release package: com.qgrid.mobile",
        "Version code: 1",
        "Version name: 1.0.0",
    ]:
        require(marker in upload_section, f"upload manifest upload section missing version identity marker: {marker}")

    source_or_rejected_paths = [
        "play_store/archive/feature_graphic_concept.png",
        "play_store/archive/icon_imagegen_20260605_rejected.png",
        "play_store/archive/icon_imagegen_20260606_rejected_owner_review.png",
        "play_store/source_assets/feature_background_imagegen.png",
        "play_store/source_assets/icon_imagegen_20260606.png",
        "play_store/icon/play_icon_preview_masked.png",
        "play_store/store_asset_review_sheet.png",
        "docs/qa_artifacts",
        "app/build/outputs/apk/debug/app-debug.apk",
        "app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk",
        "keystore.properties",
        "private/signing/qgrid-upload.p12",
        "private/signing/line56-upload.p12",
        "local.properties",
    ]
    for path in source_or_rejected_paths:
        require(f"`{path}`" not in upload_section, f"upload manifest upload section must not include {path}")
        require(f"`{path}`" in do_not_upload_section, f"upload manifest do-not-upload section missing {path}")
    for marker in [
        "Release APK outputs under app/build/outputs/apk/release",
        "Play upload uses the signed AAB listed above.",
    ]:
        require(marker in do_not_upload_section, f"upload manifest do-not-upload section missing release APK marker: {marker}")
    require("app-release.apk" not in upload_section, "upload manifest upload section must not include release APK output")

    require(
        "tools/capture_store_screenshots.py" in upload_manifest
        and "updates the checksum manifest automatically after a successful capture" in upload_manifest,
        "upload manifest must document automatic checksum refresh for store screenshot recapture",
    )
    require(
        "Signing backup evidence and owner template: `play_store/signing_backup_evidence_ru.md`" in upload_manifest,
        "upload manifest must include signing backup evidence and owner template handoff",
    )
    require(
        "Publication readiness owner actions: `play_store/publication_readiness_owner_actions_ru.md`" in upload_manifest,
        "upload manifest must include publication readiness owner-action handoff",
    )
    require(
        "Play Console packet helper: `tools/print_play_console_packet.py`" in upload_manifest,
        "upload manifest must include Play Console packet helper handoff",
    )
    require(
        "Store asset review sheet helper: `tools/create_store_asset_review_sheet.py`" in upload_manifest,
        "upload manifest must include store asset review helper handoff",
    )
    require(
        "Publication readiness helper: `tools/print_publication_readiness.py`" in upload_manifest,
        "upload manifest must include publication readiness helper handoff",
    )
    require(
        "Play-generated APK verification helper: `tools/verify_play_generated_apk.py`" in upload_manifest,
        "upload manifest must include Play-generated APK verification helper handoff",
    )
    require(
        "Play upload archive helper: `tools/prepare_play_upload_archive.py`" in upload_manifest,
        "upload manifest must include Play upload archive helper handoff",
    )
    require(
        "`build/play_upload/line56_v1_google_play_upload_packet.zip` - generated owner handoff archive only; unpack it and upload the individual files, not the ZIP itself."
        in do_not_upload_section,
        "upload manifest must keep generated upload archive out of Play uploads",
    )
    require(
        "`play_store/store_asset_review_sheet.png` - internal owner visual review sheet only; do not upload it to Play Console."
        in do_not_upload_section,
        "upload manifest must keep store asset review sheet out of Play uploads",
    )
    require(
        "Final local gate runner: `tools/run_final_local_gate.py`" in upload_manifest,
        "upload manifest must include final local gate runner handoff",
    )


def check_qa_artifacts() -> None:
    relaunch_helper = require_file("tools/capture_release_relaunch_smoke.py")
    require(os.access(relaunch_helper, os.X_OK), "tools/capture_release_relaunch_smoke.py must be executable")
    require_text_markers(
        "tools/capture_release_relaunch_smoke.py",
        [
            "Capture release background/relaunch smoke evidence on an adb device.",
            "PACKAGE = \"com.qgrid.mobile\"",
            "ACTIVITY = \"com.qgrid.mobile/.MainActivity\"",
            "STATE_PATH = ARTIFACT_DIR / \"release_relaunch_state.txt\"",
            "SCREENSHOT_PATH = ARTIFACT_DIR / \"release_relaunch_home.png\"",
            "from datetime import date",
            "date.today().isoformat()",
            "def normalize_expected_api(",
            "def validate_expected_api(",
            "def emulator_avd_name(",
            "--expected-api",
            "Use --expected-api any only for diagnostic runs",
            "installRelease",
            "uiautomator",
            "input\", \"keyevent\", \"3\"",
            "am\", \"force-stop\", PACKAGE",
            "home_progress_visible_after_relaunch=",
            "onboarding_not_visible_after_relaunch=",
            "crash_buffer=",
            "release_relaunch_smoke_ok",
        ],
    )
    spec = importlib.util.spec_from_file_location("line56_relaunch_smoke", relaunch_helper)
    require(spec is not None and spec.loader is not None, "could not import release relaunch smoke helper")
    relaunch_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(relaunch_module)
    require(relaunch_module.validate_expected_api("36", "36") == "36", "release relaunch smoke helper must accept API 36")
    require(relaunch_module.validate_expected_api("35", "any") == "any", "release relaunch smoke helper must accept explicit diagnostic any")
    try:
        relaunch_module.validate_expected_api("35", "36")
    except relaunch_module.RelaunchSmokeError:
        pass
    else:
        raise CheckFailure("release relaunch smoke helper must reject non-API36 targets by default")
    for bad_expected_api in ["", "   ", "api36", "latest", "036", "00"]:
        try:
            relaunch_module.normalize_expected_api(bad_expected_api)
        except relaunch_module.RelaunchSmokeError:
            continue
        raise CheckFailure(f"release relaunch smoke helper must reject malformed expected API: {bad_expected_api!r}")
    original_relaunch_adb = relaunch_module.adb
    try:
        relaunch_module.adb = lambda *args, **kwargs: "Medium_Phone_API_36\nOK\n"
        require(
            relaunch_module.emulator_avd_name("emulator-test") == "Medium_Phone_API_36",
            "release relaunch smoke helper must strip emulator-console OK noise from AVD name",
        )
    finally:
        relaunch_module.adb = original_relaunch_adb

    require_text_markers(
        "app/src/androidTest/java/com/qgrid/mobile/Line56AppSmokeTest.kt",
        [
            "repeat(6)",
            "@Before",
            "resetLocalStateBeforeEachTest",
            "val repository = ProgressRepository(composeRule.activity.applicationContext)",
            "clearLocalState()",
            "repository.setOnboardingSeen()",
            "currentProgress().completedLevelIds.isEmpty()",
            "completedLevelPersistsAfterActivityRecreation",
            "composeRule.activityRule.scenario.recreate()",
            "hasText(\"Соединяйте соседние клетки\", substring = true)",
            "hasText(\"Можно двигаться\", substring = true)",
            "hasText(\"Выберите уровень\")",
            "hasText(\"56 собрано\")",
            "hasContentDescription(\"Назад\", substring = true)",
            "pressBack()",
            "activity.onBackPressedDispatcher.onBackPressed()",
            "waitUntil(timeoutMillis = 10_000)",
            "highestLevelResultOffersLevelsFallbackAction",
            "hintRepairMessageAppearsForDeadEndLine",
            "gameBackReturnsToEntryScreen",
            "onNodeWithText(\"Цель\").assertIsDisplayed()",
            "нельзя довести до 56",
            "onNodeWithText(\"К уровням\")",
            "onAllNodesWithText(\"Следующий уровень\")",
            "onNodeWithText(\"Выберите уровень\")",
            "onNodeWithText(\"Прогресс\")",
        ],
    )
    android_test_source = read("app/src/androidTest/java/com/qgrid/mobile/Line56AppSmokeTest.kt")
    setup_body = android_test_source.split("fun resetLocalStateBeforeEachTest()", 1)[1].split("@Test", 1)[0]
    require(
        "composeRule.activityRule.scenario.recreate()" not in setup_body,
        "androidTest setup must not recreate Activity before each test; keep recreation in the dedicated persistence scenario",
    )
    require(
        "currentProgress().completedLevelIds.isEmpty()" in setup_body,
        "androidTest setup must wait for cleared progress before routing home",
    )
    check_png("docs/qa_artifacts/compact_about_top.png", 720, 1280, alpha=True, max_bytes=512 * 1024)
    check_png("docs/qa_artifacts/compact_about_bottom.png", 720, 1280, alpha=True, max_bytes=512 * 1024)
    check_png("docs/qa_artifacts/release_smoke_onboarding.png", 1080, 2400, alpha=True, max_bytes=512 * 1024)
    check_png("docs/qa_artifacts/release_relaunch_home.png", 1080, 2400, alpha=True, max_bytes=512 * 1024)
    check_png("docs/qa_artifacts/offline_release_smoke_onboarding.png", 1080, 2400, alpha=True, max_bytes=512 * 1024)
    check_png("docs/qa_artifacts/offline_release_smoke_game.png", 1080, 1920, alpha=True, max_bytes=512 * 1024)
    for name in [
        "talkback_onboarding.png",
        "talkback_home.png",
        "talkback_game.png",
        "talkback_settings.png",
        "talkback_about.png",
    ]:
        check_png(f"docs/qa_artifacts/{name}", 1080, 2400, alpha=True, max_bytes=512 * 1024)

    relaunch_state_path = require_file("docs/qa_artifacts/release_relaunch_state.txt")
    relaunch_screenshot_path = require_file("docs/qa_artifacts/release_relaunch_home.png")
    release_apk_path = require_file("app/build/outputs/apk/release/app-release.apk")
    relaunch_freshness_mtime = max(relaunch_helper.stat().st_mtime, release_apk_path.stat().st_mtime)
    require(
        relaunch_state_path.stat().st_mtime >= relaunch_freshness_mtime,
        "release relaunch state evidence is stale; rerun tools/capture_release_relaunch_smoke.py after release APK or helper changes",
    )
    require(
        relaunch_screenshot_path.stat().st_mtime >= relaunch_freshness_mtime,
        "release relaunch screenshot evidence is stale; rerun tools/capture_release_relaunch_smoke.py after release APK or helper changes",
    )

    talkback_state = read("docs/qa_artifacts/talkback_state.txt")
    for marker in [
        "Medium_Phone_API_36",
        "enabled_accessibility_services=com.google.android.marvin.talkback/.TalkBackService",
        "accessibility_enabled=1",
        "touchExplorationEnabled=true",
        "Service[label=TalkBack",
    ]:
        require(marker in talkback_state, f"TalkBack state evidence missing marker: {marker}")

    relaunch_state = read("docs/qa_artifacts/release_relaunch_state.txt")
    for marker in [
        "Release relaunch smoke evidence",
        "avd_name=Medium_Phone_API_36",
        "expected_api=36",
        "api=36",
        "package=com.qgrid.mobile",
        "com.qgrid.mobile/.MainActivity",
        "first_launch_command=am start -W -n com.qgrid.mobile/.MainActivity",
        "background_return_command=input keyevent HOME then am start -W",
        "force_stop_relaunch_command=am force-stop com.qgrid.mobile then am start -W",
        "home_progress_visible_after_relaunch=true",
        "home_start_action_visible_after_relaunch=true",
        "onboarding_not_visible_after_relaunch=true",
        "screenshot=docs/qa_artifacts/release_relaunch_home.png",
        "crash_buffer=no matching app crash entries",
        "release_relaunch_smoke_ok",
    ]:
        require(marker in relaunch_state, f"release relaunch smoke evidence missing marker: {marker}")
    require(
        re.search(r"(?m)^checked_on=\d{4}-\d{2}-\d{2}$", relaunch_state) is not None,
        "release relaunch smoke evidence must record checked_on as YYYY-MM-DD",
    )
    expected_api_match = re.search(r"(?m)^expected_api=(.+)$", relaunch_state)
    require(
        expected_api_match is not None and expected_api_match.group(1).strip() == "36",
        "release relaunch smoke evidence must record expected_api=36 and must not come from diagnostic --expected-api any mode",
    )

    qa_text = read("docs/qa_test_plan.md") + "\n" + read("docs/accessibility_notes.md")
    for marker in [
        "docs/qa_artifacts/compact_about_top.png",
        "docs/qa_artifacts/compact_about_bottom.png",
        "docs/qa_artifacts/talkback_onboarding.png",
        "docs/qa_artifacts/talkback_home.png",
        "docs/qa_artifacts/talkback_game.png",
        "docs/qa_artifacts/talkback_settings.png",
        "docs/qa_artifacts/talkback_about.png",
        "docs/qa_artifacts/talkback_state.txt",
        "docs/qa_artifacts/release_smoke_onboarding.png",
        "docs/qa_artifacts/release_relaunch_home.png",
        "docs/qa_artifacts/release_relaunch_state.txt",
        "docs/qa_artifacts/offline_release_smoke_onboarding.png",
        "docs/qa_artifacts/offline_release_smoke_game.png",
        "720x1280",
        "font_scale=1.3",
        "About/privacy pass",
        "TalkBack exploratory pass",
        "touchExplorationEnabled=true",
        "accessibility_enabled=0",
        "touch_exploration_enabled=0",
        "Current API 36 connected smoke test",
        "Latest release relaunch smoke check",
        "force-stop/relaunch",
        "background return",
        "Android 16 / API 36",
        "Medium_Phone_API_36(AVD) - 16",
        "fresh API 36 connected XML report",
        "Latest offline release smoke check",
        "airplane-mode enabled",
        "airplane_mode_on=1",
        "Wi-Fi is disabled",
        "Supplicant state: DISCONNECTED",
        "10/10 tests",
        "0 skipped and 0 failed tests",
        "result replay coverage",
        "order-independent",
    ]:
        require(marker in qa_text, f"QA docs missing compact About/privacy artifact marker: {marker}")


def check_connected_report_evidence() -> None:
    report_dir = ROOT / "app/build/outputs/androidTest-results/connected/debug"
    require(report_dir.exists(), f"missing connected test report directory: {report_dir.relative_to(ROOT)}")
    reports = sorted(report_dir.glob("TEST-*.xml"), key=lambda path: path.stat().st_mtime, reverse=True)
    require(bool(reports), f"missing connected test XML report in {report_dir.relative_to(ROOT)}")

    report = reports[0]
    require(
        "Medium_Phone_API_36" in report.name and "16" in report.name,
        f"connected report must come from the API 36 AVD, got {report.name}",
    )
    latest_source_mtime = latest_file_mtime(
        [
            "app/src/main",
            "app/src/androidTest",
            "app/build.gradle.kts",
            "build.gradle.kts",
            "settings.gradle.kts",
            "gradle.properties",
            "gradle/wrapper/gradle-wrapper.properties",
        ],
    )
    require(
        report.stat().st_mtime >= latest_source_mtime,
        f"connected report is stale; rerun connectedDebugAndroidTest after source/build changes: {report.relative_to(ROOT)}",
    )
    root = ET.parse(report).getroot()
    require(
        root.attrib.get("name") == "com.qgrid.mobile.Line56AppSmokeTest",
        f"connected report must be for com.qgrid.mobile.Line56AppSmokeTest, got {root.attrib.get('name')!r}",
    )
    device_property = next(
        (
            item.attrib.get("value", "")
            for item in root.findall("./properties/property")
            if item.attrib.get("name") == "device"
        ),
        "",
    )
    require(
        device_property == "Medium_Phone_API_36(AVD) - 16",
        f"connected report device property must be Medium_Phone_API_36(AVD) - 16, got {device_property!r}",
    )
    tests = int(root.attrib.get("tests", "-1"))
    failures = int(root.attrib.get("failures", "-1"))
    errors = int(root.attrib.get("errors", "-1"))
    skipped = int(root.attrib.get("skipped", "-1"))
    require(tests == 10, f"connected report must show 10 tests, got {tests}: {report}")
    require(failures == 0, f"connected report must show 0 failures, got {failures}: {report}")
    require(errors == 0, f"connected report must show 0 errors, got {errors}: {report}")
    require(skipped == 0, f"connected report must show 0 skipped tests, got {skipped}: {report}")

    testcase_names = {item.attrib.get("name", "") for item in root.findall("testcase")}
    testcase_classes = {item.attrib.get("classname", "") for item in root.findall("testcase")}
    require(
        testcase_classes == {"com.qgrid.mobile.Line56AppSmokeTest"},
        f"connected report contains unexpected testcase classes: {sorted(testcase_classes)}",
    )
    for expected in [
        "appShowsRussianProductName",
        "gameScreenExposesAccessibleBoardAndControls",
        "hintRepairMessageAppearsForDeadEndLine",
        "completedLevelPersistsAfterActivityRecreation",
        "completingSeveralLevelsAdvancesProgress",
        "highestLevelResultOffersLevelsFallbackAction",
        "completedResultCanReplayCurrentLevel",
        "gameBackReturnsToEntryScreen",
        "settingsScreenExposesAccessibleOptions",
        "aboutScreenExposesPrivacyPolicyText",
    ]:
        require(expected in testcase_names, f"connected report missing testcase {expected}: {report}")

    result_dir_name = report.name.removeprefix("TEST-").removesuffix("-_app-.xml")
    result_dir = report_dir / result_dir_name
    require(result_dir.is_dir(), f"missing connected result artifact directory: {result_dir.relative_to(ROOT)}")
    textproto = result_dir / "test-result.textproto"
    require(textproto.is_file(), f"missing connected textproto result: {textproto.relative_to(ROOT)}")
    textproto_text = textproto.read_text(encoding="utf-8", errors="ignore")
    require(
        textproto_text.count('test_package: "com.qgrid.mobile"') == 10,
        f"connected textproto must identify com.qgrid.mobile for all 10 tests: {textproto.relative_to(ROOT)}",
    )

    stale_markers = [
        "com.fiftyfive.seconds",
        "com.andrejivliev",
        "com.ivliev",
    ]
    text_artifacts = [
        *result_dir.glob("*.txt"),
        *result_dir.glob("*.log"),
        textproto,
    ]
    for artifact in text_artifacts:
        artifact_text = artifact.read_text(encoding="utf-8", errors="ignore")
        for marker in stale_markers:
            require(marker not in artifact_text, f"connected artifact contains stale package marker {marker}: {artifact.relative_to(ROOT)}")


def parse_backtick_paths(path: str) -> list[str]:
    text = read(path)
    return re.findall(r"`([^`]+)`", text)


def normalized_doc_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def check_publication_readiness_owner_actions_handoff() -> None:
    handoff_path = "play_store/publication_readiness_owner_actions_ru.md"
    require_text_markers(
        handoff_path,
        [
            "Publication Readiness Owner Actions - RU",
            "./tools/print_publication_readiness.py",
            "publication_readiness_local_ready_external_pending",
            "./tools/print_publication_readiness.py --check-recorded-privacy-url --require-production-ready",
            "пароли, private keys, keystore contents, Play account tokens",
            "Upload Artifact Identity",
            "play_store/play_console_post_upload_evidence_ru.md",
            "./tools/print_upload_packet.py",
            "Package must be `com.qgrid.mobile`.",
            "versionCode must be `1`.",
            "versionName must be `1.0.0`.",
            "First track must be internal testing; record closed testing separately if the publisher account requires it.",
            "Privacy Policy And Play Contact",
            "./tools/check_privacy_policy_url.py --local",
            "./tools/check_privacy_policy_url.py --url <https-url>",
            "URL must be public HTTPS, without credentials, query parameters or fragments.",
            "Hosted text must match `play_store/privacy_policy_ru.html`.",
            "Evidence must not use bare `yes`; it must explicitly say the Play Console support/contact field is populated and that the privacy policy uses the Google Play listing support contact.",
            "Signing Backup",
            "play_store/signing_backup_evidence_ru.md",
            "./tools/check_signing_backup_inputs.py",
            "`./tools/check_signing_backup_inputs.py` must return `signing_backup_input_ok`.",
            "Active-keystore backup evidence must explicitly mention `private/signing/qgrid-upload.p12` and `before AAB upload`.",
            "Active keystore is `private/signing/qgrid-upload.p12`.",
            "Active key alias is `qgrid_upload`.",
            "two owner-controlled secure copies exist and recovery was tested without exposing secrets",
            "Play-Generated Artifact Review",
            "./tools/verify_play_generated_apk.py --dry-run",
            "./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>",
            "Play-generated APK signature verifies and certificate SHA-256 recorded.",
            "Android Debug signing certificates",
            "missing/invalid APK signatures",
            "no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions",
            "icon pixels that differ from `play_store/icon/play_icon_512.png`",
            "application/round icon references that are not linked to that matching PNG",
            "native 16 KB page-size posture",
            "`extractNativeLibs=true`, compressed native libraries, native ZIP data offsets below 16 KB alignment",
            "native `.so` files below 16 KB ELF `PT_LOAD` alignment",
            "Version evidence must explicitly mention `versionCode 1` and `versionName 1.0.0`.",
            "Install/launch evidence must explicitly say the downloaded Play-generated APK was installed and launched on an Android device or Android emulator.",
            "Play Console Forms",
            "play_store/app_content_answers_ru.md",
            "play_store/data_safety_ru.md",
            "play_store/content_rating_notes.md",
            "Target audience should stay 13+ and non-child-directed",
            "Evidence must not use bare `yes`",
            "no restricted access/login/account, no ads, no user data collected/shared, Games / Puzzle content rating, 13+ non-child-directed target audience and no in-app generative AI features.",
            "Testing Track And Final Review",
            "./tools/create_store_asset_review_sheet.py --write",
            "Closed testing required for this account.",
            "Store listing preview checked for damaging image crops.",
            "Store listing preview evidence must explicitly mention the icon, feature graphic, phone screenshots, tablet screenshots and no damaging crops.",
            "publication_readiness_production_ready_owner_confirmed",
        ],
    )
    handoff = read(handoff_path)
    for forbidden in [
        "storePassword=",
        "keyPassword=",
        "BEGIN PRIVATE KEY",
        "BEGIN RSA PRIVATE KEY",
        "Bearer ",
        "AIza",
        "ya29.",
    ]:
        require(forbidden not in handoff, f"publication readiness owner actions must not record secret marker: {forbidden}")

    helper = require_file("tools/print_publication_readiness.py")
    spec = importlib.util.spec_from_file_location("line56_publication_readiness_for_handoff", helper)
    require(spec is not None and spec.loader is not None, "publication readiness helper could not be loaded for owner-action sync check")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sections: dict[str, str] = {}
    matches = list(re.finditer(r"^## \d+\. (?P<title>.+)$", handoff, re.MULTILINE))
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(handoff)
        sections[normalized_doc_title(match.group("title"))] = handoff[start:end]

    for title, action, evidence_files, commands, labels in module.OWNER_ACTION_GROUPS:
        normalized_title = normalized_doc_title(title)
        require(normalized_title in sections, f"owner-action handoff missing section for publication readiness group: {title}")
        section = sections[normalized_title]
        require(action.lower() in section.lower(), f"owner-action handoff section {title} missing synchronized action text")
        for evidence_file in evidence_files:
            require(evidence_file in section, f"owner-action handoff section {title} missing evidence file: {evidence_file}")
        for command in commands:
            require(command in section, f"owner-action handoff section {title} missing command: {command}")
        for label in labels:
            require(label in section, f"owner-action handoff section {title} missing evidence field label: {label}")


def check_upload_manifest() -> None:
    optional_local_only_paths = {
        "private/signing/line56-upload.p12",
        "build/play_upload/line56_v1_google_play_upload_packet.zip",
    }
    for path in parse_backtick_paths("play_store/upload_manifest.md"):
        if path in optional_local_only_paths and not (ROOT / path).exists():
            continue
        require((ROOT / path).exists(), f"upload manifest path does not exist: {path}")


def check_upload_runbook_handoff() -> None:
    require_text_markers(
        "play_store/upload_runbook_ru.md",
        [
            "Google Play Upload Runbook - RU",
            "Локальный Preflight Перед Загрузкой",
            "./tools/run_final_local_gate.py",
            "Equivalent expanded sequence:",
            "./gradlew test",
            "./gradlew assembleDebug",
            "./gradlew lint",
            "./gradlew bundleRelease",
            "./tools/verify_release.py",
            "./tools/print_upload_packet.py",
            "./tools/create_store_asset_review_sheet.py --dry-run",
            "./tools/print_play_console_packet.py",
            "./tools/print_publication_readiness.py",
            "./tools/check_signing_backup_inputs.py",
            "./tools/run_final_local_gate.py --include-connected --connected-serial <serial>",
            "При доступном API 36 устройстве `./tools/run_final_local_gate.py --include-connected --connected-serial <serial>` тоже возвращает `final_local_gate_ok`",
            "force-stops `com.qgrid.mobile`",
            "удаляет stale local debug/test packages including `com.qgrid.mobile.debug` and `com.qgrid.mobile.debug.test`",
            "./tools/run_api36_connected_gate.py",
            "./tools/run_api36_connected_gate.py --include-hosted-privacy",
            "`./tools/run_api36_connected_gate.py` возвращает `api36_connected_gate_ok`",
            "добавьте `--include-hosted-privacy`, когда сеть доступна",
            "ANDROID_SERIAL=<serial> ./gradlew connectedDebugAndroidTest",
            "`./tools/run_final_local_gate.py` возвращает `final_local_gate_ok`.",
            "`./tools/verify_release.py` возвращает `release_verification_ok`.",
            "`./tools/print_upload_packet.py` возвращает `upload_packet_ok`.",
            "`./tools/create_store_asset_review_sheet.py --dry-run` возвращает `store_asset_review_sheet_dry_run_ok`",
            "visually review `play_store/store_asset_review_sheet.png` before upload",
            "`./tools/prepare_play_upload_archive.py --dry-run` возвращает `play_upload_archive_dry_run_ok`",
            "`./tools/prepare_play_upload_archive.py --verify-existing` возвращает `play_upload_archive_existing_ok`",
            "optional `./tools/prepare_play_upload_archive.py --write` создаёт generated owner handoff ZIP under `build/play_upload`",
            "`./tools/print_play_console_packet.py` возвращает `play_console_packet_ok`.",
            "`./tools/print_publication_readiness.py` возвращает `publication_readiness_local_ready_external_pending`",
            "groups unresolved owner actions by evidence file and required command",
            "сверить действия с `play_store/publication_readiness_owner_actions_ru.md`",
            "`./tools/verify_play_generated_apk.py --dry-run` возвращает `play_generated_apk_verify_dry_run_ok`",
            "`./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` and require `play_generated_apk_verify_ok` plus the `signer certificate SHA-256: ...`, `store icon pixel matches: ...`, `application icon linked store icon: ...`, `round icon linked store icon: ...`, `allowBackup: false` and `debuggable: absent` or `debuggable: false` lines.",
            "`./tools/verify_release.py` проверяет 16 KB page-size posture для native `.so` в signed AAB",
            "--require-production-ready",
            "`./tools/check_privacy_policy_url.py --local` возвращает `privacy_policy_local_ok` and prints the canonical privacy text SHA-256 for owner comparison.",
            "`./tools/check_signing_backup_inputs.py` возвращает `signing_backup_input_ok`.",
            "`./tools/verify_remote_release.py --tag <release-tag>` возвращает `remote_release_ok`",
            "annotated remote release tag",
            "every remote upload asset checksum from `play_store/upload_checksums.md`",
            "отсутствие extra remote `.aab` outside `app/build/outputs/bundle/release/app-release.aab`",
            "case-insensitive отсутствие signing/install artifacts",
            "`app/build/outputs/bundle/release/app-release.aab`",
            "AAB SHA-256 совпадает с `play_store/upload_checksums.md`.",
            "Store icon, feature graphic, phone screenshots and large/tablet screenshots совпадают с `play_store/upload_manifest.md`.",
            "`keystore.properties`, `local.properties`, `private/signing/*.p12`, common signing-key extensions (`*.jks`, `*.keystore`, `*.pem`, `*.pk8`, `*.key`) and APK/AAB/APKS/IDSIG files case-insensitively игнорируются `.gitignore`, проверяются через `git check-ignore` in `tools/verify_release.py`, fail release verification if tracked in Git and не добавляются в публичные материалы.",
            "Owner Inputs До Создания Релиза",
            "Play Console support/contact fields",
            "Public privacy policy URL: HTTPS, без логина, не PDF, без credentials/query/fragments",
            "hosted normalized text must match `play_store/privacy_policy_ru.html`",
            "Signing backup: `private/signing/qgrid-upload.p12` and `keystore.properties`",
            "Safe signing-backup evidence template: `play_store/signing_backup_evidence_ru.md`.",
            "closed testing with 12 opted-in testers for 14 continuous days if required by account type",
            "Источник owner gates: `play_store/owner_release_inputs.md`.",
            "Owner-action breakdown for upload day: `play_store/publication_readiness_owner_actions_ru.md`.",
            "Package name: `com.qgrid.mobile`.",
            "Version code: `1`.",
            "Version name: `1.0.0`.",
            "App content field-by-field answers: `play_store/app_content_answers_ru.md`.",
            "Data Safety: `play_store/data_safety_ru.md`.",
            "Content Rating: `play_store/content_rating_notes.md`.",
            "Privacy policy HTML source: `play_store/privacy_policy_ru.html`.",
            "Before entering the URL in Play Console, run `./tools/check_privacy_policy_url.py --url <https-url>` and require `privacy_policy_url_ok`",
            "no credentials/query/fragments",
            "free of script/tracker/widget markers and text-identical to the current local policy HTML",
            "No `INTERNET` or `ACCESS_NETWORK_STATE` permission in the app.",
            "Non-child-directed target audience recommendation: select `13-15`, `16-17`, and `18 and over`",
            "Copy-ready text source:",
            "`play_store/play_console_submission_ru.md`.",
            "Command packet: run `./tools/print_play_console_packet.py` and require `play_console_packet_ok`.",
            "App bundle: `app/build/outputs/bundle/release/app-release.aab`.",
            "Store icon: `play_store/icon/play_icon_512.png`.",
            "Feature graphic: `play_store/feature_graphic.png`.",
            "`play_store/screenshots/phone/01_onboarding.png`",
            "`play_store/screenshots/phone/05_settings.png`",
            "`play_store/screenshots/tablet/01_onboarding.png`",
            "`play_store/screenshots/tablet/05_settings.png`",
            "Use alt text from `play_store/asset_alt_text_ru.md`",
            "Do Not Upload",
            "`play_store/archive/feature_graphic_concept.png`",
            "`play_store/archive/icon_imagegen_20260605_rejected.png`",
            "`play_store/archive/icon_imagegen_20260606_rejected_owner_review.png`",
            "`play_store/source_assets/feature_background_imagegen.png`",
            "`play_store/source_assets/icon_imagegen_20260606.png`",
            "`play_store/icon/play_icon_preview_masked.png`",
            "`docs/qa_artifacts`",
            "Any APK under `app/build/outputs/apk`.",
            "`app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk`.",
            "`private/signing/qgrid-upload.p12`.",
            "`private/signing/line56-upload.p12`.",
            "The only binary upload artifact for Google Play is the signed AAB.",
            "Release Track Order",
            "Upload the signed AAB to internal testing.",
            "Inspect Play-generated APKs for package, app name, version, APK signature, signer certificate SHA-256, store-icon pixel match, application/round icon linkage, permissions, `allowBackup=false`, no debuggable release manifest and native 16 KB page-size posture.",
            "Run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` on a downloaded Play-generated APK artifact and require `play_generated_apk_verify_ok`.",
            "Promote to production only after owner gates, testing tracks and review warnings are complete.",
            "Stop Conditions",
            "Play Console package is not `com.qgrid.mobile`.",
            "Pre-launch report shows a reproducible app crash.",
            "After any local rebuild, rerun the full preflight and compare `play_store/upload_checksums.md` again before uploading.",
            "Evidence To Record After Upload",
            "Public privacy policy URL.",
            "Signing backup input check result from `./tools/check_signing_backup_inputs.py`.",
            "Signing backup evidence recorded in `play_store/signing_backup_evidence_ru.md`.",
            "Support/contact field used for privacy inquiries.",
            "Use `play_store/play_console_post_upload_evidence_ru.md` as the safe evidence template.",
            "This evidence is external to the repository",
        ],
    )


def check_final_local_gate_runner() -> None:
    helper = require_file("tools/run_final_local_gate.py")
    require(os.access(helper, os.X_OK), "tools/run_final_local_gate.py must be executable")
    require_text_markers(
        "tools/run_final_local_gate.py",
        [
            "Run the final local gate before owner handoff.",
            "This script is intentionally local by default.",
            "--include-hosted-privacy only for a pre-upload run",
            "PUBLICATION_READINESS_COMMAND: tuple[str, ...] = (\"./tools/print_publication_readiness.py\",)",
            "PUBLICATION_READINESS_WITH_RECORDED_PRIVACY_COMMAND: tuple[str, ...] = (",
            "\"--check-recorded-privacy-url\"",
            "(\"./gradlew\", \"test\", \"lint\", \"assembleDebug\", \"assembleRelease\", \"bundleRelease\")",
            "(\"./tools/verify_release.py\",)",
            "(\"./tools/print_upload_packet.py\",)",
            "(\"./tools/create_store_asset_review_sheet.py\", \"--dry-run\")",
            "(\"./tools/prepare_play_upload_archive.py\", \"--dry-run\")",
            "(\"./tools/prepare_play_upload_archive.py\", \"--verify-existing\")",
            "(\"./tools/print_play_console_packet.py\",)",
            "(\"./tools/print_publication_readiness.py\",)",
            "(\"./tools/verify_play_generated_apk.py\", \"--dry-run\")",
            "(\"./tools/check_privacy_policy_url.py\", \"--local\")",
            "(\"./tools/check_signing_backup_inputs.py\",)",
            "--dry-run",
            "--include-connected",
            "--connected-serial",
            "--include-hosted-privacy",
            "CONNECTED_COMMAND: tuple[str, ...] = (\"./gradlew\", \"connectedDebugAndroidTest\")",
            "CONNECTED_OUTPUT_DIRS: tuple[Path, ...] = (",
            "FOCUS_BLOCKING_CONNECTED_PACKAGES: tuple[str, ...] = (",
            "com.qgrid.mobile",
            "STALE_CONNECTED_PACKAGES: tuple[str, ...] = (",
            "com.qgrid.mobile.debug.test",
            "com.qgrid.mobile.debug",
            "com.fiftyfive.seconds",
            "com.fiftyfive.seconds.debug.test",
            "com.andrejivliev.shawarma58.debug.test",
            "com.ivliev.line56.debug.test",
            "app/build/outputs/androidTest-results/connected/debug",
            "app/build/reports/androidTests/connected/debug",
            "def clean_connected_outputs(",
            "shutil.rmtree(directory)",
            "def installed_packages(",
            "\"adb\", \"-s\", serial, \"shell\", \"pm\", \"list\", \"packages\"",
            "def stale_process_ids(",
            "\"adb\", \"-s\", serial, \"shell\", \"pidof\", package_name",
            "def stop_stale_connected_processes(",
            "\"adb\", \"-s\", serial, \"shell\", \"am\", \"force-stop\", package_name",
            "\"adb\", \"-s\", serial, \"shell\", \"kill\", \"-9\", *pids",
            "def clean_stale_connected_packages(",
            "\"adb\", \"-s\", serial, \"uninstall\", package_name",
            "installed_stale_packages",
            "remaining_stale_packages",
            "remaining_stale_processes",
            "Stale connected package uninstall failed",
            "Stale connected packages still installed",
            "Stale connected processes still running",
            "$ clean connected test outputs",
            "$ stop focus-blocking packages and uninstall stale connected debug/test packages on the selected serial",
            "ANDROID_SERIAL",
            "final_local_gate_dry_run_ok",
            "final_local_gate_ok",
        ],
    )
    output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for command in [
        "./gradlew test lint assembleDebug assembleRelease bundleRelease",
        "./tools/verify_release.py",
        "./tools/print_upload_packet.py",
        "./tools/create_store_asset_review_sheet.py --dry-run",
        "./tools/prepare_play_upload_archive.py --dry-run",
        "./tools/prepare_play_upload_archive.py --verify-existing",
        "./tools/print_play_console_packet.py",
        "./tools/print_publication_readiness.py",
        "./tools/verify_play_generated_apk.py --dry-run",
        "./tools/check_privacy_policy_url.py --local",
        "./tools/check_signing_backup_inputs.py",
    ]:
        require(command in output, f"final local gate dry-run missing command: {command}")
    require("final_local_gate_dry_run_ok" in output, "final local gate dry-run did not finish with final_local_gate_dry_run_ok")

    hosted_privacy_output = subprocess.check_output(
        [str(helper), "--dry-run", "--include-hosted-privacy"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require(
        "./tools/print_publication_readiness.py --check-recorded-privacy-url" in hosted_privacy_output,
        "final local gate hosted privacy dry-run missing recorded privacy URL readiness command",
    )
    require(
        "./tools/print_publication_readiness.py\n" not in hosted_privacy_output,
        "final local gate hosted privacy dry-run must replace the plain publication-readiness command",
    )
    require(
        "final_local_gate_dry_run_ok" in hosted_privacy_output,
        "final local gate hosted privacy dry-run did not finish with final_local_gate_dry_run_ok",
    )

    connected_output = subprocess.check_output(
        [str(helper), "--dry-run", "--include-connected", "--connected-serial", "emulator-5560"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require(
        "ANDROID_SERIAL=emulator-5560 ./gradlew connectedDebugAndroidTest" in connected_output,
        "final local gate connected dry-run missing serial-scoped connectedDebugAndroidTest command",
    )
    require(
        "clean connected test outputs" in connected_output,
        "final local gate connected dry-run must clean generated connected outputs before connectedDebugAndroidTest",
    )
    require(
        "stop focus-blocking packages and uninstall stale connected debug/test packages on the selected serial" in connected_output,
        "final local gate connected dry-run must stop focus-blocking packages and uninstall known stale debug/test packages before connectedDebugAndroidTest",
    )
    require("./tools/verify_release.py" in connected_output, "final local gate connected dry-run must still run verifier after connected tests")
    require(
        connected_output.index("clean connected test outputs") <
        connected_output.index("stop focus-blocking packages and uninstall stale connected debug/test packages on the selected serial") <
        connected_output.index("ANDROID_SERIAL=emulator-5560 ./gradlew connectedDebugAndroidTest") <
        connected_output.index("./tools/verify_release.py"),
        "final local gate connected dry-run must clean outputs, uninstall stale packages, then run connectedDebugAndroidTest before verifier",
    )
    require(
        connected_output.index("ANDROID_SERIAL=emulator-5560 ./gradlew connectedDebugAndroidTest") <
        connected_output.index("./tools/verify_release.py"),
        "final local gate connected dry-run must run connectedDebugAndroidTest before verifier",
    )
    require("final_local_gate_dry_run_ok" in connected_output, "final local gate connected dry-run did not finish with final_local_gate_dry_run_ok")


def check_api36_connected_gate_helper() -> None:
    helper = require_file("tools/run_api36_connected_gate.py")
    require(os.access(helper, os.X_OK), "tools/run_api36_connected_gate.py must be executable")
    require_text_markers(
        "tools/run_api36_connected_gate.py",
        [
            "Boot a clean project-owned API 36 AVD and run the connected final local gate.",
            "DEFAULT_AVD = \"Medium_Phone_API_36\"",
            "DEFAULT_SERIAL = \"emulator-5560\"",
            "DEFAULT_PORT = 5560",
            "DEFAULT_BOOT_TIMEOUT_SECONDS = 180",
            "DEFAULT_LOG = Path(\"/tmp/line56_api36_connected_gate.log\")",
            "--keep-emulator",
            "--include-hosted-privacy",
            "--preserve-avd-data",
            "--dry-run",
            "-wipe-data",
            "stale debug/test APKs from older local projects cannot steal focus",
            "retries once without -wipe-data after that clean reset",
            "process_exited_before_boot(",
            "wipe-data boot exited before boot; retrying cleaned AVD without -wipe-data",
            "serial must match --port",
            "refusing to use or stop it",
            "wait_for_boot(",
            "run_final_local_gate.py\", \"--include-connected\", \"--connected-serial\"",
            "command.append(\"--include-hosted-privacy\")",
            "stop only the emulator started by this helper",
            "api36_connected_gate_dry_run_ok",
            "api36_connected_gate_ok",
        ],
    )
    output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "API 36 connected final gate",
        "AVD: Medium_Phone_API_36",
        "Serial: emulator-5560",
        "Port: 5560",
        "Wipe AVD data on managed start: True",
        "- start Medium_Phone_API_36 on emulator-5560 if needed with -wipe-data",
        "- if -wipe-data exits after reset before boot, retry the cleaned AVD once without -wipe-data",
        "- ./tools/run_final_local_gate.py --include-connected --connected-serial emulator-5560",
        "- stop only the emulator started by this helper unless --keep-emulator is set",
        "api36_connected_gate_dry_run_ok",
    ]:
        require(marker in output, f"api36 connected gate dry-run missing marker: {marker}")

    hosted_output = subprocess.check_output(
        [str(helper), "--dry-run", "--include-hosted-privacy"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    hosted_marker = "- ./tools/run_final_local_gate.py --include-connected --connected-serial emulator-5560 --include-hosted-privacy"
    require(hosted_marker in hosted_output, f"api36 connected hosted-privacy dry-run missing marker: {hosted_marker}")
    require("api36_connected_gate_dry_run_ok" in hosted_output, "api36 connected hosted-privacy dry-run did not finish with api36_connected_gate_dry_run_ok")


def check_upload_packet_helper() -> None:
    helper = require_file("tools/print_upload_packet.py")
    require(os.access(helper, os.X_OK), "tools/print_upload_packet.py must be executable")
    require_text_markers(
        "tools/print_upload_packet.py",
        [
            "This helper is intentionally read-only.",
            "CHECKSUMS_PATH = ROOT / \"play_store/upload_checksums.md\"",
            "MANIFEST_PATH = ROOT / \"play_store/upload_manifest.md\"",
            "FORBIDDEN_UPLOAD_MARKERS",
            "\"keystore.properties\"",
            "\"private/signing\"",
            "\"androidTest\"",
            "def require_safe_relative_path(",
            "Unsafe upload checksum path",
            "Duplicate upload checksum row",
            "def parse_byte_count(",
            "Bad upload checksum byte count",
            "def require_sha256(",
            "Bad upload checksum SHA-256",
            "SCREENSHOT_NAMES = (",
            "REQUIRED_UPLOAD_PATHS = (",
            "def parse_checksum_rows(",
            "def do_not_upload_entries()",
            "def verify_required_upload_paths(",
            "missing required upload paths",
            "contains unexpected upload paths",
            "path order must match the Play upload packet order",
            "def verify_rows(",
            "raise UploadPacketError(f\"Forbidden file appears in upload checksums",
            "if relative_path not in manifest:",
            "Size mismatch",
            "SHA-256 mismatch",
            "Google Play upload packet",
            "Do not upload",
            "upload_packet_ok",
        ],
    )
    output = subprocess.check_output(
        [str(helper)],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require("Google Play upload packet" in output, "upload packet helper did not print upload packet header")
    require("app/build/outputs/bundle/release/app-release.aab" in output, "upload packet helper did not print AAB path")
    require("play_store/icon/play_icon_512.png" in output, "upload packet helper did not print Play icon path")
    require("play_store/feature_graphic.png" in output, "upload packet helper did not print feature graphic path")
    require("Do not upload" in output, "upload packet helper did not print Do Not Upload section")
    require("keystore.properties" in output, "upload packet helper did not print signing secret in Do Not Upload section")
    require("upload_packet_ok" in output, "upload packet helper did not finish with upload_packet_ok")

    spec = importlib.util.spec_from_file_location("line56_upload_packet", helper)
    require(spec is not None and spec.loader is not None, "upload packet helper could not be loaded for regression checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.parse_checksum_rows()
    require(rows, "upload packet helper returned no checksum rows")
    module.verify_required_upload_paths(rows)
    module.verify_rows(rows)
    module.do_not_upload_entries()

    for bad_rows, expected_message in [
        (rows[:-1], "missing required upload paths"),
        (rows + [("play_store/screenshots/phone/extra.png", 1, "0" * 64)], "contains unexpected upload paths"),
        ([rows[1], rows[0], *rows[2:]], "path order must match the Play upload packet order"),
    ]:
        try:
            module.verify_required_upload_paths(bad_rows)
        except module.UploadPacketError as exc:
            require(expected_message in str(exc), f"upload packet helper rejected bad upload path set with unexpected message: {exc}")
        else:
            raise CheckFailure(f"upload packet helper must reject bad upload path set: {expected_message}")

    temporary_checksums = ROOT / "build/verification/upload_packet_checksums.md"
    temporary_checksums.parent.mkdir(parents=True, exist_ok=True)
    try:
        duplicate_path = rows[0][0]
        duplicate_size = rows[0][1]
        duplicate_sha = rows[0][2]
        temporary_checksums.write_text(
            "\n".join(
                [
                    "| Path | Bytes | SHA-256 |",
                    "|---|---:|---|",
                    f"| `{duplicate_path}` | {duplicate_size} | `{duplicate_sha}` |",
                    f"| `{duplicate_path}` | {duplicate_size} | `{duplicate_sha}` |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        try:
            module.parse_checksum_rows(temporary_checksums)
        except module.UploadPacketError as exc:
            require("Duplicate upload checksum row" in str(exc), f"upload packet helper rejected duplicate checksum row with unexpected message: {exc}")
        else:
            raise CheckFailure("upload packet helper must reject duplicate checksum rows")

        for bad_path in ["../outside.aab", "play_store\\icon\\play_icon_512.png"]:
            temporary_checksums.write_text(
                "\n".join(
                    [
                        "| Path | Bytes | SHA-256 |",
                        "|---|---:|---|",
                        f"| `{bad_path}` | 1 | `{'0' * 64}` |",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            try:
                module.parse_checksum_rows(temporary_checksums)
            except module.UploadPacketError as exc:
                require("Unsafe upload checksum path" in str(exc), f"upload packet helper rejected unsafe checksum path with unexpected message: {exc}")
            else:
                raise CheckFailure(f"upload packet helper must reject unsafe checksum path: {bad_path}")

        for byte_count_text, checksum_text, expected_message in [
            ("not-a-number", "0" * 64, "Bad upload checksum byte count"),
            ("-1", "0" * 64, "Bad upload checksum byte count"),
            ("1", "0" * 63, "Bad upload checksum SHA-256"),
            ("1", "A" * 64, "Bad upload checksum SHA-256"),
        ]:
            temporary_checksums.write_text(
                "\n".join(
                    [
                        "| Path | Bytes | SHA-256 |",
                        "|---|---:|---|",
                        f"| `{duplicate_path}` | {byte_count_text} | `{checksum_text}` |",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            try:
                module.parse_checksum_rows(temporary_checksums)
            except module.UploadPacketError as exc:
                require(expected_message in str(exc), f"upload packet helper rejected malformed checksum row with unexpected message: {exc}")
            else:
                raise CheckFailure(f"upload packet helper must reject malformed checksum row: {expected_message}")
    finally:
        if temporary_checksums.exists():
            temporary_checksums.unlink()

    first_path, first_size, first_sha = rows[0]
    for bad_rows, expected_message in [
        ([("keystore.properties", 1, "0" * 64)], "Forbidden file appears in upload checksums"),
        ([(first_path, first_size + 1, first_sha)], "Size mismatch"),
        ([(first_path, first_size, "0" * 64)], "SHA-256 mismatch"),
        ([("play_store/not_in_manifest.png", 1, "0" * 64)], "Upload checksum path missing from upload_manifest.md"),
    ]:
        try:
            module.verify_rows(bad_rows)
        except module.UploadPacketError as exc:
            require(expected_message in str(exc), f"upload packet helper rejected bad rows with unexpected message: {exc}")
        else:
            raise CheckFailure(f"upload packet helper must reject bad upload rows: {bad_rows}")

    original_manifest_path = module.MANIFEST_PATH
    module.MANIFEST_PATH = ROOT / "tools/print_upload_packet.py"
    try:
        try:
            module.do_not_upload_entries()
        except module.UploadPacketError as exc:
            require("Do Not Upload section is missing" in str(exc), f"upload packet helper rejected missing Do Not Upload with unexpected message: {exc}")
        else:
            raise CheckFailure("upload packet helper must reject a manifest without Do Not Upload entries")
    finally:
        module.MANIFEST_PATH = original_manifest_path


def check_store_asset_review_sheet_helper() -> None:
    helper = require_file("tools/create_store_asset_review_sheet.py")
    require(os.access(helper, os.X_OK), "tools/create_store_asset_review_sheet.py must be executable")
    require_text_markers(
        "tools/create_store_asset_review_sheet.py",
        [
            "Create a local Google Play store-asset review sheet.",
            "The generated PNG is an internal owner-review artifact and must not be uploaded to Play Console.",
            "must not be uploaded to Play Console",
            "DEFAULT_OUTPUT = ROOT / \"play_store/store_asset_review_sheet.png\"",
            "CANVAS_SIZE = (1800, 2050)",
            "EXPECTED_IMAGES: tuple[tuple[str, tuple[int, int]], ...] = (",
            "play_store/icon/play_icon_512.png",
            "play_store/feature_graphic.png",
            "play_store/screenshots/phone/01_onboarding.png",
            "play_store/screenshots/tablet/05_settings.png",
            "def validate_images(",
            "images: tuple[tuple[str, tuple[int, int]], ...] = EXPECTED_IMAGES",
            "if image.format != \"PNG\":",
            "def build_sheet(",
            "--dry-run",
            "--write",
            "Review focus: no damaging crop",
            "store_asset_review_sheet_dry_run_ok",
            "store_asset_review_sheet_ok",
        ],
    )

    dry_output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Store asset review sheet dry run",
        "planned output: play_store/store_asset_review_sheet.png",
        "planned size: 1800x2050",
        "play_store/icon/play_icon_512.png (512x512)",
        "play_store/feature_graphic.png (1024x500)",
        "play_store/screenshots/phone/01_onboarding.png (1080x2064)",
        "play_store/screenshots/tablet/05_settings.png (1600x2336)",
        "store_asset_review_sheet_dry_run_ok",
    ]:
        require(marker in dry_output, f"store asset review dry-run missing marker: {marker}")

    sheet_path = "play_store/store_asset_review_sheet.png"
    check_png(sheet_path, 1800, 2050, alpha=False, max_bytes=2 * 1024 * 1024)
    source_paths = [
        "tools/create_store_asset_review_sheet.py",
        "play_store/icon/play_icon_512.png",
        "play_store/feature_graphic.png",
        "play_store/screenshots/phone",
        "play_store/screenshots/tablet",
    ]
    require(
        (ROOT / sheet_path).stat().st_mtime >= latest_file_mtime(source_paths),
        "store asset review sheet must be regenerated after icon, feature graphic, screenshots or helper changes",
    )

    output_path = ROOT / "build/verification/store_asset_review_sheet_test.png"
    if output_path.exists():
        output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_output = subprocess.check_output(
            [str(helper), "--write", "--output", str(output_path)],
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require("store_asset_review_sheet_ok" in write_output, "store asset review write helper did not finish with store_asset_review_sheet_ok")
        require(output_path.is_file(), "store asset review helper did not create the requested PNG")
        actual_width, actual_height, bit_depth, color_type = png_info(str(output_path.relative_to(ROOT)))
        require((actual_width, actual_height) == (1800, 2050), "temporary store asset review sheet must be 1800x2050")
        require(bit_depth == 8 and color_type == 2, "temporary store asset review sheet must be 8-bit RGB PNG without alpha")
    finally:
        if output_path.exists():
            output_path.unlink()

    spec = importlib.util.spec_from_file_location("line56_store_asset_review_sheet", helper)
    require(spec is not None and spec.loader is not None, "cannot import store asset review sheet helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    try:
        module.validate_images((("play_store/icon/missing_icon.png", (512, 512)),))
    except module.ReviewSheetError as exc:
        require("Missing store asset" in str(exc), f"store asset helper rejected missing asset with unexpected message: {exc}")
    else:
        raise CheckFailure("store asset helper must reject missing assets")

    try:
        module.validate_images((("play_store/icon/play_icon_512.png", (511, 512)),))
    except module.ReviewSheetError as exc:
        require("expected (511, 512), got (512, 512)" in str(exc), f"store asset helper rejected wrong dimensions with unexpected message: {exc}")
    else:
        raise CheckFailure("store asset helper must reject wrong asset dimensions")

    bad_mode_path = ROOT / "build/verification/store_asset_review_bad_mode.png"
    bad_format_path = ROOT / "build/verification/store_asset_review_bad_format.jpg"
    try:
        module.Image.new("L", (8, 8), 128).save(bad_mode_path, format="PNG")
        module.Image.new("RGB", (8, 8), "#ffffff").save(bad_format_path, format="JPEG")
        module.validate_images(((str(bad_mode_path.relative_to(ROOT)), (8, 8)),))
    except module.ReviewSheetError as exc:
        require("expected RGB/RGBA PNG, got L" in str(exc), f"store asset helper rejected grayscale PNG with unexpected message: {exc}")
    else:
        raise CheckFailure("store asset helper must reject grayscale PNG assets")

    try:
        module.validate_images(((str(bad_format_path.relative_to(ROOT)), (8, 8)),))
    except module.ReviewSheetError as exc:
        require("expected PNG, got JPEG" in str(exc), f"store asset helper rejected non-PNG asset with unexpected message: {exc}")
    else:
        raise CheckFailure("store asset helper must reject non-PNG store assets")
    finally:
        for temporary_path in [bad_mode_path, bad_format_path]:
            if temporary_path.exists():
                temporary_path.unlink()


def check_play_upload_archive_helper() -> None:
    helper = require_file("tools/prepare_play_upload_archive.py")
    require(os.access(helper, os.X_OK), "tools/prepare_play_upload_archive.py must be executable")
    require_text_markers(
        "tools/prepare_play_upload_archive.py",
        [
            "Prepare a safe owner handoff archive for the Google Play upload packet.",
            "The archive is generated under build/ and is not a Play upload artifact itself.",
            "CHECKSUMS_PATH = ROOT / \"play_store/upload_checksums.md\"",
            "MANIFEST_PATH = ROOT / \"play_store/upload_manifest.md\"",
            "DEFAULT_OUTPUT = ROOT / \"build/play_upload/line56_v1_google_play_upload_packet.zip\"",
            "FORBIDDEN_SOURCE_PATH_MARKERS",
            "FORBIDDEN_ARCHIVE_NAME_MARKERS",
            "\"keystore.properties\"",
            "\"private/signing\"",
            "\"androidTest\"",
            "SCREENSHOT_NAMES = (",
            "REQUIRED_UPLOAD_PATHS = (",
            "HANDOFF_FILES = (",
            "play_store/upload_runbook_ru.md",
            "play_store/publication_readiness_owner_actions_ru.md",
            "play_store/privacy_policy_ru.html",
            "play_store/signing_backup_evidence_ru.md",
            "play_store/signing_certificate_report.md",
            "def project_path(",
            "Unsafe {label} path",
            "def parse_byte_count(",
            "Bad upload checksum byte count",
            "def require_sha256(",
            "Bad upload checksum SHA-256",
            "def parse_checksum_rows(",
            "Duplicate upload checksum row",
            "def validate_upload_rows(",
            "def verify_required_upload_paths(",
            "missing required archive paths",
            "contains unexpected archive paths",
            "path order must match the Play upload archive order",
            "def validate_handoff_files(",
            "def planned_archive_entries(",
            "Duplicate archive entry",
            "Forbidden archive entry path",
            "def write_archive(",
            "def verify_existing_archive(",
            "Generated Play upload archive entry is stale",
            "Generated Play upload archive README is stale",
            "_owner_handoff/publication_readiness_owner_actions_ru.md groups external owner actions and evidence fields",
            "--dry-run",
            "--verify-existing",
            "--write",
            "Do not upload this ZIP as a whole",
            "play_upload_archive_dry_run_ok",
            "play_upload_archive_existing_ok",
            "play_upload_archive_ok",
        ],
    )

    dry_output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Google Play upload archive dry run",
        "planned archive: build/play_upload/line56_v1_google_play_upload_packet.zip",
        "line56_v1_google_play_upload_packet/01_app_bundle/app-release.aab",
        "line56_v1_google_play_upload_packet/02_store_icon/play_icon_512.png",
        "line56_v1_google_play_upload_packet/03_feature_graphic/feature_graphic.png",
        "line56_v1_google_play_upload_packet/04_phone_screenshots/01_onboarding.png",
        "line56_v1_google_play_upload_packet/05_large_tablet_screenshots/01_onboarding.png",
        "line56_v1_google_play_upload_packet/_owner_handoff/upload_manifest.md",
        "line56_v1_google_play_upload_packet/_owner_handoff/publication_readiness_owner_actions_ru.md",
        "line56_v1_google_play_upload_packet/_owner_handoff/privacy_policy_ru.html",
        "line56_v1_google_play_upload_packet/_owner_handoff/signing_backup_evidence_ru.md",
        "line56_v1_google_play_upload_packet/_owner_handoff/signing_certificate_report.md",
        "play_upload_archive_dry_run_ok",
    ]:
        require(marker in dry_output, f"upload archive dry-run missing marker: {marker}")

    archive_path = ROOT / "build/verification/play_upload_archive_test.zip"
    if archive_path.exists():
        archive_path.unlink()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_output = subprocess.check_output(
            [str(helper), "--write", "--output", str(archive_path)],
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require("play_upload_archive_ok" in write_output, "upload archive write helper did not finish with play_upload_archive_ok")
        require(archive_path.is_file(), "upload archive helper did not create the requested ZIP")
        existing_output = subprocess.check_output(
            [str(helper), "--verify-existing", "--output", str(archive_path)],
            cwd=ROOT,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require("Google Play upload archive existing verification" in existing_output, "upload archive existing verification missing heading")
        require("play_upload_archive_existing_ok" in existing_output, "upload archive existing verification did not finish with play_upload_archive_existing_ok")
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            for name in [
                "line56_v1_google_play_upload_packet/README_UPLOAD_PACKET.txt",
                "line56_v1_google_play_upload_packet/01_app_bundle/app-release.aab",
                "line56_v1_google_play_upload_packet/02_store_icon/play_icon_512.png",
                "line56_v1_google_play_upload_packet/03_feature_graphic/feature_graphic.png",
                "line56_v1_google_play_upload_packet/04_phone_screenshots/01_onboarding.png",
                "line56_v1_google_play_upload_packet/04_phone_screenshots/05_settings.png",
                "line56_v1_google_play_upload_packet/05_large_tablet_screenshots/01_onboarding.png",
                "line56_v1_google_play_upload_packet/05_large_tablet_screenshots/05_settings.png",
                "line56_v1_google_play_upload_packet/_owner_handoff/upload_checksums.md",
                "line56_v1_google_play_upload_packet/_owner_handoff/play_console_submission_ru.md",
                "line56_v1_google_play_upload_packet/_owner_handoff/publication_readiness_owner_actions_ru.md",
                "line56_v1_google_play_upload_packet/_owner_handoff/signing_backup_evidence_ru.md",
                "line56_v1_google_play_upload_packet/_owner_handoff/signing_certificate_report.md",
                "line56_v1_google_play_upload_packet/_owner_handoff/privacy_policy_ru.html",
            ]:
                require(name in names, f"upload archive missing expected entry: {name}")
            forbidden_name_markers = [
                "keystore.properties",
                "local.properties",
                "private/signing",
                "app-debug.apk",
                "androidTest",
                ".apks",
                ".idsig",
                "source_assets",
                "archive/icon_imagegen_20260605_rejected",
                "archive/icon_imagegen_20260606_rejected_owner_review",
            ]
            for name in names:
                for marker in forbidden_name_markers:
                    require(marker not in name, f"upload archive contains forbidden entry marker {marker}: {name}")
            readme = archive.read("line56_v1_google_play_upload_packet/README_UPLOAD_PACKET.txt").decode("utf-8")
            require("not a Play Console upload artifact" in readme, "upload archive README must warn that ZIP is not a Play upload artifact")
            require("publication_readiness_owner_actions_ru.md groups external owner actions" in readme, "upload archive README must mention owner-action handoff")
            require("Do not upload this ZIP as a whole" in readme, "upload archive README must warn not to upload the ZIP itself")
    finally:
        if archive_path.exists():
            archive_path.unlink()

    spec = importlib.util.spec_from_file_location("line56_play_upload_archive", helper)
    require(spec is not None and spec.loader is not None, "cannot import Play upload archive helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.parse_checksum_rows()
    module.verify_required_upload_paths(rows)

    archive_checksums = ROOT / "build/verification/archive_upload_checksums.md"
    archive_checksums.parent.mkdir(parents=True, exist_ok=True)
    first_path, first_size, first_sha = rows[0]
    try:
        archive_checksums.write_text(
            "\n".join(
                [
                    "| Path | Bytes | SHA-256 |",
                    "|---|---:|---|",
                    f"| `{first_path}` | {first_size} | `{first_sha}` |",
                    f"| `{first_path}` | {first_size} | `{first_sha}` |",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        try:
            module.parse_checksum_rows(archive_checksums)
        except module.ArchiveError as exc:
            require("Duplicate upload checksum row" in str(exc), f"archive helper rejected duplicate checksum row with unexpected message: {exc}")
        else:
            raise CheckFailure("Play upload archive helper must reject duplicate upload checksum rows")

        for byte_count_text, checksum_text, expected_message in [
            ("not-a-number", "0" * 64, "Bad upload checksum byte count"),
            ("-1", "0" * 64, "Bad upload checksum byte count"),
            ("1", "0" * 63, "Bad upload checksum SHA-256"),
            ("1", "A" * 64, "Bad upload checksum SHA-256"),
        ]:
            archive_checksums.write_text(
                "\n".join(
                    [
                        "| Path | Bytes | SHA-256 |",
                        "|---|---:|---|",
                        f"| `{first_path}` | {byte_count_text} | `{checksum_text}` |",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            try:
                module.parse_checksum_rows(archive_checksums)
            except module.ArchiveError as exc:
                require(expected_message in str(exc), f"archive helper rejected malformed checksum row with unexpected message: {exc}")
            else:
                raise CheckFailure(f"Play upload archive helper must reject malformed checksum row: {expected_message}")
    finally:
        if archive_checksums.exists():
            archive_checksums.unlink()

    for bad_rows, expected_message in [
        (rows[:-1], "missing required archive paths"),
        (rows + [("play_store/screenshots/tablet/extra.png", 1, "0" * 64)], "contains unexpected archive paths"),
        ([rows[1], rows[0], *rows[2:]], "path order must match the Play upload archive order"),
    ]:
        try:
            module.verify_required_upload_paths(bad_rows)
        except module.ArchiveError as exc:
            require(expected_message in str(exc), f"archive helper rejected bad required path set with unexpected message: {exc}")
        else:
            raise CheckFailure(f"Play upload archive helper must reject bad required upload path sets: {expected_message}")

    try:
        module.validate_upload_rows((("../outside.aab", 1, "0" * 64),))
    except module.ArchiveError as exc:
        require("Unsafe upload source path" in str(exc), f"archive helper rejected unsafe upload path with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject unsafe upload source paths")

    try:
        module.validate_upload_rows((("keystore.properties", 1, "0" * 64),))
    except module.ArchiveError as exc:
        require("Forbidden upload source path" in str(exc), f"archive helper rejected forbidden upload path with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject forbidden upload source paths")

    icon_relative_path = "play_store/icon/play_icon_512.png"
    icon_path = ROOT / icon_relative_path
    icon_size = icon_path.stat().st_size
    icon_sha = hashlib.sha256(icon_path.read_bytes()).hexdigest()
    missing_manifest_path = ROOT / "build/verification/archive_missing_manifest.md"
    manifest_path = ROOT / "build/verification/archive_upload_manifest.md"
    try:
        missing_manifest_path.write_text("# Missing current upload path\n", encoding="utf-8")
        module.validate_upload_rows(((icon_relative_path, icon_size, icon_sha),), manifest_path=missing_manifest_path)
    except module.ArchiveError as exc:
        require("Upload source path missing from upload_manifest.md" in str(exc), f"archive helper rejected missing manifest row with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject upload rows absent from upload_manifest.md")

    try:
        manifest_path.write_text(icon_relative_path, encoding="utf-8")
        module.validate_upload_rows(((icon_relative_path, icon_size + 1, icon_sha),), manifest_path=manifest_path)
    except module.ArchiveError as exc:
        require("Size mismatch" in str(exc), f"archive helper rejected wrong upload size with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject wrong upload byte counts")

    try:
        module.validate_upload_rows(((icon_relative_path, icon_size, "0" * 64),), manifest_path=manifest_path)
    except module.ArchiveError as exc:
        require("SHA-256 mismatch" in str(exc), f"archive helper rejected wrong upload checksum with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject wrong upload checksums")
    finally:
        for temporary_path in [missing_manifest_path, manifest_path]:
            if temporary_path.exists():
                temporary_path.unlink()

    try:
        module.validate_handoff_files(("../keystore.properties",))
    except module.ArchiveError as exc:
        require("Unsafe handoff path" in str(exc), f"archive helper rejected unsafe handoff path with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject unsafe handoff paths")

    try:
        module.validate_handoff_files(("play_store/missing_handoff.md",))
    except module.ArchiveError as exc:
        require("Handoff file is missing" in str(exc), f"archive helper rejected missing handoff with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject missing handoff files")

    try:
        module.planned_archive_entries(
            [("play_store/icon/play_icon_512.png", icon_size, icon_sha)],
            ("play_store/upload_manifest.md", "docs/upload_manifest.md"),
        )
    except module.ArchiveError as exc:
        require("Duplicate archive entry" in str(exc), f"archive helper rejected duplicate archive entry with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject duplicate archive entries")

    try:
        module.planned_archive_entries(
            [],
            ("play_store/store_asset_review_sheet.png",),
        )
    except module.ArchiveError as exc:
        require("Forbidden archive entry path" in str(exc), f"archive helper rejected forbidden archive entry with unexpected message: {exc}")
    else:
        raise CheckFailure("Play upload archive helper must reject forbidden archive entry names")

    default_archive_path = ROOT / "build/play_upload/line56_v1_google_play_upload_packet.zip"
    if default_archive_path.exists():
        checksum_rows: dict[str, tuple[int, str]] = {}
        for line in read("play_store/upload_checksums.md").splitlines():
            if not line.startswith("| `"):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            require(len(parts) == 3, f"bad upload checksum row while checking generated archive: {line}")
            relative_path = parts[0].strip("`")
            byte_count = int(parts[1])
            checksum_rows[relative_path] = (byte_count, parts[2].strip("`"))

        def archive_upload_entry(relative_path: str) -> str:
            name = Path(relative_path).name
            if relative_path.endswith(".aab"):
                return f"line56_v1_google_play_upload_packet/01_app_bundle/{name}"
            if relative_path == "play_store/icon/play_icon_512.png":
                return f"line56_v1_google_play_upload_packet/02_store_icon/{name}"
            if relative_path == "play_store/feature_graphic.png":
                return f"line56_v1_google_play_upload_packet/03_feature_graphic/{name}"
            if "/screenshots/phone/" in relative_path:
                return f"line56_v1_google_play_upload_packet/04_phone_screenshots/{name}"
            if "/screenshots/tablet/" in relative_path:
                return f"line56_v1_google_play_upload_packet/05_large_tablet_screenshots/{name}"
            raise CheckFailure(f"unexpected generated archive upload path: {relative_path}")

        handoff_files = [
            "play_store/upload_manifest.md",
            "play_store/upload_checksums.md",
            "play_store/upload_runbook_ru.md",
            "play_store/play_console_submission_ru.md",
            "play_store/app_content_answers_ru.md",
            "play_store/data_safety_ru.md",
            "play_store/content_rating_notes.md",
            "play_store/owner_release_inputs.md",
            "play_store/publication_readiness_owner_actions_ru.md",
            "play_store/play_console_post_upload_evidence_ru.md",
            "play_store/signing_backup_evidence_ru.md",
            "play_store/signing_certificate_report.md",
            "play_store/privacy_policy_ru.md",
            "play_store/privacy_policy_ru.html",
            "play_store/privacy_policy_hosting_checklist.md",
            "play_store/asset_alt_text_ru.md",
        ]
        expected_names = {"line56_v1_google_play_upload_packet/README_UPLOAD_PACKET.txt"}
        expected_names.update(archive_upload_entry(path) for path in checksum_rows)
        expected_names.update(f"line56_v1_google_play_upload_packet/_owner_handoff/{Path(path).name}" for path in handoff_files)

        require(
            default_archive_path.stat().st_mtime >= latest_file_mtime(["tools/prepare_play_upload_archive.py", *checksum_rows.keys(), *handoff_files]),
            "generated Play upload archive must be regenerated after upload assets, handoff files or archive helper changes",
        )
        require(default_archive_path.stat().st_size < 10 * 1024 * 1024, "generated Play upload archive is unexpectedly large")
        with zipfile.ZipFile(default_archive_path) as archive:
            names = set(archive.namelist())
            require(names == expected_names, f"generated Play upload archive entry mismatch: {sorted(names ^ expected_names)}")
            forbidden_name_markers = [
                "keystore.properties",
                "local.properties",
                "private/signing",
                "app-debug.apk",
                "androidTest",
                ".apks",
                ".idsig",
                "source_assets",
                "archive/icon_imagegen_20260605_rejected",
                "archive/icon_imagegen_20260606_rejected_owner_review",
                "store_asset_review_sheet",
            ]
            for name in names:
                for marker in forbidden_name_markers:
                    require(marker not in name, f"generated Play upload archive contains forbidden entry marker {marker}: {name}")

            for relative_path, (expected_size, expected_sha) in checksum_rows.items():
                entry = archive_upload_entry(relative_path)
                data = archive.read(entry)
                require(len(data) == expected_size, f"generated archive entry byte mismatch for {entry}")
                require(hashlib.sha256(data).hexdigest() == expected_sha, f"generated archive entry checksum mismatch for {entry}")
                require(data == (ROOT / relative_path).read_bytes(), f"generated archive entry is stale: {entry}")

            for relative_path in handoff_files:
                entry = f"line56_v1_google_play_upload_packet/_owner_handoff/{Path(relative_path).name}"
                require(archive.read(entry) == (ROOT / relative_path).read_bytes(), f"generated archive handoff file is stale: {entry}")

            readme = archive.read("line56_v1_google_play_upload_packet/README_UPLOAD_PACKET.txt").decode("utf-8")
            require("Line 56 Google Play upload packet" in readme, "generated archive README missing title")
            require("not a Play Console upload artifact" in readme, "generated archive README must warn that ZIP is not a Play upload artifact")
            require("publication_readiness_owner_actions_ru.md groups external owner actions" in readme, "generated archive README must mention owner-action handoff")
            require("Do not upload this ZIP as a whole" in readme, "generated archive README must warn not to upload the ZIP itself")


def check_play_console_packet_helper() -> None:
    helper = require_file("tools/print_play_console_packet.py")
    require(os.access(helper, os.X_OK), "tools/print_play_console_packet.py must be executable")
    require_text_markers(
        "tools/print_play_console_packet.py",
        [
            "Print and verify the Play Console form packet for the owner.",
            "This helper is intentionally read-only.",
            "LISTING_PATH = ROOT / \"play_store/listing_ru.md\"",
            "SUBMISSION_PATH = ROOT / \"play_store/play_console_submission_ru.md\"",
            "APP_CONTENT_PATH = ROOT / \"play_store/app_content_answers_ru.md\"",
            "DATA_SAFETY_PATH = ROOT / \"play_store/data_safety_ru.md\"",
            "CONTENT_RATING_PATH = ROOT / \"play_store/content_rating_notes.md\"",
            "OWNER_INPUTS_PATH = ROOT / \"play_store/owner_release_inputs.md\"",
            "PRIVACY_CHECKLIST_PATH = ROOT / \"play_store/privacy_policy_hosting_checklist.md\"",
            "SIGNING_BACKUP_EVIDENCE_PATH = ROOT / \"play_store/signing_backup_evidence_ru.md\"",
            "POST_UPLOAD_EVIDENCE_PATH = ROOT / \"play_store/play_console_post_upload_evidence_ru.md\"",
            "FORBIDDEN_LISTING_MARKERS = (",
            "contains forbidden placeholder marker",
            "def verify_listing(",
            "app name exceeds Play Console 30-character limit",
            "short description exceeds Play Console 80-character limit",
            "full description exceeds Play Console 4000-character limit",
            "release notes exceed Play Console 500-character limit",
            "def verify_policy_handoff()",
            "Google Play Console packet",
            "App content posture",
            "Manual owner gates",
            "play_console_packet_ok",
        ],
    )
    output = subprocess.check_output(
        [str(helper)],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require("Google Play Console packet" in output, "Play Console helper did not print packet header")
    require("Package name: com.qgrid.mobile" in output, "Play Console helper did not print package")
    require("App name: Линия 56" in output, "Play Console helper did not print app name")
    require("Short description: Соединяйте числа и соберите сумму ровно 56." in output, "Play Console helper did not print short description")
    require("App content posture" in output, "Play Console helper did not print App content posture")
    require("Data Safety: no user data collected or shared." in output, "Play Console helper did not print data safety posture")
    require("Manual owner gates" in output, "Play Console helper did not print manual owner gates")
    require("./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html" in output, "Play Console helper did not print hosted privacy URL check")
    require("play_store/signing_backup_evidence_ru.md" in output, "Play Console helper did not print signing backup evidence path")
    require("play_console_packet_ok" in output, "Play Console helper did not finish with play_console_packet_ok")

    spec = importlib.util.spec_from_file_location("line56_play_console_packet", helper)
    require(spec is not None and spec.loader is not None, "Play Console packet helper could not be loaded for regression checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    listing = read("play_store/listing_ru.md")
    submission = read("play_store/play_console_submission_ru.md")
    module.verify_listing(listing, submission)

    def replace_listing_section(source: str, heading: str, replacement: str) -> str:
        marker = f"## {heading}"
        start = source.index(marker)
        content_start = source.index("\n", start) + 1
        next_match = re.search(r"^##\s+", source[content_start:], re.M)
        content_end = content_start + next_match.start() if next_match else len(source)
        return source[:content_start] + "\n" + replacement + "\n\n" + source[content_end:].lstrip("\n")

    too_long_name_listing = listing.replace("\nЛиния 56\n\n## Short Description", f"\n{'A' * 31}\n\n## Short Description", 1)
    try:
        module.verify_listing(too_long_name_listing, submission)
    except module.PlayConsolePacketError as exc:
        require("app name exceeds Play Console 30-character limit" in str(exc), f"Play Console helper rejected long app name with unexpected message: {exc}")
    else:
        raise CheckFailure("Play Console helper must reject app name over the Play Console length limit")

    too_long_short_listing = listing.replace("Соединяйте числа и соберите сумму ровно 56.", "B" * 81, 1)
    try:
        module.verify_listing(too_long_short_listing, submission)
    except module.PlayConsolePacketError as exc:
        require("short description exceeds Play Console 80-character limit" in str(exc), f"Play Console helper rejected long short description with unexpected message: {exc}")
    else:
        raise CheckFailure("Play Console helper must reject short description over the Play Console length limit")

    too_long_full_listing = replace_listing_section(listing, "Full Description", "C" * 4001)
    try:
        module.verify_listing(too_long_full_listing, submission)
    except module.PlayConsolePacketError as exc:
        require("full description exceeds Play Console 4000-character limit" in str(exc), f"Play Console helper rejected long full description with unexpected message: {exc}")
    else:
        raise CheckFailure("Play Console helper must reject full description over the Play Console length limit")

    too_long_notes_listing = replace_listing_section(listing, "Release Notes", "D" * 501)
    try:
        module.verify_listing(too_long_notes_listing, submission)
    except module.PlayConsolePacketError as exc:
        require("release notes exceed Play Console 500-character limit" in str(exc), f"Play Console helper rejected long release notes with unexpected message: {exc}")
    else:
        raise CheckFailure("Play Console helper must reject release notes over the Play Console length limit")

    placeholder_listing = listing.replace("Линия 56", "Линия 56 TODO", 1)
    try:
        module.verify_listing(placeholder_listing, submission)
    except module.PlayConsolePacketError as exc:
        require("contains forbidden placeholder marker" in str(exc), f"Play Console helper rejected placeholder listing with unexpected message: {exc}")
    else:
        raise CheckFailure("Play Console helper must reject placeholder markers in listing copy")

    unsynced_submission = submission.replace("Соединяйте числа и соберите сумму ровно 56.", "", 1)
    try:
        module.verify_listing(listing, unsynced_submission)
    except module.PlayConsolePacketError as exc:
        require("short description is not synced into play_console_submission_ru.md" in str(exc), f"Play Console helper rejected unsynced listing with unexpected message: {exc}")
    else:
        raise CheckFailure("Play Console helper must reject listing/submission handoff mismatch")


def check_play_generated_apk_helper() -> None:
    helper = require_file("tools/verify_play_generated_apk.py")
    require(os.access(helper, os.X_OK), "tools/verify_play_generated_apk.py must be executable")
    require_text_markers(
        "tools/verify_play_generated_apk.py",
        [
            "Verify a Play-generated APK or local release APK against the release identity.",
            "signature,",
            "manifest-privacy regressions before rollout",
            "page-size ELF and APK packaging alignment",
            "EXPECTED_PACKAGE = \"com.qgrid.mobile\"",
            "EXPECTED_VERSION_CODE = \"1\"",
            "EXPECTED_VERSION_NAME = \"1.0.0\"",
            "EXPECTED_LABEL = \"Линия 56\"",
            "EXPECTED_MIN_SDK = \"24\"",
            "EXPECTED_TARGET_SDK = \"36\"",
            "EXPECTED_STORE_ICON = ROOT / \"play_store/icon/play_icon_512.png\"",
            "REQUIRED_NATIVE_LOAD_ALIGNMENT = 16 * 1024",
            "FORBIDDEN_PERMISSIONS = {",
            "\"android.permission.INTERNET\"",
            "\"android.permission.ACCESS_NETWORK_STATE\"",
            "\"android.permission.POST_NOTIFICATIONS\"",
            "FORBIDDEN_ZIP_MARKERS = (",
            "\"androidtest\"",
            "\"espresso\"",
            "\"junit\"",
            "def find_aapt(",
            "def find_aapt2(",
            "def find_apksigner(",
            "def run_aapt_badging(",
            "def run_apksigner_verify(",
            "def run_aapt_xmltree(",
            "def run_aapt2_resources(",
            "def permissions_from_badging(",
            "def apk_signature_summary(",
            "def png_rgba_from_bytes(",
            "def store_icon_rgba(",
            "def elf_load_alignments(",
            "def native_library_alignment_summary(",
            "def verify_native_library_alignment(",
            "def zip_entry_data_offset(",
            "def power_of_two_alignment(",
            "def native_library_zip_packaging_summary(",
            "def verify_native_library_zip_packaging(",
            "def resource_file_map(",
            "def application_icon_resource_ids(",
            "def application_icon_matching_candidates(",
            "def manifest_application_resource_id(",
            "def manifest_application_attributes(",
            "def manifest_boolean_value(",
            "def verify_manifest_privacy_posture(",
            "def verify_extract_native_libs_posture(",
            "def manifest_icon_matching_candidates(",
            "def icon_candidates(",
            "APK requests unexpected permissions",
            "APK requests forbidden permissions",
            "APK signature verification found no signers.",
            "APK is signed with an Android Debug certificate",
            "APK signature must verify with APK Signature Scheme v2, v3 or v3.1.",
            "APK manifest is missing explicit android:allowBackup=false.",
            "APK manifest android:allowBackup must be false.",
            "APK manifest android:debuggable must be absent or false.",
            "APK manifest is missing explicit android:extractNativeLibs=false.",
            "APK manifest android:extractNativeLibs must be false for 16 KB ZIP-aligned native loading.",
            "APK native libraries must support 16 KB page sizes",
            "APK native libraries must be stored uncompressed for 16 KB page-size direct loading",
            "APK native libraries must be 16 KB ZIP-aligned",
            "APK does not contain a 512x512 PNG icon candidate.",
            "pixel-match play_store/icon/play_icon_512.png",
            "does not link to a store-icon pixel match",
            "--dry-run",
            "--apk",
            "play_generated_apk_verify_dry_run_ok",
            "play_generated_apk_verify_ok",
        ],
    )

    dry_output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Play-generated APK verification dry run",
        "expected package: com.qgrid.mobile",
        "expected versionCode: 1",
        "expected versionName: 1.0.0",
        "expected label: Линия 56",
        "no INTERNET, no ACCESS_NETWORK_STATE and no dangerous runtime permissions",
        "required signature posture: APK signature verifies, certificate SHA-256 is printed and Android Debug certificates are rejected",
        "required manifest privacy posture: allowBackup=false and no debuggable release manifest",
        "required icon posture: a 512x512 PNG candidate must pixel-match play_store/icon/play_icon_512.png",
        "required app icon posture: application icon reference must link to the store-icon pixel match",
        "required round icon posture: round icon reference must link to the store-icon pixel match",
        "required native posture: native libraries, when present, have PT_LOAD alignment >= 16384 bytes for 16 KB page sizes",
        "required native APK packaging posture: native libraries must be uncompressed, 16 KB ZIP-aligned and extractNativeLibs=false",
        "play_generated_apk_verify_dry_run_ok",
    ]:
        require(marker in dry_output, f"Play-generated APK helper dry-run missing marker: {marker}")

    release_apk = require_file("app/build/outputs/apk/release/app-release.apk")
    release_output = subprocess.check_output(
        [str(helper), "--apk", str(release_apk)],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Play-generated APK verification",
        "package: com.qgrid.mobile",
        "versionCode: 1",
        "versionName: 1.0.0",
        "label: Линия 56",
        "minSdk/targetSdk: 24/36",
        "signer certificate DN: CN=QuietGrid Upload, OU=QuietGrid, O=QuietGrid, L=Local, ST=Local, C=US",
        "signer certificate SHA-256: dd971e778a0a87e79e1a44181d453b83807fb306ff48deacbafd4811368372f1",
        "signature schemes: v1=false, v2=true, v3=false, v3.1=false, v4=false",
        "permissions: com.qgrid.mobile.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION",
        "allowBackup: false",
        "debuggable: absent",
        "extractNativeLibs: false",
        "512x512 icon candidates:",
        "store icon pixel matches:",
        "application icon linked store icon:",
        "round icon reference:",
        "round icon linked store icon:",
        "native libraries: 8 checked; minimum PT_LOAD alignment: 16384 bytes",
        "native APK packaging: 8 uncompressed; minimum ZIP data alignment: 16384 bytes",
        "play_generated_apk_verify_ok",
    ]:
        require(marker in release_output, f"Play-generated APK helper release check missing marker: {marker}")

    debug_apk = require_file("app/build/outputs/apk/debug/app-debug.apk")
    rejected = subprocess.run(
        [str(helper), "--apk", str(debug_apk)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    require(rejected.returncode != 0, "Play-generated APK helper must reject debug APK")
    require(
        "APK package mismatch: 'com.qgrid.mobile.debug' != 'com.qgrid.mobile'" in rejected.stdout,
        f"Play-generated APK helper rejected debug APK with unexpected message: {rejected.stdout}",
    )

    spec = importlib.util.spec_from_file_location("line56_play_generated_apk", helper)
    require(spec is not None and spec.loader is not None, "cannot import Play-generated APK helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    release_result = module.verify_apk(release_apk)
    require(release_result["package"] == "com.qgrid.mobile", "Play-generated APK helper module returned wrong release package")
    require(release_result["versionCode"] == "1", "Play-generated APK helper module returned wrong release versionCode")
    require(release_result["versionName"] == "1.0.0", "Play-generated APK helper module returned wrong release versionName")
    require(release_result["label"] == "Линия 56", "Play-generated APK helper module returned wrong release label")
    require(
        release_result["signature"]["certificateSha256"] == "dd971e778a0a87e79e1a44181d453b83807fb306ff48deacbafd4811368372f1",
        "Play-generated APK helper module returned wrong local release signer certificate SHA-256",
    )
    require(release_result["signature"]["signatureSchemes"].get("v2") is True, "Play-generated APK helper module did not verify v2 APK signing")
    require(release_result["allowBackup"] is False, "Play-generated APK helper module returned wrong allowBackup posture")
    require(release_result["debuggable"] in {"absent", "false"}, "Play-generated APK helper module returned wrong debuggable posture")
    require(release_result["extractNativeLibs"] is False, "Play-generated APK helper module returned wrong extractNativeLibs posture")
    require(release_result["matchingIconCandidates"], "Play-generated APK helper module did not find a store-icon pixel match")
    require(release_result["linkedIconCandidates"], "Play-generated APK helper module did not link application icon to store-icon match")
    require(release_result["roundIconReferences"], "Play-generated APK helper module did not find a round icon reference")
    require(release_result["roundLinkedIconCandidates"], "Play-generated APK helper module did not link round icon to store-icon match")
    require(len(release_result["nativeLibraries"]) == 8, "Play-generated APK helper module returned wrong native library count")
    require(
        release_result["minimumNativeLoadAlignment"] == 16384,
        "Play-generated APK helper module returned wrong native library alignment",
    )
    require(
        release_result["minimumNativeZipAlignment"] == 16384,
        "Play-generated APK helper module returned wrong native library ZIP alignment",
    )
    original_alignment_summary = module.native_library_alignment_summary
    try:
        module.native_library_alignment_summary = lambda _apk: (["lib/arm64-v8a/bad.so"], 4096)
        try:
            module.verify_native_library_alignment(release_apk)
        except module.ApkReviewError as exc:
            require("16 KB page sizes" in str(exc), f"Play-generated APK helper rejected low native alignment with unexpected message: {exc}")
        else:
            raise CheckFailure("Play-generated APK helper must reject native libraries below 16 KB alignment")
    finally:
        module.native_library_alignment_summary = original_alignment_summary

    original_apksigner_verify = module.run_apksigner_verify
    for bad_output, expected_message in [
        ("Verifies\nNumber of signers: 0\n", "found no signers"),
        (
            "Verifies\n"
            "Verified using v1 scheme (JAR signing): true\n"
            "Verified using v2 scheme (APK Signature Scheme v2): false\n"
            "Verified using v3 scheme (APK Signature Scheme v3): false\n"
            "Verified using v3.1 scheme (APK Signature Scheme v3.1): false\n"
            "Number of signers: 1\n"
            "Signer #1 certificate DN: CN=Release\n"
            "Signer #1 certificate SHA-256 digest: " + "a" * 64 + "\n",
            "APK Signature Scheme v2, v3 or v3.1",
        ),
        (
            "Verifies\n"
            "Verified using v2 scheme (APK Signature Scheme v2): true\n"
            "Number of signers: 1\n"
            "Signer #1 certificate DN: C=US, O=Android, CN=Android Debug\n"
            "Signer #1 certificate SHA-256 digest: " + "b" * 64 + "\n",
            "Android Debug certificate",
        ),
    ]:
        try:
            module.run_apksigner_verify = lambda _apk, output=bad_output: output
            try:
                module.apk_signature_summary(release_apk)
            except module.ApkReviewError as exc:
                require(expected_message in str(exc), f"Play-generated APK helper rejected bad signature output with unexpected message: {exc}")
            else:
                raise CheckFailure("Play-generated APK helper must reject bad APK signature posture")
        finally:
            module.run_apksigner_verify = original_apksigner_verify

    try:
        module.apk_signature_summary(debug_apk)
    except module.ApkReviewError as exc:
        require("Android Debug certificate" in str(exc), f"Play-generated APK helper rejected debug certificate with unexpected message: {exc}")
    else:
        raise CheckFailure("Play-generated APK helper must reject Android Debug signing certificates")

    original_zip_packaging_summary = module.native_library_zip_packaging_summary
    for bad_summary, expected_message in [
        ((["lib/arm64-v8a/bad.so"], 4096, []), "16 KB ZIP-aligned"),
        ((["lib/arm64-v8a/bad.so"], 16384, ["lib/arm64-v8a/bad.so"]), "stored uncompressed"),
    ]:
        try:
            module.native_library_zip_packaging_summary = lambda _apk, summary=bad_summary: summary
            try:
                module.verify_native_library_zip_packaging(release_apk)
            except module.ApkReviewError as exc:
                require(expected_message in str(exc), f"Play-generated APK helper rejected bad native ZIP packaging with unexpected message: {exc}")
            else:
                raise CheckFailure("Play-generated APK helper must reject bad native ZIP packaging")
        finally:
            module.native_library_zip_packaging_summary = original_zip_packaging_summary

    original_manifest_attributes = module.manifest_application_attributes
    for bad_attributes, expected_message in [
        ({}, "missing explicit android:allowBackup=false"),
        ({"allowBackup": "(type 0x12)0xffffffff"}, "allowBackup must be false"),
        (
            {"allowBackup": "(type 0x12)0x0", "debuggable": "(type 0x12)0xffffffff"},
            "debuggable must be absent or false",
        ),
        (
            {"allowBackup": "(type 0x12)0x0"},
            "missing explicit android:extractNativeLibs=false",
        ),
        (
            {"allowBackup": "(type 0x12)0x0", "extractNativeLibs": "(type 0x12)0xffffffff"},
            "extractNativeLibs must be false",
        ),
    ]:
        try:
            module.manifest_application_attributes = lambda _apk, attrs=bad_attributes: attrs
            try:
                module.verify_apk(release_apk)
            except module.ApkReviewError as exc:
                require(expected_message in str(exc), f"Play-generated APK helper rejected manifest privacy regression with unexpected message: {exc}")
            else:
                raise CheckFailure("Play-generated APK helper must reject manifest privacy regressions")
        finally:
            module.manifest_application_attributes = original_manifest_attributes

    original_icon_link_checker = module.application_icon_matching_candidates
    try:
        module.application_icon_matching_candidates = lambda _apk, _icon_reference, _matching_candidates: []
        try:
            module.verify_apk(release_apk)
        except module.ApkReviewError as exc:
            require("does not link to a store-icon pixel match" in str(exc), f"Play-generated APK helper rejected unlinked icon with unexpected message: {exc}")
        else:
            raise CheckFailure("Play-generated APK helper must reject app icons that do not link to the store-icon pixel match")
    finally:
        module.application_icon_matching_candidates = original_icon_link_checker

    original_manifest_icon_link_checker = module.manifest_icon_matching_candidates
    try:
        module.manifest_icon_matching_candidates = lambda _apk, _attribute_name, _matching_candidates: (["res/round.xml"], [])
        try:
            module.verify_apk(release_apk)
        except module.ApkReviewError as exc:
            require("round icon reference does not link to a store-icon pixel match" in str(exc), f"Play-generated APK helper rejected unlinked round icon with unexpected message: {exc}")
        else:
            raise CheckFailure("Play-generated APK helper must reject round icons that do not link to the store-icon pixel match")
    finally:
        module.manifest_icon_matching_candidates = original_manifest_icon_link_checker

    def solid_png(width: int, height: int, rgba: bytes) -> bytes:
        def chunk(name: bytes, payload: bytes) -> bytes:
            return (
                struct.pack(">I", len(payload))
                + name
                + payload
                + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)
            )

        raw_rows = b"".join(b"\x00" + rgba * width for _ in range(height))
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk("IHDR".encode("ascii"), struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk("IDAT".encode("ascii"), zlib.compress(raw_rows))
            + chunk("IEND".encode("ascii"), b"")
        )

    with tempfile.TemporaryDirectory(prefix="line56-apk-icon-", dir=ROOT / "build") as temp_dir:
        tampered_apk = Path(temp_dir) / "app-release-icon-mismatch.apk"
        matching_icon = release_result["matchingIconCandidates"][0]
        with zipfile.ZipFile(release_apk) as source, zipfile.ZipFile(tampered_apk, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == matching_icon:
                    data = solid_png(512, 512, b"\xff\x00\x00\xff")
                target.writestr(info, data)
        original_signature_summary = module.apk_signature_summary
        try:
            module.apk_signature_summary = lambda _apk: release_result["signature"]
            try:
                module.verify_apk(tampered_apk)
            except module.ApkReviewError as exc:
                require("pixel-for-pixel" in str(exc), f"Play-generated APK helper rejected icon mismatch with unexpected message: {exc}")
            else:
                raise CheckFailure("Play-generated APK helper must reject 512x512 icons that do not match the store icon")
        finally:
            module.apk_signature_summary = original_signature_summary

    try:
        module.verify_apk(debug_apk)
    except module.ApkReviewError as exc:
        require("APK package mismatch" in str(exc), f"Play-generated APK helper module rejected debug APK with unexpected message: {exc}")
    else:
        raise CheckFailure("Play-generated APK helper module must reject debug APK")


def check_publication_readiness_helper() -> None:
    helper = require_file("tools/print_publication_readiness.py")
    require(os.access(helper, os.X_OK), "tools/print_publication_readiness.py must be executable")
    require_text_markers(
        "tools/print_publication_readiness.py",
        [
            "Print local-vs-production publication readiness for the owner.",
            "This helper is intentionally read-only.",
            "POST_UPLOAD_EVIDENCE = ROOT / \"play_store/play_console_post_upload_evidence_ru.md\"",
            "SIGNING_BACKUP_EVIDENCE = ROOT / \"play_store/signing_backup_evidence_ru.md\"",
            "OWNER_INPUTS = ROOT / \"play_store/owner_release_inputs.md\"",
            "REQUIRED_OWNER_GATES = (",
            "POST_UPLOAD_LABELS = (",
            "SIGNING_BACKUP_LABELS = (",
            "OWNER_ACTION_GROUPS = (",
            "FORBIDDEN_EVIDENCE_MARKERS = (",
            "FORBIDDEN_EVIDENCE_PATTERNS = (",
            "client_secret",
            "access[_-]?token",
            "PLACEHOLDER_PRIVACY_HOSTS = (",
            "POSITIVE_EVIDENCE_VALUES = (",
            "NEGATIVE_EVIDENCE_PHRASES = (",
            "FULL_DATE_PATTERNS = (",
            "Public privacy policy URL",
            "Play Console support/contact field populated",
            "Active upload keystore backed up before AAB upload",
            "Internal testing upload completed",
            "internal testing first",
            "def expected_aab_sha256(",
            "def collect_evidence_status(",
            "def validate_post_upload_value(",
            "def validate_closed_testing_consistency(",
            "def validate_signing_backup_value(",
            "def validate_no_negative_markers(",
            "def normalized_public_https_url(",
            "def validate_public_https_url(",
            "def validate_privacy_url_matches_recorded(",
            "def validate_no_forbidden_evidence(",
            "def negative_status_markers(",
            "def unresolved_label(",
            "def print_owner_action_breakdown(",
            "checked_url = normalized_public_https_url(\"--privacy-url\", url, \"command line\")",
            "must not include query parameters",
            "must be a positive confirmation without negative status markers",
            "must explicitly say evidence was recorded without secrets",
            "validate_contains_all(label, value, file_label, (\"private/signing/qgrid-upload.p12\", \"before AAB upload\"))",
            "\"Play-generated APK signature verifies and certificate SHA-256 recorded\"",
            "must include a certificate SHA-256 fingerprint",
            "must not be an Android Debug certificate",
            "\"Play-generated icon matches `play_store/icon/play_icon_512.png`\"",
            "(\"application icon\", \"round icon\", \"store icon\", \"pixel\")",
            "\"Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest\"",
            "(\"allowBackup=false\", \"no debuggable\")",
            "(\"16 KB\", \"16384\", \"uncompressed\", \"ZIP-aligned\", \"extractNativeLibs=false\")",
            "\"Play-generated APK installed and launched on at least one Android device or emulator\"",
            "must mention an Android device or emulator",
            "\"Store listing preview checked for damaging image crops\"",
            "must explicitly say there are no damaging crops",
            "must explicitly mention at least two secure copies",
            "must explicitly say recovery was tested without exposing secrets",
            "must not be pending, unknown or negative evidence",
            "must include a full date such as 2026-06-06",
            "closed testing is required but status is not completed",
            "closed testing is not required but status says completed",
            "def validate_contains_0o600(",
            "def recorded_privacy_url_value(",
            "--privacy-url",
            "--check-recorded-privacy-url",
            "--require-production-ready",
            "--dry-run",
            "def verify_local_handoff_files(",
            "def validate_privacy_url(",
            "privacy_policy_url_ok",
            "Publication readiness",
            "Production rollout status: NOT READY",
            "Owner action breakdown",
            "group unresolved owner actions by evidence file and required command",
            "Upload artifact identity",
            "Privacy policy and Play contact",
            "Signing backup",
            "Play-generated artifact review",
            "manifest privacy and native 16 KB page-size posture",
            "native 16 KB page-size posture",
            "Play Console forms",
            "Testing track and final review",
            "publication_readiness_local_ready_external_pending",
            "publication_readiness_blocked",
            "publication_readiness_production_ready_owner_confirmed",
        ],
    )
    dry_output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Publication readiness dry run",
        "validate owner release inputs",
        "validate exact recorded evidence values against package/version/checksum/privacy/signing expectations",
        "list owner-controlled external gates",
        "group unresolved owner actions by evidence file and required command",
        "validate recorded public HTTPS privacy policy URL via `--check-recorded-privacy-url`",
        "publication_readiness_dry_run_ok",
    ]:
        require(marker in dry_output, f"publication readiness dry-run missing marker: {marker}")

    output = subprocess.check_output(
        [str(helper)],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Publication readiness",
        "Local release candidate: READY",
        "Production rollout status: NOT READY",
        "Play Console support/contact field populated: not yet available locally",
        "Active upload keystore backed up before AAB upload: not yet available locally",
        "Owner action breakdown",
        "Privacy policy and Play contact: 2 unresolved field(s).",
        "action: Validate the hosted privacy policy URL, enter it in Play Console and populate Play Console support/contact fields.",
        "command: ./tools/check_privacy_policy_url.py --url <https-url>",
        "Signing backup: 9 unresolved field(s).",
        "evidence: play_store/play_console_post_upload_evidence_ru.md, play_store/signing_backup_evidence_ru.md",
        "command: ./tools/check_signing_backup_inputs.py",
        "Play-generated artifact review: 9 unresolved field(s).",
        "Testing track and final review: 7 unresolved field(s).",
        "publication_readiness_local_ready_external_pending",
    ]:
        require(marker in output, f"publication readiness output missing marker: {marker}")

    blocked = subprocess.run(
        [str(helper), "--require-production-ready"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(blocked.returncode != 0, "publication readiness --require-production-ready must fail while external gates are unresolved")
    require("publication_readiness_blocked" in blocked.stdout, "publication readiness production-required mode must print publication_readiness_blocked")

    spec = importlib.util.spec_from_file_location("line56_publication_readiness", helper)
    require(spec is not None and spec.loader is not None, "publication readiness helper could not be loaded for regression checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected_sha = module.expected_aab_sha256(read("play_store/upload_checksums.md"))

    negative_post_upload_cases = [
        ("Uploaded package name", "com.wrong.package", "unexpected value"),
        ("Uploaded AAB SHA-256", "0" * 64, "unexpected value"),
        ("First release track used", "production", "internal testing first"),
        ("First release track used", "closed testing", "internal testing first"),
        ("Public privacy policy URL", "http://example.com/privacy", "must be HTTPS"),
        ("Public privacy policy URL", "https://user:pass@privacy.example.co/policy", "must not include credentials"),
        ("Public privacy policy URL", "https://example.com/privacy", "must not use a placeholder host"),
        ("Public privacy policy URL", "https://10.0.0.1/privacy", "must be public"),
        ("Public privacy policy URL", "https://privacy.example.co/policy?utm_source=play", "must not include query parameters"),
        ("Public privacy policy URL", "https://privacy.example.co/policy#copy", "must not include a URL fragment"),
        ("Play Console support/contact field populated", "none", "missing"),
        ("Play Console support/contact field populated", "yes", "missing"),
        ("Play Console support/contact field populated", "yes, but not completed", "negative status markers"),
        (
            "Support/contact mechanism matches `play_store/privacy_policy_ru.html`",
            "yes",
            "missing",
        ),
        ("Owner-controlled backup evidence recorded without secrets", "yes", "without secrets"),
        ("Active upload keystore backed up before AAB upload", "yes", "missing"),
        (
            "Active upload keystore backed up before AAB upload",
            "private/signing/qgrid-upload.p12",
            "before AAB upload",
        ),
        ("Play-generated APK signature verifies and certificate SHA-256 recorded", "verified SHA-256", "certificate SHA-256 fingerprint"),
        (
            "Play-generated APK signature verifies and certificate SHA-256 recorded",
            "verified SHA-256 aa26d9564ed889380da8132dadbc4b255312deb463bf21e58f5b0709abf92b3e Android Debug",
            "Android Debug certificate",
        ),
        ("Play-generated icon matches `play_store/icon/play_icon_512.png`", "yes, application icon linked store icon pixel matches helper output", "missing"),
        ("Play-generated version code/name match this release candidate", "yes", "versionCode 1"),
        (
            "Play-generated version code/name match this release candidate",
            "versionCode 1",
            "versionName 1.0.0",
        ),
        ("Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions", "looks fine", "missing"),
        (
            "Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions",
            "no INTERNET, no ACCESS_NETWORK_STATE, no dangerous runtime permissions, not completed",
            "negative status markers",
        ),
        ("Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest", "looks fine", "missing"),
        (
            "Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest",
            "allowBackup=false, no debuggable release manifest, not completed",
            "negative status markers",
        ),
        ("Play-generated native libraries support 16 KB page sizes", "looks fine", "missing"),
        (
            "Play-generated native libraries support 16 KB page sizes",
            "16 KB page sizes, PT_LOAD alignment 16384 bytes",
            "missing",
        ),
        ("Play-generated APK installed and launched on at least one Android device or emulator", "yes", "missing"),
        (
            "Play-generated APK installed and launched on at least one Android device or emulator",
            "installed and launched",
            "missing",
        ),
        ("App access completed as no restricted access/login/account", "yes", "missing"),
        (
            "App access completed as no restricted access/login/account",
            "no login, no account",
            "missing",
        ),
        ("Ads declaration completed as no ads", "yes", "missing"),
        ("Data Safety completed as no user data collected or shared", "yes", "missing"),
        (
            "Data Safety completed as no user data collected or shared",
            "no user data collected",
            "missing",
        ),
        ("Content rating completed as Games / Puzzle posture", "Puzzle", "missing"),
        (
            "Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path",
            "13+",
            "non-child-directed",
        ),
        (
            "AI disclosure completed as no in-app generative AI features",
            "yes",
            "no in-app generative AI features",
        ),
        ("Store listing preview checked for damaging image crops", "yes", "missing"),
        (
            "Store listing preview checked for damaging image crops",
            "icon, feature graphic, screenshots, no damaging crops",
            "missing",
        ),
        (
            "Store listing preview checked for damaging image crops",
            "icon, feature graphic, phone screenshots, tablet screenshots",
            "no damaging crops",
        ),
    ]
    for label, value, expected_message in negative_post_upload_cases:
        try:
            module.validate_post_upload_value(label, value, "verifier bad post-upload evidence", expected_sha)
        except module.PublicationReadinessError as exc:
            require(expected_message in str(exc), f"publication helper rejected {label} with unexpected message: {exc}")
        else:
            raise CheckFailure(f"publication helper must reject bad post-upload evidence for {label}")

    module.validate_post_upload_value("Upload date/time", "2026-06-06 12:30", "verifier good post-upload evidence", expected_sha)
    module.validate_signing_backup_value("Backup date/time", "6 June 2026, 12:30", "verifier good signing evidence")
    post_upload_template = read("play_store/play_console_post_upload_evidence_ru.md")

    def closed_testing_post_upload(required: str, status: str) -> str:
        return post_upload_template.replace(
            "- Closed testing required for this account: not yet available locally.",
            f"- Closed testing required for this account: {required}.",
        ).replace(
            "- Closed testing status if required: not yet available locally.",
            f"- Closed testing status if required: {status}.",
        )

    module.validate_closed_testing_consistency(post_upload_template, "verifier pending post-upload evidence")
    module.validate_closed_testing_consistency(
        closed_testing_post_upload("yes", "completed required closed testing"),
        "verifier required closed-testing evidence",
    )
    module.validate_closed_testing_consistency(
        closed_testing_post_upload("no", "not required for this account"),
        "verifier no-closed-testing evidence",
    )
    for required, status, expected_message in [
        ("yes", "not required for this account", "closed testing is required but status is not completed"),
        ("no", "completed required closed testing", "closed testing is not required but status says completed"),
    ]:
        try:
            module.validate_closed_testing_consistency(
                closed_testing_post_upload(required, status),
                "verifier inconsistent closed-testing evidence",
            )
        except module.PublicationReadinessError as exc:
            require(expected_message in str(exc), f"publication helper rejected inconsistent closed-testing evidence with unexpected message: {exc}")
        else:
            raise CheckFailure("publication helper must reject inconsistent closed-testing evidence")

    def replace_evidence_lines(template: str, replacements: dict[str, str]) -> str:
        completed = template
        for label, value in replacements.items():
            completed = re.sub(
                rf"^- {re.escape(label)}: .+$",
                f"- {label}: {value}.",
                completed,
                count=1,
                flags=re.MULTILINE,
            )
        return completed

    completed_post_upload = replace_evidence_lines(
        post_upload_template,
        {
            "Uploaded package name": "com.qgrid.mobile",
            "Uploaded version code": "1",
            "Uploaded version name": "1.0.0",
            "Uploaded AAB SHA-256": expected_sha,
            "First release track used": "internal testing",
            "Upload date/time": "2026-06-06 12:30",
            "Public privacy policy URL": "https://privacy.qgrid.app/line56",
            "Privacy policy URL check command returned `privacy_policy_url_ok`": "privacy_policy_url_ok",
            "Privacy policy URL is HTTPS": "yes",
            "Privacy policy URL is accessible without login": "yes",
            "Privacy policy URL is not PDF": "yes",
            "Play Console support/contact field populated": "Play Console support/contact field populated",
            "Support/contact mechanism matches `play_store/privacy_policy_ru.html`": "privacy policy uses the Google Play listing support contact",
            "Active upload keystore backed up before AAB upload": "private/signing/qgrid-upload.p12 backed up before AAB upload",
            "Owner-controlled backup evidence recorded without secrets": "yes, recorded without secrets",
            "Play-generated APK package is `com.qgrid.mobile`": "com.qgrid.mobile",
            "Play-generated APK signature verifies and certificate SHA-256 recorded": "verified, SHA-256 dd971e778a0a87e79e1a44181d453b83807fb306ff48deacbafd4811368372f1",
            "Play-generated app label is `Линия 56`": "Линия 56",
            "Play-generated icon matches `play_store/icon/play_icon_512.png`": "yes, application icon linked store icon pixel matches and round icon linked store icon pixel matches helper output",
            "Play-generated version code/name match this release candidate": "versionCode 1, versionName 1.0.0",
            "Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions": "no INTERNET, no ACCESS_NETWORK_STATE, no dangerous runtime permissions",
            "Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest": "allowBackup=false, no debuggable release manifest",
            "Play-generated native libraries support 16 KB page sizes": "16 KB page sizes, minimum PT_LOAD alignment 16384 bytes, uncompressed, ZIP-aligned 16384 bytes, extractNativeLibs=false",
            "Play-generated APK installed and launched on at least one Android device or emulator": "installed and launched on Android emulator",
            "App access completed as no restricted access/login/account": "no restricted access, no login, no account",
            "Ads declaration completed as no ads": "no ads",
            "Data Safety completed as no user data collected or shared": "no user data collected, no user data shared",
            "Content rating completed as Games / Puzzle posture": "Games / Puzzle",
            "Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path": "13+ non-child-directed",
            "AI disclosure completed as no in-app generative AI features": "no in-app generative AI features",
            "Internal testing upload completed": "yes",
            "Closed testing required for this account": "no",
            "Closed testing status if required": "not required for this account",
            "Pre-launch report result": "passed",
            "Reproducible crashes in pre-launch report": "none",
            "Play policy warnings": "none",
            "Store listing preview checked for damaging image crops": "icon, feature graphic, phone screenshots and tablet screenshots reviewed; no damaging crops",
        },
    )
    completed_post_unresolved = module.collect_evidence_status(
        completed_post_upload,
        module.POST_UPLOAD_LABELS,
        "verifier completed post-upload evidence fixture",
        expected_sha=expected_sha,
    )
    require(not completed_post_unresolved, f"publication helper must accept completed post-upload evidence fixture: {completed_post_unresolved}")
    module.validate_closed_testing_consistency(completed_post_upload, "verifier completed post-upload evidence fixture")

    completed_signing_backup = replace_evidence_lines(
        read("play_store/signing_backup_evidence_ru.md"),
        {
            "Backup completed before Play upload": "yes",
            "Secure owner-controlled storage type chosen": "owner password manager plus encrypted offline backup",
            "At least two owner-controlled secure copies exist": "yes, two owner-controlled secure copies exist",
            "Recovery tested without exposing secrets": "yes, recovery tested without exposing secrets",
            "Responsible owner": "release owner recorded in owner tracker",
            "Backup date/time": "2026-06-06 13:00",
            "Backup record location in owner tracker or password manager": "owner password manager release record",
        },
    )
    completed_signing_unresolved = module.collect_evidence_status(
        completed_signing_backup,
        module.SIGNING_BACKUP_LABELS,
        "verifier completed signing-backup evidence fixture",
    )
    require(not completed_signing_unresolved, f"publication helper must accept completed signing-backup evidence fixture: {completed_signing_unresolved}")

    for label, validator in [
        ("Upload date/time", lambda value: module.validate_post_upload_value("Upload date/time", value, "verifier weak post-upload evidence", expected_sha)),
        ("Backup date/time", lambda value: module.validate_signing_backup_value("Backup date/time", value, "verifier weak signing evidence")),
    ]:
        for value, expected_message in [
            ("2026", "must include a full date"),
            ("pending 2026-06-06", "concrete date/time without negative status markers"),
            ("2026 unknown", "concrete date/time without negative status markers"),
        ]:
            try:
                validator(value)
            except module.PublicationReadinessError as exc:
                require(expected_message in str(exc), f"publication helper rejected weak {label} with unexpected message: {exc}")
            else:
                raise CheckFailure(f"publication helper must reject weak date evidence for {label}: {value}")

    try:
        module.validate_no_forbidden_evidence("- storePassword=secret", "verifier bad evidence")
    except module.PublicationReadinessError as exc:
        require("must not record secret/private marker" in str(exc), f"publication helper rejected secret marker with unexpected message: {exc}")
    else:
        raise CheckFailure("publication helper must reject evidence containing signing secrets")

    for bad_evidence in [
        "- storePassword: secret-value",
        "- keyPassword = secret-value",
        "- client_secret: secret-value",
        "- access_token = secret-value",
        "- refresh-token: secret-value",
        "- support bearer token: Bearer ya29.secret",
    ]:
        try:
            module.validate_no_forbidden_evidence(bad_evidence, "verifier bad evidence")
        except module.PublicationReadinessError as exc:
            require(
                "must not record secret/private evidence matching pattern" in str(exc)
                or "must not record secret/private marker" in str(exc),
                f"publication helper rejected secret pattern with unexpected message: {exc}",
            )
        else:
            raise CheckFailure(f"publication helper must reject evidence containing secret pattern: {bad_evidence}")

    try:
        module.validate_privacy_url_matches_recorded(
            "https://privacy.example.co/other",
            "https://privacy.example.co/policy",
            "verifier bad post-upload evidence",
        )
    except module.PublicationReadinessError as exc:
        require("must match recorded Public privacy policy URL" in str(exc), f"publication helper rejected mismatched checked privacy URL with unexpected message: {exc}")
    else:
        raise CheckFailure("publication helper must reject privacy URL checks that do not match recorded owner evidence")

    recorded_privacy_subprocess_calls: list[list[str]] = []
    original_subprocess_run = module.subprocess.run

    class RecordedPrivacyCompleted:
        returncode = 0
        stdout = "privacy_policy_url_ok\n"

    def fake_privacy_url_run(command: list[str], **kwargs: object) -> RecordedPrivacyCompleted:
        recorded_privacy_subprocess_calls.append(command)
        return RecordedPrivacyCompleted()

    module.subprocess.run = fake_privacy_url_run
    try:
        module.validate_privacy_url(
            "https://privacy.example.co/policy.",
            recorded_value="https://privacy.example.co/policy.",
        )
    finally:
        module.subprocess.run = original_subprocess_run
    require(
        recorded_privacy_subprocess_calls
        and recorded_privacy_subprocess_calls[0][-1] == "https://privacy.example.co/policy",
        "publication helper must strip sentence punctuation before invoking privacy URL checker",
    )

    try:
        module.validate_signing_backup_value("Active key alias", "line56_upload", "verifier bad signing evidence")
    except module.PublicationReadinessError as exc:
        require("unexpected value" in str(exc), f"publication helper rejected wrong signing alias with unexpected message: {exc}")
    else:
        raise CheckFailure("publication helper must reject wrong signing-backup alias")

    negative_signing_evidence_cases = [
        ("Active upload keystore exists and is owner-only", "`private/signing/qgrid-upload.p12`, mode `0o644`", "missing"),
        ("`keystore.properties` exists and is owner-only", "mode `0o644`", "missing"),
        ("`keystore.properties` points to `private/signing/qgrid-upload.p12`", "`private/signing/line56-upload.p12`", "unexpected value"),
        ("`keystore.properties` uses key alias `qgrid_upload`", "`line56_upload`", "unexpected value"),
        ("`storePassword` and `keyPassword` fields are present; values were not printed or recorded", "missing", "missing"),
        ("Legacy ignored local key exists and is owner-only", "`private/signing/line56-upload.p12`, mode `0o644`; ignored, not active", "missing"),
        ("At least two owner-controlled secure copies exist", "yes", "at least two secure copies"),
        ("At least two owner-controlled secure copies exist", "yes, one owner-controlled secure copy exists", "at least two secure copies"),
        ("Recovery tested without exposing secrets", "yes", "without exposing secrets"),
    ]
    for label, value, expected_message in negative_signing_evidence_cases:
        try:
            module.validate_signing_backup_value(label, value, "verifier bad signing evidence")
        except module.PublicationReadinessError as exc:
            require(expected_message in str(exc), f"publication helper rejected {label} with unexpected message: {exc}")
        else:
            raise CheckFailure(f"publication helper must reject bad signing evidence for {label}")

    for label in [
        "Responsible owner",
        "Backup record location in owner tracker or password manager",
        "Secure owner-controlled storage type chosen",
    ]:
        for value in ["pending", "unknown", "not available locally", "todo"]:
            try:
                module.validate_signing_backup_value(label, value, "verifier weak signing evidence")
            except module.PublicationReadinessError as exc:
                require("must not be pending, unknown or negative evidence" in str(exc), f"publication helper rejected weak non-empty {label} with unexpected message: {exc}")
            else:
                raise CheckFailure(f"publication helper must reject weak non-empty signing evidence for {label}: {value}")


def check_privacy_policy_url_helper() -> None:
    helper = require_file("tools/check_privacy_policy_url.py")
    require(os.access(helper, os.X_OK), "tools/check_privacy_policy_url.py must be executable")
    require_text_markers(
        "tools/check_privacy_policy_url.py",
        [
            "Validate the privacy policy page before entering it in Play Console.",
            "Use --local for the repository HTML source and --url after the owner hosts the",
            "LOCAL_POLICY = ROOT / \"play_store/privacy_policy_ru.html\"",
            "REQUIRED_TEXT_MARKERS",
            "FORBIDDEN_TEXT_MARKERS",
            "PLACEHOLDER_HOSTS",
            "RESERVED_HOST_SUFFIXES",
            "FORBIDDEN_HTML_MARKERS",
            "def canonical_policy_text(",
            "def canonical_text_sha256(",
            "def require_public_ip(",
            "def resolve_public_host(",
            "def reject_private_url(",
            "privacy policy URL must use HTTPS",
            "privacy policy URL must not include credentials",
            "privacy policy URL must not include query parameters",
            "privacy policy URL must not include a fragment",
            "privacy policy URL must not be localhost",
            "privacy policy URL must not use a placeholder host",
            "privacy policy URL must not use a reserved local/test host",
            "privacy policy URL must not be a PDF path",
            "privacy policy URL must be public",
            "privacy policy URL host must resolve publicly",
            "must resolve only to public global IPs",
            "def fetch_url(",
            "privacy policy URL must return HTTP 200",
            "privacy policy final URL must stay HTTPS",
            "privacy policy must not be served as PDF",
            "privacy policy final URL must not be a PDF path",
            "privacy policy page must be valid UTF-8",
            "def validate_html(",
            "must not include scripts, trackers or embedded external widgets",
            "def require_matches_local_policy(",
            "hosted privacy policy text must match play_store/privacy_policy_ru.html",
            "privacy_policy_text_sha256",
            "PrivacyPolicyCheckError",
            "local privacy policy",
            "hosted privacy policy",
            "privacy_policy_local_ok",
            "privacy_policy_url_ok",
            "privacy_policy_check_error",
            "контакт поддержки разработчика",
            "Google Play",
        ],
    )
    output = subprocess.check_output(
        [str(helper), "--local"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require("privacy_policy_local_ok" in output, "privacy policy helper did not validate local HTML")
    require("privacy_policy_text_sha256:" in output, "privacy policy helper did not print canonical text SHA-256")

    spec = importlib.util.spec_from_file_location("line56_privacy_policy_check", helper)
    require(spec is not None and spec.loader is not None, "privacy policy helper could not be loaded for regression checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    local_html = read("play_store/privacy_policy_ru.html")
    expected_sha = module.canonical_text_sha256(local_html)
    require(f"privacy_policy_text_sha256: {expected_sha}" in output, "privacy policy helper printed an unexpected canonical text SHA-256")
    module.validate_html(local_html, "verifier local privacy policy")

    negative_url_cases = [
        ("http://privacy.example.co/policy", "must use HTTPS"),
        ("https://user:pass@privacy.example.co/policy", "must not include credentials"),
        ("https://privacy.example.co/policy?utm_source=play", "must not include query parameters"),
        ("https://privacy.example.co/policy#section", "must not include a fragment"),
        ("https://localhost/policy", "must not be localhost"),
        ("https://example.com/privacy", "must not use a placeholder host"),
        ("https://privacy.test/policy", "must not use a reserved local/test host"),
        ("https://10.0.0.1/privacy", "must resolve only to public global IPs"),
        ("https://privacy.example.co/privacy.pdf", "must not be a PDF path"),
    ]
    for url, expected_message in negative_url_cases:
        try:
            module.reject_private_url(url, resolve_host=False)
        except module.PrivacyPolicyCheckError as exc:
            require(expected_message in str(exc), f"privacy helper rejected bad URL {url} with unexpected message: {exc}")
        else:
            raise CheckFailure(f"privacy helper must reject bad URL: {url}")

    original_getaddrinfo = module.socket.getaddrinfo
    try:
        module.socket.getaddrinfo = lambda *_args, **_kwargs: [
            (module.socket.AF_INET, module.socket.SOCK_STREAM, 6, "", ("192.168.1.10", 443))
        ]
        try:
            module.reject_private_url("https://privacy.example.co/policy", resolve_host=True)
        except module.PrivacyPolicyCheckError as exc:
            require("must resolve only to public global IPs" in str(exc), f"privacy helper rejected private DNS resolution with unexpected message: {exc}")
        else:
            raise CheckFailure("privacy helper must reject DNS results that resolve to private IP addresses")
    finally:
        module.socket.getaddrinfo = original_getaddrinfo

    script_html = local_html.replace("</body>", "<script>document.cookie='x'</script></body>")
    try:
        module.validate_html(script_html, "verifier script-injected privacy policy")
    except module.PrivacyPolicyCheckError as exc:
        require("scripts, trackers or embedded external widgets" in str(exc), "privacy helper rejected script injection with an unexpected error")
    else:
        raise CheckFailure("privacy helper must reject script-injected hosted policy HTML")

    mismatched_html = local_html.replace("не собирает", "собирает", 1)
    try:
        module.require_matches_local_policy(mismatched_html)
    except module.PrivacyPolicyCheckError as exc:
        require("must match play_store/privacy_policy_ru.html" in str(exc), "privacy helper rejected hosted mismatch with an unexpected error")
    else:
        raise CheckFailure("privacy helper must reject hosted policy text that differs from the local HTML")


def check_remote_release_helper() -> None:
    helper = require_file("tools/verify_remote_release.py")
    require(os.access(helper, os.X_OK), "tools/verify_remote_release.py must be executable")
    require_text_markers(
        "tools/verify_remote_release.py",
        [
            "Verify the pushed GitHub release handoff after local gates pass.",
            "networked and post-push oriented",
            "verify an explicit annotated remote release tag",
            "verifies every remote upload",
            "rejects unexpected extra",
            "CHECKSUMS_PATH = ROOT / \"play_store/upload_checksums.md\"",
            "POST_UPLOAD_EVIDENCE_PATH = ROOT / \"play_store/play_console_post_upload_evidence_ru.md\"",
            "PRIVACY_URL_CHECK = ROOT / \"tools/check_privacy_policy_url.py\"",
            "AAB_PATH = \"app/build/outputs/bundle/release/app-release.aab\"",
            "MAIN_FORBIDDEN_PATTERNS",
            "case-insensitively",
            "def forbidden_path_pattern(",
            "re.IGNORECASE",
            "forbidden_path_pattern(r\"\\.jks$\")",
            "forbidden_path_pattern(r\"\\.keystore$\")",
            "forbidden_path_pattern(r\"\\.pem$\")",
            "forbidden_path_pattern(r\"\\.pk8$\")",
            "forbidden_path_pattern(r\"\\.key$\")",
            "PAGES_FORBIDDEN_PATTERNS",
            "--remote",
            "--branch",
            "--pages-branch",
            "--tag",
            "--privacy-url",
            "--skip-privacy-url",
            "--allow-dirty",
            "--dry-run",
            "def expected_aab(",
            "def require_safe_checksum_path(",
            "def parse_upload_checksum_rows(",
            "def recorded_privacy_url(",
            "def require_clean_worktree(",
            "def fetch_remote(",
            "def remote_tag_ref(",
            "def require_remote_head_matches(",
            "def require_remote_tag_matches(",
            "def verify_remote_aab(",
            "def verify_remote_upload_assets(",
            "def verify_forbidden_paths(",
            "def verify_expected_aab_paths(",
            "def validate_privacy_url(",
            "verify_expected_aab_paths(f\"{args.remote}/{args.branch}\", release_paths)",
            "remote release branch AAB path scan: ok",
            "remote_release_dry_run_ok",
            "remote_release_ok",
            "remote_release_error",
        ],
    )
    output = subprocess.check_output(
        [str(helper), "--dry-run"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Remote release verification",
        "Remote: origin",
        "Branch: main",
        "Pages branch: gh-pages",
        "- fetch origin main and gh-pages",
        "- require origin/main matches local HEAD",
        "- verify every remote upload asset bytes and SHA-256 from `play_store/upload_checksums.md`",
        "- scan remote release branch for signing/install artifacts",
        "- require remote release branch contains no extra AAB files beyond `app/build/outputs/bundle/release/app-release.aab`",
        "- scan remote pages branch for signing/install/binary artifacts",
        "- validate hosted privacy URL: https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html",
        "remote_release_dry_run_ok",
    ]:
        require(marker in output, f"remote release dry-run missing marker: {marker}")

    tagged_output = subprocess.check_output(
        [str(helper), "--dry-run", "--tag", "v1.0.0-rc5"],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for marker in [
        "Tag: v1.0.0-rc5",
        "- require origin tag v1.0.0-rc5 is annotated and peels to local HEAD",
        "remote_release_dry_run_ok",
    ]:
        require(marker in tagged_output, f"remote release tagged dry-run missing marker: {marker}")

    spec = importlib.util.spec_from_file_location("line56_remote_release_check", helper)
    require(spec is not None and spec.loader is not None, "remote release helper could not be loaded for regression checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checksum_rows = module.parse_upload_checksum_rows()
    require(len(checksum_rows) == 13, "remote release helper parsed unexpected upload asset row count")
    require(
        checksum_rows[1][0] == "play_store/icon/play_icon_512.png",
        "remote release helper parsed unexpected upload asset order",
    )
    expected_size, expected_sha = module.expected_aab()
    require(expected_size == 2930928, "remote release helper parsed unexpected AAB size")
    require(expected_sha == "3affd5cc6de7735d7cb9cc4f381e114caa0b20d6bfa933621d596d24dc2e3043", "remote release helper parsed unexpected AAB SHA")
    require(
        module.recorded_privacy_url() == "https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html",
        "remote release helper parsed unexpected recorded privacy URL",
    )
    require(
        module.remote_tag_ref("origin", "v1.0.0-rc5") == "refs/remotes/origin/tags/v1.0.0-rc5",
        "remote release helper produced unexpected remote tag ref",
    )
    try:
        module.require_safe_checksum_path("../private/signing/qgrid-upload.p12")
    except module.RemoteReleaseError as exc:
        require("unsafe upload checksum path" in str(exc), "remote release helper rejected unsafe checksum path with unexpected message")
    else:
        raise CheckFailure("remote release helper must reject unsafe upload checksum paths")

    original_run_bytes = module.run_bytes

    def local_upload_asset_bytes(args: list[str], *, timeout: int = 60) -> bytes:
        path = args[-1].split(":", 1)[1]
        return (ROOT / path).read_bytes()

    try:
        module.run_bytes = local_upload_asset_bytes
        remote_assets = module.verify_remote_upload_assets("origin", "main")
        require(len(remote_assets) == 13, "remote release helper verified unexpected remote upload asset count")
        require(
            remote_assets[0][0] == "app/build/outputs/bundle/release/app-release.aab",
            "remote release helper returned unexpected first remote upload asset",
        )

        def mismatched_upload_asset_bytes(args: list[str], *, timeout: int = 60) -> bytes:
            path = args[-1].split(":", 1)[1]
            if path == "play_store/icon/play_icon_512.png":
                return b"not the remote icon"
            return (ROOT / path).read_bytes()

        module.run_bytes = mismatched_upload_asset_bytes
        try:
            module.verify_remote_upload_assets("origin", "main")
        except module.RemoteReleaseError as exc:
            require(
                "remote upload asset size mismatch for play_store/icon/play_icon_512.png" in str(exc),
                "remote release helper rejected remote upload asset mismatch with unexpected message",
            )
        else:
            raise CheckFailure("remote release helper must reject remote upload asset byte mismatches")
    finally:
        module.run_bytes = original_run_bytes

    original_run_text = module.run_text

    def fake_tag_run_text(args: list[str], *, timeout: int = 60) -> str:
        if args == ["git", "cat-file", "-t", "refs/remotes/origin/tags/v-test"]:
            return "tag"
        if args == ["git", "rev-parse", "refs/remotes/origin/tags/v-test"]:
            return "tag-object"
        if args == ["git", "rev-parse", "refs/remotes/origin/tags/v-test^{}"]:
            return "commit-object"
        raise AssertionError(f"unexpected fake tag command: {args}")

    try:
        module.run_text = fake_tag_run_text
        tag_object, tag_commit = module.require_remote_tag_matches("origin", "v-test", "commit-object")
        require(tag_object == "tag-object", "remote release helper returned unexpected tag object")
        require(tag_commit == "commit-object", "remote release helper returned unexpected peeled commit")

        def fake_lightweight_run_text(args: list[str], *, timeout: int = 60) -> str:
            if args == ["git", "cat-file", "-t", "refs/remotes/origin/tags/v-test"]:
                return "commit"
            raise AssertionError(f"unexpected fake lightweight command: {args}")

        module.run_text = fake_lightweight_run_text
        try:
            module.require_remote_tag_matches("origin", "v-test", "commit-object")
        except module.RemoteReleaseError as exc:
            require("must be an annotated tag" in str(exc), "remote release helper rejected lightweight tag with unexpected message")
        else:
            raise CheckFailure("remote release helper must reject lightweight release tags")

        def fake_wrong_commit_run_text(args: list[str], *, timeout: int = 60) -> str:
            if args == ["git", "cat-file", "-t", "refs/remotes/origin/tags/v-test"]:
                return "tag"
            if args == ["git", "rev-parse", "refs/remotes/origin/tags/v-test"]:
                return "tag-object"
            if args == ["git", "rev-parse", "refs/remotes/origin/tags/v-test^{}"]:
                return "other-commit"
            raise AssertionError(f"unexpected fake wrong-commit command: {args}")

        module.run_text = fake_wrong_commit_run_text
        try:
            module.require_remote_tag_matches("origin", "v-test", "commit-object")
        except module.RemoteReleaseError as exc:
            require("does not peel to local HEAD" in str(exc), "remote release helper rejected wrong tag commit with unexpected message")
        else:
            raise CheckFailure("remote release helper must reject tags that do not peel to local HEAD")
    finally:
        module.run_text = original_run_text

    module.verify_forbidden_paths("verifier good remote tree", ["app/build/outputs/bundle/release/app-release.aab"], module.MAIN_FORBIDDEN_PATTERNS)
    module.verify_expected_aab_paths("verifier good remote tree", ["app/build/outputs/bundle/release/app-release.aab"])
    try:
        module.verify_expected_aab_paths(
            "verifier bad remote tree",
            ["app/build/outputs/bundle/release/app-release.aab", "release/extra.aab"],
        )
    except module.RemoteReleaseError as exc:
        require("unexpected AAB paths" in str(exc), "remote release helper rejected extra AAB with unexpected message")
    else:
        raise CheckFailure("remote release helper must reject unexpected remote AAB paths")
    forbidden_remote_path_cases = [
        "private/signing/qgrid-upload.p12",
        "PRIVATE/signing/QGRID-UPLOAD.P12",
        "release/upload.jks",
        "release/UPLOAD.JKS",
        "release/upload.keystore",
        "release/UPLOAD.KEYSTORE",
        "release/upload.pem",
        "release/UPLOAD.PEM",
        "release/upload.pk8",
        "release/UPLOAD.PK8",
        "release/upload.key",
        "release/UPLOAD.KEY",
        "app-release.apk",
        "APP-RELEASE.APK",
        "bundle.apks",
        "BUNDLE.APKS",
        "artifact.idsig",
        "ARTIFACT.IDSIG",
    ]
    for forbidden_path in forbidden_remote_path_cases:
        try:
            module.verify_forbidden_paths("verifier bad remote tree", [forbidden_path], module.MAIN_FORBIDDEN_PATTERNS)
        except module.RemoteReleaseError as exc:
            require("forbidden signing/install paths" in str(exc), f"remote release helper rejected {forbidden_path} with unexpected message")
        else:
            raise CheckFailure(f"remote release helper must reject forbidden remote path: {forbidden_path}")


def check_signing_backup_helper() -> None:
    helper = require_file("tools/check_signing_backup_inputs.py")
    require(os.access(helper, os.X_OK), "tools/check_signing_backup_inputs.py must be executable")
    require_text_markers(
        "tools/check_signing_backup_inputs.py",
        [
            "Check local signing inputs before the owner makes a secure backup.",
            "never prints password values",
            "ACTIVE_KEYSTORE = ROOT / \"private/signing/qgrid-upload.p12\"",
            "LEGACY_KEYSTORE = ROOT / \"private/signing/line56-upload.p12\"",
            "KEYSTORE_PROPERTIES = ROOT / \"keystore.properties\"",
            "EXPECTED_ALIAS = \"qgrid_upload\"",
            "def check_owner_only_file(",
            "mode & 0o077 == 0",
            "def parse_properties(",
            "def validate_properties(",
            "\"storeFile\", \"storePassword\", \"keyAlias\", \"keyPassword\"",
            "keystore.properties storeFile must point to private/signing/qgrid-upload.p12",
            "keystore.properties must not point to the legacy obvious signing file",
            "storePassword/keyPassword present, values hidden",
            "signing_backup_input_check",
            "signing_backup_input_ok",
            "signing_backup_input_error",
        ],
    )
    output = subprocess.check_output(
        [str(helper)],
        cwd=ROOT,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require("signing_backup_input_check" in output, "signing backup helper did not print check header")
    require(
        "active upload keystore: private/signing/qgrid-upload.p12 (mode 0o600)" in output,
        "signing backup helper did not prove the active keystore path and owner-only 0o600 mode",
    )
    require(
        "signing properties: keystore.properties (mode 0o600; storePassword/keyPassword present, values hidden)" in output,
        "signing backup helper did not prove keystore.properties owner-only 0o600 mode with hidden password values",
    )
    require("store file target: private/signing/qgrid-upload.p12" in output, "signing backup helper did not print active storeFile target")
    require("key alias: qgrid_upload" in output, "signing backup helper did not print alias")
    require(
        "legacy signing file: private/signing/line56-upload.p12 (mode 0o600; ignored, not active)" in output,
        "signing backup helper did not prove the legacy signing file is owner-only and inactive",
    )
    require("values hidden" in output, "signing backup helper must state password values are hidden")
    require("signing_backup_input_ok" in output, "signing backup helper did not finish with signing_backup_input_ok")

    spec = importlib.util.spec_from_file_location("line56_signing_backup_inputs", helper)
    require(spec is not None and spec.loader is not None, "signing backup helper could not be loaded for regression checks")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    temp_path = ROOT / "build/verification/signing_backup_world_readable.tmp"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text("not a key", encoding="utf-8")
    temp_path.chmod(0o644)
    try:
        try:
            module.check_owner_only_file(temp_path, "verifier temp signing file")
        except module.SigningBackupInputError as exc:
            require("must not be group/world readable or writable" in str(exc), f"signing helper rejected unsafe file mode with unexpected message: {exc}")
        else:
            raise CheckFailure("signing helper must reject group/world-readable signing files")
    finally:
        temp_path.chmod(0o600)
        temp_path.unlink()

    good_properties = {
        "storeFile": "private/signing/qgrid-upload.p12",
        "storePassword": "hidden",
        "keyAlias": "qgrid_upload",
        "keyPassword": "hidden",
    }
    module.validate_properties(good_properties)
    for bad_properties, expected_message in [
        ({key: value for key, value in good_properties.items() if key != "keyPassword"}, "must contain non-empty keyPassword"),
        ({**good_properties, "storeFile": "private/signing/line56-upload.p12"}, "storeFile must point to private/signing/qgrid-upload.p12"),
        ({**good_properties, "keyAlias": "line56_upload"}, "must use keyAlias=qgrid_upload"),
    ]:
        try:
            module.validate_properties(bad_properties)
        except module.SigningBackupInputError as exc:
            require(expected_message in str(exc), f"signing helper rejected bad properties with unexpected message: {exc}")
        else:
            raise CheckFailure(f"signing helper must reject bad signing properties: {bad_properties}")


def check_signing_backup_evidence_handoff() -> None:
    require_text_markers(
        "play_store/signing_backup_evidence_ru.md",
        [
            "Signing Backup Evidence - RU",
            "owner-controlled backup перед Google Play upload",
            "не доказываются локальным репозиторием",
            "Не записывать сюда пароли, private keys, keystore contents",
            "Active upload keystore: `private/signing/qgrid-upload.p12`.",
            "Signing credentials file: `keystore.properties`.",
            "Active key alias: `qgrid_upload`.",
            "Public certificate reference: `play_store/signing_certificate_report.md`.",
            "Legacy ignored local key: `private/signing/line56-upload.p12`",
            "./tools/check_signing_backup_inputs.py",
            "Latest local preflight, checked on 6 June 2026:",
            "Command returned `signing_backup_input_ok`.",
            "Active upload keystore exists and is owner-only: `private/signing/qgrid-upload.p12`, mode `0o600`.",
            "`keystore.properties` exists and is owner-only: mode `0o600`.",
            "`keystore.properties` points to `private/signing/qgrid-upload.p12`: `private/signing/qgrid-upload.p12`.",
            "`keystore.properties` uses key alias `qgrid_upload`: `qgrid_upload`.",
            "`storePassword` and `keyPassword` fields are present; values were not printed or recorded: present; values were not printed and not recorded.",
            "Legacy ignored local key exists and is owner-only: `private/signing/line56-upload.p12`, mode `0o600`; ignored, not active.",
            "Expected owner-side backup result:",
            "Backup completed before Play upload: not yet available locally.",
            "Secure owner-controlled storage type chosen: not yet available locally.",
            "At least two owner-controlled secure copies exist: not yet available locally.",
            "Recovery tested without exposing secrets: not yet available locally.",
            "For secure copies, use wording like `yes, two owner-controlled secure copies exist`.",
            "For recovery, use wording like `yes, recovery tested without exposing secrets`.",
            "Fewer than two owner-controlled secure backup copies exist.",
            "Recovery has not been tested without exposing secrets.",
            "Stop the Play upload until resolved",
            "Do not copy passwords, keystore contents, private keys or storage access details.",
        ],
    )


def check_play_console_submission_handoff() -> None:
    require_text_markers(
        "play_store/play_console_submission_ru.md",
        [
            "Package name: `com.qgrid.mobile`",
            "Version code: `1`",
            "Version name: `1.0.0`",
            "App name: `Линия 56`",
            "Default language: Russian (`ru-RU`)",
            "App or game: Game",
            "Category: Puzzle",
            "Monetization: free, no ads, no in-app purchases",
            "`play_store/owner_release_inputs.md`",
            "Use `play_store/upload_runbook_ru.md` for the final manual upload sequence",
            "App bundle: `app/build/outputs/bundle/release/app-release.aab`",
            "Release package/version: `com.qgrid.mobile`, versionCode `1`, versionName `1.0.0`",
            "Store icon: `play_store/icon/play_icon_512.png`",
            "Feature graphic: `play_store/feature_graphic.png`",
            "Phone screenshots:",
            "Large/tablet screenshots:",
            "`play_store/screenshots/phone/01_onboarding.png`",
            "`play_store/screenshots/phone/02_home.png`",
            "`play_store/screenshots/phone/03_game_start.png`",
            "`play_store/screenshots/phone/04_game_line.png`",
            "`play_store/screenshots/phone/05_settings.png`",
            "`play_store/screenshots/tablet/01_onboarding.png`",
            "`play_store/screenshots/tablet/02_home.png`",
            "`play_store/screenshots/tablet/03_game_start.png`",
            "`play_store/screenshots/tablet/04_game_line.png`",
            "`play_store/screenshots/tablet/05_settings.png`",
            "Privacy policy: required.",
            "Data collection: no collected user data.",
            "Data sharing: no shared user data.",
            "Analytics: none.",
            "Crash reporting: none.",
            "Encryption in transit: no user data is transmitted by the app.",
            "Account deletion: not applicable, app has no accounts.",
            "AI-generated content disclosure: not applicable to in-app user experience",
            "Content Rating Posture",
            "Target Audience Decision",
            "Resolve owner inputs from `play_store/owner_release_inputs.md`.",
            "Fill the Play Console support/contact fields used by the privacy policy inquiry mechanism.",
            "Publish the privacy policy on a public HTTPS URL.",
            "Back up `private/signing/qgrid-upload.p12` and `keystore.properties` before upload.",
            "Run required internal/closed testing tracks for the publisher account type.",
            "Re-run `./tools/run_final_local_gate.py` and require `final_local_gate_ok` immediately before uploading.",
        ],
    )


def check_app_content_answers_handoff() -> None:
    require_text_markers(
        "play_store/app_content_answers_ru.md",
        [
            "Final submission still depends on the publisher account, real privacy-policy URL and account-specific testing requirements.",
            "Restricted access: No.",
            "Login required: No.",
            "Paid access required: No.",
            "The app is fully usable offline after launch.",
            "Contains ads: No.",
            "Ad SDKs: None.",
            "Ad ID usage: No.",
            "Privacy policy required: Yes.",
            "hosted at a public HTTPS URL and the Play Console support/contact fields used by the policy inquiry mechanism are filled with a real support contact.",
            "no user data collection, no sharing, no ads, no analytics, no crash reporting SDK, no accounts, no payments, Android backup disabled.",
            "Does the app collect or share any required user data types: No.",
            "User data collected: none.",
            "User data shared: none.",
            "Data encrypted in transit: No user data is transmitted by the app.",
            "Local-only data: onboarding flag, completed level ids, last level id and settings for haptics, high contrast and reduced motion.",
            "Third-party SDK data: none beyond AndroidX/Compose runtime libraries",
            "Rating category: Games.",
            "Game type: Puzzle / logic / numeric puzzle.",
            "Violence: No.",
            "Fear, shock or horror: No.",
            "Sexual content or nudity: No.",
            "Gambling, simulated gambling or betting: No.",
            "Real-money purchases or paid random items: No.",
            "User-generated content: No.",
            "User-to-user communication: No.",
            "Online gameplay or online interaction: No.",
            "Target age groups: 13-15, 16-17, 18 and over.",
            "Do not select: 5 and under, 6-8, 9-12.",
            "Designed for children: No.",
            "Families program: Do not enroll unless the publisher intentionally prepares a child-directed release path.",
            "Financial products or services: No.",
            "Health or medical features: No.",
            "Government affiliation or government services: No.",
            "In-app generative AI features: No.",
            "Store creative note: `play_store/feature_graphic.png` uses a static generated background source documented in the asset manifest",
            "Category: Puzzle.",
            "Avoid tags or claims: casino, gambling, betting, money, education for children, school, kids, multiplayer, online.",
            "First upload target: Internal testing.",
            "Personal account created after 13 November 2023: plan for at least 12 opted-in testers for 14 continuous days before production availability.",
            "Production rollout: only after Play Console policy forms, generated artifact review, privacy URL and testing track requirements are complete.",
        ],
    )


def check_content_rating_notes_handoff() -> None:
    require_text_markers(
        "play_store/content_rating_notes.md",
        [
            "Expected category: Games / Puzzle.",
            "Use this as the local handoff for the Play Console content-rating questionnaire.",
            "Violence: none.",
            "Fear, shock or horror: none.",
            "Sexual content or nudity: none.",
            "Crude humor: none.",
            "Profanity or offensive language: none.",
            "Drugs, alcohol or tobacco: none.",
            "Gambling, simulated gambling or betting: none.",
            "Real-money purchases, in-app purchases or paid random items: none.",
            "User-generated content: none.",
            "User-to-user communication: none.",
            "Location sharing: none.",
            "Online gameplay or online interaction: none.",
            "Unrestricted web access: none.",
            "Personal data sharing: none.",
            "The game is a quiet offline numeric puzzle.",
            "selecting neighboring numbered cells to reach the target sum 56",
            "There are no social, political, medical, financial, adult, gambling, real-money, UGC, chat, leaderboard, online multiplayer or external-link mechanics.",
            "select `13-15`, `16-17`, and `18 and over`",
            "do not select child age groups unless the publisher intentionally prepares a Families-policy path",
            "Store copy avoids kids/school/child-directed claims, mascots, ads and purchases.",
            "`app/src/main/AndroidManifest.xml` has no `INTERNET` or `ACCESS_NETWORK_STATE` permission.",
            "`app/build.gradle.kts` has no ads, billing, analytics, crash reporting, auth/location Play Services, backend client, network client or image-loading SDK.",
            "`play_store/app_content_answers_ru.md` contains the field-by-field App content answers.",
            "`play_store/data_safety_ru.md` and `docs/privacy_and_permissions.md` document no data collection or sharing.",
        ],
    )


def check_owner_release_inputs() -> None:
    require_text_markers(
        "play_store/owner_release_inputs.md",
        [
            "Production package: `com.qgrid.mobile`.",
            "Debug package: `com.qgrid.mobile.debug`.",
            "Upload version for this release candidate: versionCode `1`, versionName `1.0.0`.",
            "App name: `Линия 56`.",
            "Default language: Russian (`ru-RU`).",
            "App type/category: Game / Puzzle.",
            "Monetization: free, no ads, no in-app purchases.",
            "Data Safety posture: no user data collected, no user data shared.",
            "select `13-15`, `16-17`, and `18 and over`",
            "do not select child age groups",
            "Support contact",
            "Working owner email or support website URL",
            "Privacy policy URL",
            "Public HTTPS URL, accessible without login, no credentials/query/fragments, not PDF, not editable by readers",
            "Signing backup",
            "Secure owner-controlled backup of `private/signing/qgrid-upload.p12` and `keystore.properties` after `./tools/check_signing_backup_inputs.py` returns `signing_backup_input_ok`",
            "record two owner-controlled secure copies and recovery tested without exposing secrets",
            "`play_store/signing_backup_evidence_ru.md`",
            "Play account testing path",
            "closed testing with 12 opted-in testers for 14 continuous days if required by account type",
            "Final generated-artifact review",
            "APK signature/certificate fingerprint",
            "manifest privacy/debug posture",
            "Upload Execution",
            "Use `play_store/upload_runbook_ru.md` as the owner-facing sequence for the upload day.",
            "Do Not Upload list, release-track order, stop conditions and post-upload evidence to record.",
            "After upload, use `play_store/play_console_post_upload_evidence_ru.md` to record only safe external facts",
            "Before upload, use `play_store/signing_backup_evidence_ru.md` to record only safe owner-side backup facts.",
            "Do not record secrets or tester personal data.",
            "Do Not Change Without Rebuilding And Rechecking",
            "`applicationId` / package name.",
            "AAB signing key, alias or keystore path.",
            "Privacy/data-safety posture.",
            "Target audience posture.",
            "./gradlew test lint assembleDebug assembleDebugAndroidTest bundleRelease",
            "./tools/verify_release.py",
            "./gradlew connectedDebugAndroidTest",
            "publication is still blocked externally",
        ],
    )


def check_post_upload_evidence_handoff() -> None:
    require_text_markers(
        "play_store/play_console_post_upload_evidence_ru.md",
        [
            "Play Console Post-Upload Evidence - RU",
            "безопасной фиксации внешних Play Console фактов после upload",
            "не доказываются локальным репозиторием",
            "Не записывать сюда пароли, private keys, keystore contents",
            "персональные данные тестеров",
            "Uploaded package name: not yet available locally; must be `com.qgrid.mobile`.",
            "Uploaded version code: not yet available locally; must be `1`.",
            "Uploaded version name: not yet available locally; must be `1.0.0`.",
            "Uploaded AAB SHA-256: not yet available locally; compare with `play_store/upload_checksums.md`.",
            "Public privacy policy URL: https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html.",
            "Privacy policy URL check command returned `privacy_policy_url_ok`: privacy_policy_url_ok.",
            "Privacy policy URL is HTTPS: yes.",
            "Privacy policy URL is accessible without login: yes.",
            "Privacy policy URL is not PDF: yes.",
            "Play Console support/contact field populated: not yet available locally.",
            "Support/contact mechanism matches `play_store/privacy_policy_ru.html`: not yet available locally.",
            "After entering the privacy policy URL, keep support/contact evidence explicit and do not use a bare `yes`",
            "the mechanism line must mention the Google Play listing support contact and the privacy policy.",
            "Signing backup evidence file: `play_store/signing_backup_evidence_ru.md`.",
            "Signing backup input check command returned `signing_backup_input_ok`: recorded locally on 6 June 2026.",
            "Active upload keystore backed up before AAB upload: not yet available locally.",
            "Owner-controlled backup evidence recorded without secrets: not yet available locally.",
            "After the real backup is complete, keep the backup evidence line explicit and safe, for example: `yes, recorded without secrets`.",
            "The active-keystore backup line must explicitly mention `private/signing/qgrid-upload.p12` and `before AAB upload`",
            "Play-generated APK verification command: run `./tools/verify_play_generated_apk.py --apk <path-to-play-generated.apk>` on a downloaded Play-generated APK artifact and require `play_generated_apk_verify_ok`.",
            "Play-generated APK package is `com.qgrid.mobile`: not yet available locally.",
            "Play-generated APK signature verifies and certificate SHA-256 recorded: not yet available locally.",
            "Play-generated app label is `Линия 56`: not yet available locally.",
            "Play-generated icon matches `play_store/icon/play_icon_512.png`: not yet available locally.",
            "Play-generated permissions review shows no `INTERNET`, no `ACCESS_NETWORK_STATE` and no dangerous runtime permissions: not yet available locally.",
            "Play-generated manifest privacy review shows `allowBackup=false` and no debuggable release manifest: not yet available locally.",
            "Play-generated native libraries support 16 KB page sizes: not yet available locally.",
            "After Play-generated artifact review, the icon line must be based on helper output `store icon pixel matches: ...`, `application icon linked store icon: ...` and `round icon linked store icon: ...`",
            "The signature line must explicitly include `verified`, `SHA-256` and the signer certificate SHA-256 fingerprint",
            "The icon line must explicitly mention application-icon-linked and round-icon-linked store-icon pixel matches.",
            "The version line must explicitly include `versionCode 1` and `versionName 1.0.0`",
            "After Play-generated artifact review, the permissions line must explicitly include `no INTERNET`, `no ACCESS_NETWORK_STATE` and `no dangerous runtime permissions`.",
            "The manifest privacy line must explicitly include `allowBackup=false` and `no debuggable`",
            "The native-library line must explicitly include `16 KB`, `16384`, `uncompressed`, `ZIP-aligned` and `extractNativeLibs=false`",
            "The install/launch line must explicitly say the Play-generated APK was `installed` and `launched` on an Android device or Android emulator",
            "App access completed as no restricted access/login/account: not yet available locally.",
            "Ads declaration completed as no ads: not yet available locally.",
            "Data Safety completed as no user data collected or shared: not yet available locally.",
            "Content rating completed as Games / Puzzle posture: not yet available locally.",
            "Target audience completed as non-child-directed 13+ posture unless publisher intentionally chose a child-directed path: not yet available locally.",
            "AI disclosure completed as no in-app generative AI features: not yet available locally.",
            "After completing Policy Forms, keep the evidence explicit and do not use a bare `yes`",
            "Data Safety must mention `no user data collected` and `no user data shared`",
            "target audience must mention `13+` and `non-child-directed`",
            "AI disclosure must mention `no in-app generative AI features`.",
            "Internal testing upload completed: not yet available locally.",
            "Closed testing required for this account: not yet available locally.",
            "Closed testing status if required: not yet available locally.",
            "Pre-launch report result: not yet available locally.",
            "Reproducible crashes in pre-launch report: not yet available locally.",
            "Play policy warnings: not yet available locally.",
            "Store listing preview checked for damaging image crops: not yet available locally.",
            "After store-listing preview review, the preview-crop line must explicitly mention the icon, feature graphic, phone screenshots, tablet screenshots and `no damaging crops`",
            "Stop production rollout and return to local rebuild/recheck",
            "package `com.qgrid.mobile`",
            "versionCode `1` and versionName `1.0.0`",
            "no-data/no-network/no-ads/no-payments/no-accounts posture",
            "Do not copy secrets or tester personal data.",
        ],
    )


def check_upload_checksums() -> None:
    checksum_path = "play_store/upload_checksums.md"
    require(
        "Verified for the current local release candidate after the ImageGen icon/onboarding brand-mark alignment, Play screenshot aspect-ratio normalization, system-bar crop and git/VCS metadata refresh" in read(checksum_path),
        "upload checksums must mention icon/onboarding alignment, screenshot normalization, system-bar crop and git/VCS metadata refresh",
    )
    expected_paths = {
        "app/build/outputs/bundle/release/app-release.aab",
        "play_store/icon/play_icon_512.png",
        "play_store/feature_graphic.png",
        "play_store/screenshots/phone/01_onboarding.png",
        "play_store/screenshots/phone/02_home.png",
        "play_store/screenshots/phone/03_game_start.png",
        "play_store/screenshots/phone/04_game_line.png",
        "play_store/screenshots/phone/05_settings.png",
        "play_store/screenshots/tablet/01_onboarding.png",
        "play_store/screenshots/tablet/02_home.png",
        "play_store/screenshots/tablet/03_game_start.png",
        "play_store/screenshots/tablet/04_game_line.png",
        "play_store/screenshots/tablet/05_settings.png",
    }
    rows: dict[str, tuple[int, str]] = {}
    for line in read(checksum_path).splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        require(len(parts) == 3, f"bad upload checksum row: {line}")
        path = parts[0].strip("`")
        byte_count_text = parts[1]
        sha256 = parts[2].strip("`")
        require(byte_count_text.isdigit(), f"bad byte count for {path}: {byte_count_text}")
        require(re.fullmatch(r"[0-9a-f]{64}", sha256), f"bad SHA-256 for {path}: {sha256}")
        require(path not in rows, f"duplicate checksum row for {path}")
        rows[path] = (int(byte_count_text), sha256)

    require(set(rows) == expected_paths, f"upload checksums path mismatch: {sorted(set(rows) ^ expected_paths)}")
    for path, (expected_size, expected_sha256) in rows.items():
        file_path = require_file(path)
        data = file_path.read_bytes()
        require(len(data) == expected_size, f"{path}: checksum manifest byte count {expected_size}, got {len(data)}")
        actual_sha256 = hashlib.sha256(data).hexdigest()
        require(actual_sha256 == expected_sha256, f"{path}: checksum manifest SHA-256 mismatch")


def check_alt_text() -> None:
    text = read("play_store/asset_alt_text_ru.md")
    rows = [line for line in text.splitlines() if line.startswith("| `")]
    require(rows, "alt text table is empty")
    for row in rows:
        parts = [part.strip() for part in row.strip("|").split("|")]
        require(len(parts) == 2, f"bad alt text row: {row}")
        asset = parts[0].strip("`")
        alt_text = parts[1]
        require((ROOT / asset).exists(), f"alt text asset does not exist: {asset}")
        require(len(alt_text) <= 140, f"alt text too long for {asset}: {len(alt_text)}")


def check_privacy_html() -> None:
    path = require_file("play_store/privacy_policy_ru.html")
    parser = HTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    text = path.read_text(encoding="utf-8")
    source = read("play_store/privacy_policy_ru.md")
    hosting = read("play_store/privacy_policy_hosting_checklist.md")

    for marker in [
        "Дата: 6 июня 2026",
        "не собирает, не передаёт и не продаёт персональные данные пользователя",
        "факт прохождения первого экрана с правилами",
        "список пройденных уровней",
        "последний выбранный уровень",
        "настройки интерфейса и тактильного отклика",
        "не отправляются за пределы устройства",
        "Android backup для приложения отключён",
        "аккаунты",
        "рекламу",
        "аналитику",
        "платежи",
        "идентификаторы устройства",
        "пользовательский контент",
        "Игра работает без обязательного подключения к интернету",
        "очистив данные приложения в настройках Android или удалив приложение",
        "По вопросам конфиденциальности используйте контакт поддержки разработчика",
        "указанный на странице приложения «Линия 56» в Google Play",
        "официальный канал для вопросов о локальных данных, удалении данных и политике конфиденциальности",
    ]:
        require(marker in source, f"privacy policy markdown missing marker: {marker}")

    for marker in [
        "Дата: 6 июня 2026 года",
        "не собирает, не передаёт и не продаёт персональные данные пользователя",
        "факт прохождения первого экрана с правилами",
        "список пройденных уровней",
        "последний выбранный уровень",
        "настройки интерфейса и тактильного отклика",
        "не отправляются за пределы устройства",
        "Android backup для приложения отключён",
        "аккаунты",
        "рекламу",
        "аналитику",
        "платежи",
        "идентификаторы устройства",
        "пользовательский контент",
        "Игра работает без обязательного подключения к интернету",
        "очистив данные приложения в настройках Android или удалив приложение",
        "По вопросам конфиденциальности используйте контакт поддержки разработчика",
        "указанный на странице приложения «Линия 56» в Google Play",
        "официальный канал для вопросов о локальных данных, удалении данных и политике конфиденциальности",
    ]:
        require(marker in text, f"privacy policy HTML missing marker: {marker}")

    for marker in [
        "URL must be public and accessible without login.",
        "URL must use HTTPS.",
        "URL must not include credentials, query parameters or fragments.",
        "URL host must be a real public domain, not a placeholder/reserved host, and DNS must resolve only to public global IP addresses.",
        "Page must show the app name: `Линия 56`.",
        "Page must include developer information and a privacy point of contact or a mechanism to submit inquiries.",
        "Page contact mechanism must not point to an empty placeholder.",
        "Page content must match the app behavior: no data collection, no sharing, no ads, no analytics, no payments, Android backup disabled.",
        "Hosted page text must match the current normalized text of `play_store/privacy_policy_ru.html`; do not edit the hosted copy separately.",
        "Hosted page must not inject scripts, trackers, iframes, cookie logic or external widgets into the policy body.",
        "Policy source text is hosted at `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` and passed `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` on 2026-06-11.",
        "Populated Play Console support/contact fields remain a manual release blocker because they are external to the local codebase.",
        "Run `./tools/check_privacy_policy_url.py --url <https-url>` and require `privacy_policy_url_ok`; the helper also checks valid UTF-8, HTML content, public HTTPS, no credentials/query/fragments, no placeholder/reserved host, public-global DNS resolution, non-PDF final URL, exact normalized-text match with `play_store/privacy_policy_ru.html` and no script/tracker/widget markers.",
        "./tools/check_privacy_policy_url.py --local",
    ]:
        require(marker in hosting, f"privacy hosting checklist missing marker: {marker}")

    require("Android backup" in text, "privacy HTML must mention Android backup")
    require("contact-block" in text, "privacy HTML must keep a styled contact/inquiry block")
    forbidden_policy_markers = [
        "contact-required",
        "Перед публикацией владелец приложения должен заменить",
        "Не публикуйте эту HTML-страницу",
        "незаполненным контактным блоком",
        "placeholder",
    ]
    for marker in forbidden_policy_markers:
        require(marker not in source, f"privacy policy markdown still contains placeholder marker: {marker}")
        require(marker not in text, f"privacy policy HTML still contains placeholder marker: {marker}")


def require_text_markers(path: str, markers: list[str]) -> None:
    text = read(path)
    for marker in markers:
        require(marker in text, f"{path} missing required privacy/safety marker: {marker}")


def check_privacy_safety_handoff() -> None:
    require_text_markers(
        "play_store/data_safety_ru.md",
        [
            "Данные пользователя не собираются.",
            "Данные не передаются третьим лицам.",
            "не покидают устройство",
            "Нет сетевой передачи пользовательских данных.",
            "Manifest не запрашивает `INTERNET` или `ACCESS_NETWORK_STATE`.",
            "Нет аккаунтов, аналитики, рекламы, платежей, crash reporting SDK или device identifiers.",
        ],
    )
    require_text_markers(
        "docs/privacy_and_permissions.md",
        [
            "Приложение не собирает персональные данные.",
            "Локально сохраняются только:",
            "факт прохождения onboarding",
            "список пройденных уровней",
            "последний уровень",
            "настройки haptics/high contrast/reduce motion",
            "Android backup отключён в manifest через `android:allowBackup=\"false\"`",
            "Manifest не запрашивает dangerous/platform runtime permissions.",
            "`INTERNET` и `ACCESS_NETWORK_STATE` также не запрашиваются",
            "единственный `uses-permission` в debug APK - generated `com.qgrid.mobile.debug.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`",
            "Analytics: нет.",
            "Crash logs: нет.",
            "Ads: нет.",
            "Payments/IAP: нет.",
            "Accounts: нет.",
            "Device identifiers: нет.",
            "User-generated content: нет.",
            "Можно указать: данные не собираются и не передаются третьим лицам.",
            "uses the Google Play listing support contact as the privacy inquiry mechanism",
            "Перед публикацией владелец должен ввести verified hosted URL в Play Console and заполнить рабочий support contact в Play Console.",
            "In-app About/privacy copy also states the local privacy posture in short scannable points",
            "`tools/verify_release.py` gates these key Android string markers.",
            "Signing passwords and the upload keystore remain only in ignored local files or owner-controlled environment variables.",
            "ads, analytics, crash SDKs, billing, auth/location Play Services, backend/network clients and image-loading SDKs are blocked",
        ],
    )
    require_text_markers(
        "play_store/play_console_submission_ru.md",
        [
            "Data collection: no collected user data.",
            "Data sharing: no shared user data.",
            "Analytics: none.",
            "Crash reporting: none.",
            "Ads: no.",
            "Account deletion: not applicable, app has no accounts.",
            "Encryption in transit: no user data is transmitted by the app.",
        ],
    )
    require_text_markers(
        "play_store/app_content_answers_ru.md",
        [
            "Restricted access: No.",
            "Contains ads: No.",
            "Does the app collect or share any required user data types: No.",
            "User data collected: none.",
            "User data shared: none.",
            "Data encrypted in transit: No user data is transmitted by the app.",
            "Users can request data deletion: Not applicable; the app has no accounts and does not collect user data.",
            "Rating category: Games.",
            "Game type: Puzzle / logic / numeric puzzle.",
            "Gambling, simulated gambling or betting: No.",
            "User-generated content: No.",
            "Online gameplay or online interaction: No.",
            "Target age groups: 13-15, 16-17, 18 and over.",
            "Designed for children: No.",
            "Financial products or services: No.",
            "Health or medical features: No.",
            "Government affiliation or government services: No.",
            "In-app generative AI features: No.",
            "Personal account created after 13 November 2023: plan for at least 12 opted-in testers for 14 continuous days before production availability.",
        ],
    )
    require_text_markers(
        "play_store/content_rating_notes.md",
        [
            "Expected category: Games / Puzzle.",
            "Violence: none.",
            "Fear, shock or horror: none.",
            "Sexual content or nudity: none.",
            "Profanity or offensive language: none.",
            "Drugs, alcohol or tobacco: none.",
            "Gambling, simulated gambling or betting: none.",
            "Real-money purchases, in-app purchases or paid random items: none.",
            "User-generated content: none.",
            "User-to-user communication: none.",
            "Location sharing: none.",
            "Online gameplay or online interaction: none.",
            "Unrestricted web access: none.",
            "Personal data sharing: none.",
        ],
    )


def check_signing_certificate_report() -> None:
    text = read("play_store/signing_certificate_report.md")
    expected_sha256 = "DD:97:1E:77:8A:0A:87:E7:9E:1A:44:18:1D:45:3B:83:80:7F:B3:06:FF:48:DE:AC:BA:FD:48:11:36:83:72:F1"
    require("Checked on 6 June 2026" in text, "signing report must show the latest 6 June 2026 check")
    require("qgrid_upload" in text, "signing report must include upload key alias")
    require("QuietGrid Upload" in text, "signing report must include QuietGrid certificate owner")
    require(
        "common signing-key extensions (`*.jks`, `*.keystore`, `*.pem`, `*.pk8`, `*.key`) and Android upload/install artifact extensions (`*.apk`, `*.aab`, `*.apks`, `*.idsig`) are ignored case-insensitively by `.gitignore`" in text,
        "signing report must document local ignore coverage for common signing-key and Android artifact extensions",
    )
    require(
        "`tools/verify_release.py` verifies representative lower/upper-case paths with `git check-ignore`" in text,
        "signing report must document semantic git check-ignore coverage",
    )
    require(
        "fails if forbidden sensitive/install paths are tracked in Git" in text,
        "signing report must document tracked forbidden-path coverage",
    )
    require(
        expected_sha256 in text,
        "signing report must include the upload certificate SHA-256 fingerprint",
    )
    aab = require_file("app/build/outputs/bundle/release/app-release.aab")
    keytool = resolve_keytool()
    cert_output = subprocess.check_output(
        [str(keytool), "-printcert", "-jarfile", str(aab)],
        stderr=subprocess.STDOUT,
        text=True,
    )
    require("Owner: CN=QuietGrid Upload" in cert_output, "release AAB certificate owner does not match signing report")
    require("Serial number: 719e6a96be867b6d" in cert_output, "release AAB certificate serial does not match signing report")
    require(f"SHA256: {expected_sha256}" in cert_output, "release AAB certificate SHA-256 does not match signing report")
    require("Signature algorithm name: SHA384withRSA" in cert_output, "release AAB signature algorithm does not match signing report")
    forbidden_secret_markers = [
        "storePassword",
        "keyPassword",
        "QGRID_STORE_PASSWORD",
        "QGRID_KEY_PASSWORD",
        "BEGIN PRIVATE KEY",
        "PRIVATE KEY-----",
    ]
    for marker in forbidden_secret_markers:
        require(marker not in text, f"signing report must not include secret marker: {marker}")


def markdown_sections(text: str, level: int) -> dict[str, str]:
    matches = list(re.finditer(rf"^(#{{1,{level}}})\s+(.+?)\s*$", text, re.M))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        if len(match.group(1)) != level:
            continue
        start = match.end()
        end = len(text)
        for next_match in matches[index + 1:]:
            if len(next_match.group(1)) <= level:
                end = next_match.start()
                break
        sections[match.group(2).strip()] = text[start:end].strip()
    return sections


def require_markdown_section(sections: dict[str, str], name: str, source: str) -> str:
    require(name in sections, f"missing {name!r} in {source}")
    value = sections[name].strip()
    require(value, f"empty {name!r} in {source}")
    return value


def check_store_metadata() -> None:
    listing_path = "play_store/listing_ru.md"
    submission_path = "play_store/play_console_submission_ru.md"
    listing = read(listing_path)
    submission = read(submission_path)
    listing_sections = markdown_sections(listing, 2)
    submission_sections = markdown_sections(submission, 3)
    limits = {
        "App Name": 30,
        "Short Description": 80,
        "Full Description": 4000,
        "Release Notes": 500,
    }

    for name, max_length in limits.items():
        value = require_markdown_section(listing_sections, name, listing_path)
        require(len(value) <= max_length, f"{name} too long in {listing_path}: {len(value)} > {max_length}")

        submission_value = require_markdown_section(submission_sections, name, submission_path)
        require(
            submission_value == value,
            f"{name} differs between {listing_path} and {submission_path}",
        )

    placeholder_patterns = [
        r"\bTODO\b",
        r"\blorem\b",
        r"\bplaceholder\b",
        r"contact-required",
        r"example\.com",
    ]
    for path, text in [(listing_path, listing), (submission_path, submission)]:
        for pattern in placeholder_patterns:
            require(re.search(pattern, text, re.I) is None, f"metadata placeholder marker {pattern!r} in {path}")


def check_no_forbidden_identifiers() -> None:
    forbidden = [
        "com.ivliev",
        "ivliev",
        "andrej",
        "com.quietgrid.lattice",
        "com/quietgrid/lattice",
        "com.quietgrid.numberpath",
        "com/quietgrid/numberpath",
        "numberpath",
    ]
    roots = ["README.md", "AGENTS.md", "docs", "play_store", "app/src/main", "app/build.gradle.kts"]
    for item in roots:
        path = ROOT / item
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
        for file_path in files:
            if file_path.suffix.lower() in {".png", ".p12", ".apk", ".aab", ".jar"}:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for needle in forbidden:
                require(needle not in text, f"forbidden identifier {needle!r} in {file_path.relative_to(ROOT)}")


def check_no_russian_literals_in_main_kotlin() -> None:
    pattern = re.compile(r'"[^"\n]*[\u0400-\u04ff][^"\n]*"')
    for file_path in (ROOT / "app/src/main/java").rglob("*.kt"):
        text = file_path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if match is not None:
            raise CheckFailure(f"Russian UI literal in {file_path.relative_to(ROOT)}: {match.group(0)}")


def check_game_model_validation_source() -> None:
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/game/Models.kt",
        [
            "Cell at index $index must have position",
            "Cell values must be positive.",
            "Board size must stay readable on phones.",
            "size in 4..6",
            "fun contains(position: CellPosition): Boolean",
            "fun parseCompletedLevelIds(raw: String?): Set<Int>",
            "fun serializedCompletedLevelIds(levelIds: Iterable<Int>): String",
            "val isNewCompletion = levelId !in sanitizedProgress.completedLevelIds",
            "lastLevelId = if (isNewCompletion)",
            "Level id must be within the released level set.",
            "Level size must match board size.",
            "Level solution path must not be empty.",
            "Level solution path must not repeat cells.",
            "Level solution path must use adjacent cells only.",
            "Level solution path must sum to the target.",
            "Game selection must not repeat cells.",
            "Game selection must use adjacent cells only.",
            "Game status must match selected sum.",
            "Hinted cell is only valid for active games.",
            "Hinted cell must stay inside the board.",
            "Hinted cell must not already be selected.",
            "Hinted cell must stay adjacent to the current line.",
            "Hinted cell must not overshoot the target.",
            "Hints used must not be negative.",
        ],
    )
    require_text_markers(
        "app/src/test/java/com/qgrid/mobile/game/LevelFactoryTest.kt",
        [
            "boardRejectsCellsThatDoNotMatchTheirGridPosition",
            "boardRejectsNonPositiveCellValues",
            "boardRejectsOversizedReleasedBoard",
            "createsThirtySixPlayableLevels",
            "assertEquals(36, levels.size)",
            "assertEquals((1..36).toList(), levels.map { it.id })",
            "generatedLevelsUseDocumentedDifficultyBoardSizesAndPathLengths",
            "everyCanonicalSolutionSumsToTarget",
            "solutionPathsUseAdjacentCellsOnly",
            "solverFindsReachableTargetOnEveryGeneratedBoard",
            "levelRejectsMismatchedBoardSize",
            "levelRejectsIdsOutsideReleasedSet",
            "levelRejectsEmptySolutionPath",
            "levelRejectsRepeatedSolutionCells",
            "levelRejectsNonAdjacentSolutionCells",
            "levelRejectsSolutionCellsOutsideBoard",
            "levelRejectsSolutionThatDoesNotReachTarget",
            "solverContinuesFromCurrentSelection",
            "solverReturnsNullWhenCurrentSelectionCannotReachTarget",
            "solverReturnsSelectedPathWhenCurrentSelectionAlreadyReachesTarget",
            "solverRejectsCurrentSelectionOutsideBoard",
            "solverRejectsRepeatedCurrentSelectionCells",
            "solverRejectsNonAdjacentCurrentSelectionCells",
            "LevelSolver.findPathFromSelection",
            "assertThrows(IllegalArgumentException::class.java)",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/data/ProgressRepository.kt",
        [
            "ProgressRules.parseCompletedLevelIds(preferences[Keys.COMPLETED_LEVELS])",
            "ProgressRules.serializedCompletedLevelIds(completed + levelId)",
            "levelId in 1..LEVEL_COUNT",
            "preferences[Keys.LAST_LEVEL_ID] = ProgressRules.sanitizedLastLevelId(levelId)",
            "fun clearLocalState()",
            "preferences.clear()",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/game/LevelSolver.kt",
        [
            "fun findPathFromSelection(",
            "Selected path must stay inside the board.",
            "Selected path must not repeat cells.",
            "Selected path must use adjacent cells only.",
            "selectedIndices.fold(0L)",
            "current = selectedIndices.last()",
        ],
    )
    require_text_markers(
        "app/src/test/java/com/qgrid/mobile/game/ProgressStateTest.kt",
        [
            "progressRulesParseCorruptedCompletedLevelCsv",
            "progressRulesSerializeCompletedLevelIdsInStableOrder",
            "progressRulesAddCompletedLevelWithoutLosingSettings",
            "progressRulesRecordNewCompletedLevelAsLastPlayed",
            "progressRulesIgnoreInvalidCompletedLevelWhenAddingOptimistically",
            "progressRulesTreatReplayedCompletedLevelAsIdempotent",
            "ProgressRules.withCompletedLevel",
            "not-a-level",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/game/GameReducer.kt",
        [
            "!state.level.board.contains(position)",
            "GameMessage.NOT_ON_BOARD",
            "LevelSolver.findPathFromSelection(",
            "GameMessage.HINT_REPAIR",
        ],
    )
    require_text_markers(
        "app/src/test/java/com/qgrid/mobile/game/GameReducerTest.kt",
        [
            "reducerRejectsCellOutsideBoardAtStart",
            "reducerRejectsCellOutsideBoardAfterSelection",
            "GameMessage.NOT_ON_BOARD",
            "hintPointsToReachableStart",
            "hintFollowsCurrentPlayableSelectionWhenItIsNotCanonicalPrefix",
            "hintAsksForRepairWhenCurrentSelectionCannotReachTarget",
            "GameMessage.HINT_REPAIR",
            "gameStateRejectsStatusThatDoesNotMatchCurrentSum",
            "gameStateRejectsInvalidSelectionShapeAndHintMetadata",
            "gameStateRejectsHintsThatCannotBePlayedFromCurrentSelection",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/ui/LevelNavigation.kt",
        [
            "val orderedLevels = levels.distinctBy { it.id }.sortedBy { it.id }",
            "val orderedLevelIds = levels.map { it.id }.distinct().sorted()",
            "orderedLevels.firstOrNull { it.id > levelId }",
            "if (currentLevelId == null) return orderedLevelIds.first()",
            "orderedLevelIds.firstOrNull { it > currentId }",
        ],
    )
    require_text_markers(
        "app/src/test/java/com/qgrid/mobile/ui/LevelNavigationTest.kt",
        [
            "levelForIdUsesAvailableLevelIdsWhenListIsSparseOrReordered",
            "nextLevelIdUsesAvailableLevelIdsWhenListIsSparseOrReordered",
            "levelForIdUsesDistinctAvailableIdsWhenListContainsDuplicates",
            "nextLevelIdUsesDistinctAvailableIdsWhenListContainsDuplicates",
            "sparseLevels",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/ui/AppState.kt",
        [
            "val displayLevels: List<LevelDefinition> = levels.distinctBy { it.id }.sortedBy { it.id }",
            "val gameReturnScreen: AppScreen = AppScreen.LEVELS",
            "val totalLevelCount: Int = orderedLevelIds.size",
            "private val hasLevels: Boolean = orderedLevelIds.isNotEmpty()",
            "val currentGameIsLastLevel: Boolean = gameState?.level?.id == orderedLevelIds.lastOrNull()",
            "val currentGameHasNumberedNextLevel: Boolean = gameState?.level?.id",
            "val currentGameNextLevelId: Int = gameState?.level?.id",
            "LevelNavigation.nextLevelId(levels, currentLevelId)",
            "val currentGameCompletesAllLevels: Boolean = hasLevels",
            "private val projectedCompletedLevelIds: Set<Int> = currentWonLevelId",
            "private val lastPlayedLevelId: Int? = progress.lastLevelId.takeIf { it in availableLevelIds }",
            "val availableLevelIds: Set<Int> = orderedLevelIds.toSet()",
            ").intersect(availableLevelIds)",
            "lastPlayedLevelId?.takeIf { it !in sanitizedCompletedLevelIds }",
            "orderedLevelIds.firstOrNull { it !in sanitizedCompletedLevelIds }",
            "val shouldShowContinueAction: Boolean = hasLevels",
        ],
    )
    require_text_markers(
        "app/src/test/java/com/qgrid/mobile/ui/AppUiStateTest.kt",
        [
            "nextLevelUsesLastPlayedLevelWhenItIsStillIncomplete",
            "nextLevelFallsBackToFirstIncompleteWhenLastPlayedLevelIsComplete",
            "startActionRemainsForFreshProgressOnFirstLevel",
            "emptyLevelListDoesNotExposeContinueAction",
            "continueActionShowsWhenFreshProgressStoppedOnLaterLevel",
            "completedCountUsesOnlyAvailableLevelIdsWhenListIsSparseOrReordered",
            "totalLevelCountUsesDistinctAvailableLevelIdsWhenListIsSparseOrReordered",
            "completedCountUsesDistinctAvailableLevelIdsWhenListContainsDuplicates",
            "nextLevelUsesSortedAvailableIdsWhenListIsSparseOrReordered",
            "nextLevelUsesDistinctAvailableIdsWhenListContainsDuplicates",
            "currentGameLastLevelUsesHighestAvailableLevelIdWhenListIsSparseOrReordered",
            "currentGameHasNumberedNextLevel",
            "currentGameNextLevelUsesGameStateLevelWhenCurrentLevelIsStale",
            "currentGameNextLevelFallsBackToContinueRouteWhenNoGameIsOpen",
            "currentGameDoesNotCompleteAllLevelsJustBecauseHighestLevelWasWon",
            "currentGameCompletesAllLevelsWhenLastMissingLevelIsWon",
            "currentGameCompletesAllLevelsUsesDistinctAvailableLevelIds",
            "completedLevelIds = setOf(1, 2, 3, 99)",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/ui/Line56App.kt",
        [
            "total = state.totalLevelCount",
            "R.string.progress_description",
            "ProgressBarRangeInfo(progressValue, 0f..1f)",
            "progressBarRangeInfo =",
            "drawStopIndicator = {}",
            "state.displayLevels.chunked(4)",
            "hasNextLevel = state.currentGameHasNumberedNextLevel",
            "allLevelsComplete = state.currentGameCompletesAllLevels",
            "onLevels = onLevels",
            "onReplay = viewModel::replayCurrentLevel",
            "onReplay = onReplay",
            "stringResource(R.string.back_to_levels)",
            "stringResource(R.string.replay_level)",
            "state.shouldShowContinueAction",
            "animateColorAsState(",
            "animateDpAsState(",
            "val animationDuration = if (settings.reduceMotion) 0 else 140",
            "val previousSelectedCount = remember(game.level.id) { mutableIntStateOf(selectedCount) }",
            "val previousStatus = remember(game.level.id) { mutableStateOf(game.status) }",
            "selectedCount > previousSelectedCount.intValue",
            "previousStatus.value != GameStatus.WON",
            "val handleCell: (CellPosition) -> Unit = onCell",
            "onBack = viewModel::openGameReturnScreen",
            "onLevels = viewModel::openLevels",
            "val useStackedLayout = maxWidth < 330.dp",
            ".verticalScroll(rememberScrollState())",
        ],
    )
    require_text_markers(
        "app/src/main/java/com/qgrid/mobile/ui/GameViewModel.kt",
        [
            "fun openGameReturnScreen()",
            "fun startLevelFromLevels(levelId: Int)",
            "private fun startLevel(levelId: Int, returnScreen: AppScreen)",
            "gameReturnScreen = returnScreen.safeGameReturnScreen()",
            "startLevel(_state.value.nextLevelId, AppScreen.HOME)",
            "startLevel(current.currentGameNextLevelId, current.gameReturnScreen)",
            "fun replayCurrentLevel()",
            "val level = current.gameState?.level ?: current.currentLevel ?: return",
            "gameState = GameReducer.newGame(level)",
            "val levelWasJustCompleted = currentGame.status != GameStatus.WON && nextGame.status == GameStatus.WON",
            "ProgressRules.withCompletedLevel(current.progress, nextGame.level.id)",
            "private fun AppScreen.safeGameReturnScreen(): AppScreen",
        ],
    )
    require_text_markers(
        "app/src/androidTest/java/com/qgrid/mobile/Line56AppSmokeTest.kt",
        [
            "onNodeWithContentDescription(\"Прогресс: 0 из 36 уровней.\")",
            "repository.setOnboardingSeen()",
            "composeRule.activityRule.scenario.recreate()",
            "hasText(\"Соединяйте соседние клетки\", substring = true)",
            "hasText(\"Можно двигаться\", substring = true)",
        ],
    )


def run_checks() -> None:
    checks = [
        check_build_config,
        check_tech_stack_handoff,
        check_discreet_package_identity,
        check_required_documents,
        check_agents_handoff,
        check_readme_handoff,
        check_google_play_sources,
        check_google_play_checklist_handoff,
        check_product_decision,
        check_product_spec_handoff,
        check_content_audit_handoff,
        check_ui_audit_handoff,
        check_accessibility_notes_handoff,
        check_requirements_traceability,
        check_release_plan_handoff,
        check_release_report_handoff,
        check_completion_audit_handoff,
        check_qa_test_plan_handoff,
        check_sensitive_files_ignored,
        check_no_committed_secret_values,
        check_manifest_source,
        check_android_string_resources,
        check_dependency_surface,
        check_merged_manifests_permissions,
        check_debug_apk_permissions,
        check_debug_manifest_binary,
        check_aab_signature,
        check_release_aab_clean,
        check_release_native_library_alignment,
        check_build_artifact_freshness,
        check_size_budgets,
        check_performance_notes,
        check_art_direction_handoff,
        check_store_assets,
        check_screenshot_manifest_handoff,
        check_asset_handoff,
        check_qa_artifacts,
        check_connected_report_evidence,
        check_publication_readiness_owner_actions_handoff,
        check_upload_manifest,
        check_upload_runbook_handoff,
        check_final_local_gate_runner,
        check_api36_connected_gate_helper,
        check_upload_packet_helper,
        check_store_asset_review_sheet_helper,
        check_play_upload_archive_helper,
        check_play_console_packet_helper,
        check_play_generated_apk_helper,
        check_publication_readiness_helper,
        check_privacy_policy_url_helper,
        check_remote_release_helper,
        check_signing_backup_helper,
        check_signing_backup_evidence_handoff,
        check_play_console_submission_handoff,
        check_app_content_answers_handoff,
        check_content_rating_notes_handoff,
        check_owner_release_inputs,
        check_post_upload_evidence_handoff,
        check_upload_checksums,
        check_alt_text,
        check_privacy_html,
        check_privacy_safety_handoff,
        check_signing_certificate_report,
        check_store_metadata,
        check_no_forbidden_identifiers,
        check_no_russian_literals_in_main_kotlin,
        check_game_model_validation_source,
    ]
    for check in checks:
        check()
        print(f"PASS {check.__name__}")
    print("release_verification_ok")


if __name__ == "__main__":
    try:
        run_checks()
    except (CheckFailure, subprocess.CalledProcessError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        sys.exit(1)
