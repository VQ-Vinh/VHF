# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = collect_data_files("PySide6", include_py_files=True)

datas += collect_data_files("silero_vad")
datas += collect_data_files("qtawesome")
datas += [
    ("..\\src\\prana_elex\\ui\\resources\\styles.qss", "prana_elex\\ui\\resources"),
    ("..\\config\\default.toml", "config"),
]

hiddenimports = [
    "qasync",
    "google.genai",
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
    ["..\\src\\prana_elex\\__main_window__.py"],
    pathex=["..\\src", ".."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["scripts\\pyi_rth_hide_subprocess_console.py"],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
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
    icon=None,
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
