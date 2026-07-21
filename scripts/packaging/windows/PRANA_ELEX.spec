# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]

datas = collect_data_files("silero_vad")
datas += collect_data_files("qtawesome")
datas += [
    (str(PROJECT_ROOT / "src/prana_elex/ui/resources/styles.qss"), "prana_elex/ui/resources"),
    (str(PROJECT_ROOT / "src/prana_elex/ui/resources/google-g.svg"), "prana_elex/ui/resources"),
    (str(PROJECT_ROOT / "config/profiles/windows-device.toml"), "config"),
]

hiddenimports = [
    "qasync",
    "httpx",
    "cryptography",
    "keyring",
    "keyring.backends.Windows",
    "silero_vad",
    "silero_vad.data",
    "webrtcvad",
    "pyaudiowpatch",
    "pydantic",
    "pydantic.v1",
    "qtawesome",
    "qtpy",
    "qtpy.QtCore",
    "qtpy.QtGui",
    "qtpy.QtWidgets",
]

excludes = [
    "sympy",
    "matplotlib",
    "PIL",
    "networkx",
]

a = Analysis(
    [str(PROJECT_ROOT / "src/prana_elex/app/frozen_entry.py")],
    pathex=[str(PROJECT_ROOT / "src"), str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(PROJECT_ROOT / "scripts/packaging/windows/hooks/hide_subprocess_console.py")],
    excludes=excludes,
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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "scripts/packaging/windows/installer/assets/prana-elex.ico"),
    version=str(PROJECT_ROOT / "scripts/packaging/windows/version_info.txt"),
)

COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PRANA_ELEX",
)
