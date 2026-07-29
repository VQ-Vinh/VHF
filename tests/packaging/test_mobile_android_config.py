import json
from pathlib import Path


def test_production_mobile_does_not_use_debug_signing() -> None:
    gradle = Path("apps/android/android/app/build.gradle").read_text(encoding="utf-8")
    assert "signingConfigs.debug" not in gradle
    assert "PRANA_ANDROID_KEYSTORE_PATH" in gradle
    assert "Production release signing is not configured" in gradle
    assert "throw new org.gradle.api.GradleException" in gradle


def test_mobile_signing_properties_are_ignored() -> None:
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "apps/android/android/key.properties" in ignore


def test_mobile_icons_use_density_resources_and_compact_ui_asset() -> None:
    manifest = Path(
        "apps/android/android/app/src/main/AndroidManifest.xml"
    ).read_text(encoding="utf-8")
    assert 'android:icon="@mipmap/ic_launcher"' in manifest
    assert not Path(
        "apps/android/android/app/src/main/res/drawable-nodpi/logo_mobileapp.png"
    ).exists()
    for density in ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"):
        assert Path(
            f"apps/android/android/app/src/main/res/mipmap-{density}/ic_launcher.png"
        ).exists()
    assert Path("apps/android/assets/logo_mobileapp.png").stat().st_size < 500_000


def test_mobile_launcher_and_splash_use_complete_brand_lockup() -> None:
    gradle = Path("apps/android/android/app/build.gradle").read_text(
        encoding="utf-8"
    )
    manifest = Path(
        "apps/android/android/app/src/main/AndroidManifest.xml"
    ).read_text(encoding="utf-8")
    adaptive_icon = Path(
        "apps/android/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"
    ).read_text(encoding="utf-8")
    styles = Path(
        "apps/android/android/app/src/main/res/values/styles.xml"
    ).read_text(encoding="utf-8")
    android_12_styles = Path(
        "apps/android/android/app/src/main/res/values-v31/styles.xml"
    ).read_text(encoding="utf-8")
    generator = Path(
        "tools/packaging/generate_android_brand_assets.ps1"
    ).read_text(encoding="utf-8")

    assert 'android:roundIcon="@mipmap/ic_launcher"' in manifest
    assert 'resValue "string", "app_name", "PRANA STG"' in gradle
    assert 'resValue "string", "app_name", "PRANA ELEX"' in gradle
    assert '@color/prana_canvas' in adaptive_icon
    assert '@drawable/ic_launcher_foreground' in adaptive_icon
    assert '@drawable/launch_background' in styles
    assert '@drawable/splash_logo' in android_12_styles
    assert 'logo_lockup.png' in generator
    assert "-ContentWidth 252" in generator


def test_mobile_apk_build_wrapper_uses_flavor_config() -> None:
    physical_device = Path("build_android_apk.bat").read_text(encoding="utf-8")
    script = Path("apps/android/scripts/build-apk.ps1").read_text(encoding="utf-8")
    assert "apps\\android\\build.bat" in physical_device
    assert "apps\\android\\build.bat" in physical_device
    assert "-PhysicalDevice" in physical_device
    assert 'ValidateSet("staging", "production")' in script
    assert "--dart-define-from-file=config/$Flavor.json" in script
    assert '"--dart-define=API_URL=$ApiUrl"' in script
    assert 'Get-NetRoute' not in script
    assert "build\\buildapp\\flutter" in script
    assert "installers\\android\\$Flavor" in script
    assert 'config "--build-dir=$flutterBuildDirSetting"' in script
    assert 'config "--build-dir=build"' in script
    assert '$localApk = Join-Path $appRoot "build\\app\\outputs\\flutter-apk' in script
    assert "foreach ($oldApk in @($expectedApk, $localApk, $installerApk))" in script
    assert "Sort-Object LastWriteTimeUtc -Descending" in script
    assert "FIREBASE_API_KEY" not in script


def test_mobile_runner_pins_the_named_avd_to_balanced_resolution() -> None:
    runner = Path("apps/android/scripts/run.ps1").read_text(encoding="utf-8")
    enable_station = Path("scripts/dev/enable-station.ps1").read_text(
        encoding="utf-8"
    )

    for script in (runner, enable_station):
        assert '[string]$EmulatorResolution = "1080x2160"' in script
    assert "[switch]$WithMobile" in enable_station
    assert "if ($WithMobile)" in enable_station
    assert "-EmulatorResolution $EmulatorResolution" in enable_station

    assert "getprop ro.boot.qemu.avd_name" in runner
    assert "emu avd name" in runner
    assert "(Get-EmulatorAvdName -DeviceId $candidateId) -eq $AvdName" in runner
    assert "Get-EmulatorResolution -DeviceId $deviceId" in runner
    assert "emu kill" in runner
    assert '"-skin", $EmulatorResolution' in runner
    assert "& $flutter build apk" in runner
    assert "--use-application-binary=$prebuiltApk" in runner
    assert "for ($stableCheck = 1; $stableCheck -le 3; $stableCheck++)" in runner


def test_mobile_runner_uses_utf8_and_safe_kotlin_compatibility() -> None:
    root_wrapper = Path("run_android_emulator.bat").read_text(encoding="utf-8")
    app_wrapper = Path("apps/android/run.bat").read_text(encoding="utf-8")
    runner_bytes = Path("apps/android/scripts/run.ps1").read_bytes()
    runner = runner_bytes.decode("utf-8-sig")
    properties = Path(
        "apps/android/android/gradle.properties"
    ).read_text(encoding="utf-8")
    settings = Path(
        "apps/android/android/settings.gradle"
    ).read_text(encoding="utf-8")

    assert "chcp 65001" in root_wrapper
    assert "chcp 65001" in app_wrapper
    assert runner_bytes.startswith(b"\xef\xbb\xbf")
    assert "[Console]::OutputEncoding = $utf8" in runner
    assert "$OutputEncoding = $utf8" in runner
    assert "android.builtInKotlin=false" in properties
    assert "android.newDsl=false" in properties
    assert "org.jetbrains.kotlin.android" in settings


def test_mobile_declares_android_text_to_speech_support() -> None:
    pubspec = Path("apps/android/pubspec.yaml").read_text(encoding="utf-8")
    manifest = Path(
        "apps/android/android/app/src/main/AndroidManifest.xml"
    ).read_text(encoding="utf-8")
    live = Path("apps/android/lib/features/live/live_screen.dart").read_text(
        encoding="utf-8"
    )

    assert "flutter_tts: ^4.2.5" in pubspec
    assert "android.intent.action.TTS_SERVICE" in manifest
    assert "speak_translation" in live
    assert "Icons.volume_up_outlined" in live


def test_live_screen_does_not_render_station_diagnostics() -> None:
    live = Path("apps/android/lib/features/live/live_screen.dart").read_text(
        encoding="utf-8"
    )
    localization = Path(
        "apps/android/lib/core/localization.dart"
    ).read_text(encoding="utf-8")

    assert "_DiagnosticsPanel" not in live
    assert "_DiagnosticRow" not in live
    assert "'diagnostics':" not in localization
    assert "onAction:" in live
    assert "controller.retry(station)" in live


def test_account_screen_keeps_plan_choices_collapsed_by_default() -> None:
    account = Path(
        "apps/android/lib/features/account/account_screen.dart"
    ).read_text(encoding="utf-8")

    assert "bool showPlans = false;" in account
    assert "if (showPlans)" in account
    assert "class _StatusChip" in account
    assert "VisualDensity(vertical: -2)" in account
    assert "reset_password_short" in account


def test_station_list_does_not_expose_internal_session_ids() -> None:
    stations = Path(
        "apps/android/lib/features/stations/station_list_screen.dart"
    ).read_text(encoding="utf-8")

    assert "station.sessionId" not in stations
    assert "not_started" not in stations
    assert "childAspectRatio: columns == 1 ? 2.7 : 2" in stations


def test_installer_layout_is_separate_from_build_cache() -> None:
    readme = Path("installers/README.md").read_text(encoding="utf-8")
    assert "artifact" in readme
    assert "release/" not in readme


def test_platform_build_wrappers_forward_arguments() -> None:
    assert 'apps\\android\\build.bat" -PhysicalDevice %*' in Path(
        "build_android_apk.bat"
    ).read_text(encoding="utf-8")
    assert 'apps/linux/build.sh" "$@"' in Path("buildlinux").read_text(encoding="utf-8")


def test_physical_android_build_defaults_to_remote_cloud_api() -> None:
    example = json.loads(
        Path("apps/android/config/staging.example.json").read_text(encoding="utf-8")
    )
    app_config = Path("apps/android/lib/core/app_config.dart").read_text(
        encoding="utf-8"
    )
    build_script = Path("apps/android/scripts/build-apk.ps1").read_text(
        encoding="utf-8"
    )

    assert example["API_URL"].startswith("https://")
    assert ".run.app" in example["API_URL"]
    assert example["API_URL"] in app_config
    assert "Get-NetRoute" not in build_script
    assert "Get-NetIPAddress" not in build_script


def test_python_packages_share_one_version_source() -> None:
    core = Path("packages/prana_core/src/prana_core/__init__.py").read_text(encoding="utf-8")
    windows = Path("apps/windows/src/prana_windows/__init__.py").read_text(encoding="utf-8")
    linux = Path("apps/linux/src/prana_linux/__init__.py").read_text(encoding="utf-8")
    version = Path("packages/prana_core/src/prana_core/VERSION").read_text(encoding="utf-8").strip()
    assert 'joinpath("VERSION")' in core
    assert "from prana_core import __version__" in windows
    assert "from prana_core import __version__" in linux
    assert f'"prana-elex-core=={version}"' in Path("apps/windows/pyproject.toml").read_text(encoding="utf-8")
    assert f'"prana-elex-core=={version}"' in Path("apps/linux/pyproject.toml").read_text(encoding="utf-8")
    assert f"version: {version}+1" in Path("apps/android/pubspec.yaml").read_text(encoding="utf-8")
