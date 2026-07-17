# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]

datas = collect_data_files("silero_vad")
datas += collect_data_files("qtawesome")
datas += [
    (str(PROJECT_ROOT / "src/prana_elex/ui/resources/styles.qss"), "prana_elex/ui/resources"),
    (str(PROJECT_ROOT / "config/profiles/raspberry-pi.toml"), "config"),
]

hiddenimports = [
    "qasync",
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
    "qtawesome",
    "qtpy",
    "qtpy.QtCore",
    "qtpy.QtGui",
    "qtpy.QtWidgets",
]

a = Analysis(
    [str(PROJECT_ROOT / "src/prana_elex/app/frozen_entry.py")],
    pathex=[str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pyaudiowpatch", "sympy", "matplotlib", "PIL", "networkx", "win32api"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PRANA_ELEX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PRANA_ELEX",
)
