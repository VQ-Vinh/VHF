# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]

datas = collect_data_files("silero_vad")
datas += [(str(PROJECT_ROOT / "apps/linux/config/default.toml"), "config")]

hiddenimports = [
    "httpx",
    "cryptography",
    "keyring",
    "keyring.backends.SecretService",
    "silero_vad",
    "silero_vad.data",
    "webrtcvad",
    "pyaudio",
    "pydantic",
    "pydantic.v1",
]

a = Analysis(
    [str(PROJECT_ROOT / "apps/linux/src/prana_linux/station.py")],
    pathex=[
        str(PROJECT_ROOT / "packages/prana_core/src"),
        str(PROJECT_ROOT / "apps/linux/src"),
        str(PROJECT_ROOT),
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "prana_windows",
        "pyaudiowpatch",
        "PySide6",
        "qasync",
        "qtawesome",
        "sympy",
        "matplotlib",
        "networkx",
        "win32api",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PRANA_Station",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PRANA_Station",
)
