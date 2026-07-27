from pathlib import Path


def test_production_mobile_does_not_use_debug_signing() -> None:
    gradle = Path("apps/android/android/app/build.gradle").read_text(encoding="utf-8")
    assert "signingConfigs.debug" not in gradle
    assert "PRANA_ANDROID_KEYSTORE_PATH" in gradle
    assert "Production release signing is not configured" in gradle


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


def test_mobile_apk_build_wrapper_uses_flavor_config() -> None:
    wrapper = Path("buildapp.bat").read_text(encoding="utf-8")
    legacy = Path("build_mobile_apk.bat").read_text(encoding="utf-8")
    script = Path("apps/android/scripts/build-apk.ps1").read_text(encoding="utf-8")
    assert "apps\\android\\build.bat" in wrapper
    assert "buildapp.bat" in legacy
    assert "-PhysicalDevice" in legacy
    assert 'ValidateSet("staging", "production")' in script
    assert "--dart-define-from-file=config/$Flavor.json" in script
    assert '"--dart-define=API_URL=$ApiUrl"' in script
    assert 'Get-NetRoute' in script
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
    assert "-EmulatorResolution $EmulatorResolution" in enable_station

    assert "getprop ro.boot.qemu.avd_name" in runner
    assert "emu avd name" in runner
    assert "(Get-EmulatorAvdName -DeviceId $candidateId) -eq $AvdName" in runner
    assert "Get-EmulatorResolution -DeviceId $deviceId" in runner
    assert "emu kill" in runner
    assert '"-skin", $EmulatorResolution' in runner


def test_installer_layout_is_separate_from_build_cache() -> None:
    readme = Path("installers/README.md").read_text(encoding="utf-8")
    assert "artifact" in readme
    assert "release/" not in readme


def test_platform_build_wrappers_forward_arguments() -> None:
    assert 'apps\\windows\\build.bat" %*' in Path("buildwin.bat").read_text(encoding="utf-8")
    assert 'apps/linux/build.sh" "$@"' in Path("buildlinux").read_text(encoding="utf-8")


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
