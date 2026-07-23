from pathlib import Path


def test_core_has_no_platform_app_or_gui_dependencies() -> None:
    forbidden = (
        "prana_windows",
        "prana_linux",
        "PySide6",
        "qasync",
        "qtawesome",
        "sys.platform",
        "pyaudiowpatch",
        "pyaudio",
    )
    root = Path("packages/prana_core/src/prana_core")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in root.rglob("*.py")
    )
    for name in forbidden:
        assert name not in source


def test_platform_audio_backends_are_owned_by_their_apps() -> None:
    assert Path("apps/windows/src/prana_windows/audio/wasapi.py").is_file()
    assert Path("apps/linux/src/prana_linux/audio/pulse.py").is_file()
    assert not Path("packages/prana_core/src/prana_core/audio/wasapi.py").exists()
    assert not Path("packages/prana_core/src/prana_core/audio/pulse.py").exists()
