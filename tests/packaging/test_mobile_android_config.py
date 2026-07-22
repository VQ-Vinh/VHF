from pathlib import Path


def test_production_mobile_does_not_use_debug_signing() -> None:
    gradle = Path("apps/prana_mobile/android/app/build.gradle").read_text(encoding="utf-8")
    assert "signingConfigs.debug" not in gradle
    assert "PRANA_ANDROID_KEYSTORE_PATH" in gradle
    assert "Production release signing is not configured" in gradle


def test_mobile_signing_properties_are_ignored() -> None:
    ignore = Path(".gitignore").read_text(encoding="utf-8")
    assert "apps/prana_mobile/android/key.properties" in ignore
