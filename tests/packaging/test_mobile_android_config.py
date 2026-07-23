from pathlib import Path


def test_production_mobile_does_not_use_debug_signing() -> None:
    gradle = Path("apps/android/android/app/build.gradle").read_text(encoding="utf-8")
    assert "signingConfigs.debug" not in gradle
    assert "PRANA_ANDROID_KEYSTORE_PATH" in gradle
    assert "Production release signing is not configured" in gradle


def test_mobile_signing_properties_are_ignored() -> None:
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "apps/android/android/key.properties" in ignore


def test_mobile_apk_build_wrapper_uses_flavor_config() -> None:
    wrapper = Path("buildapp.bat").read_text(encoding="utf-8")
    legacy = Path("build_mobile_apk.bat").read_text(encoding="utf-8")
    script = Path("apps/android/scripts/build-apk.ps1").read_text(encoding="utf-8")
    assert "apps\\android\\build.bat" in wrapper
    assert "buildapp.bat" in legacy
    assert 'ValidateSet("staging", "production")' in script
    assert "--dart-define-from-file=config/$Flavor.json" in script
    assert "build\\buildapp\\flutter" in script
    assert "installers\\android\\$Flavor" in script
    assert 'config "--build-dir=$flutterBuildDirSetting"' in script
    assert 'config "--build-dir=build"' in script
    assert '$localApk = Join-Path $appRoot "build\\app\\outputs\\flutter-apk' in script
    assert "FIREBASE_API_KEY" not in script


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
