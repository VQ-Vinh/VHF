# -*- mode: python ; coding: utf-8 -*-

import sys

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = collect_data_files("PySide6", include_py_files=True)

datas += [
    ("..\\src\\vhf_processor\\gui\\resources\\styles.qss", "vhf_processor\\gui\\resources"),
    ("..\\config\\default.toml", "config"),
]

hiddenimports = [
    "qasync",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "google.cloud.storage",
    "google.cloud.storage._http",
    "google.genai",
    "silero_vad",
    "webrtcvad",
    "pyaudiowpatch",
    "pydantic",
    "pydantic.v1",
]

excludes = [
    "torch.onnx",
    "torch.export",
    "torch.ao",
    "torch.utils.tensorboard",
    "torch.nn.attention",
    "torch.nn.parallel",
    "torch.distributions",
    "sympy",
    "matplotlib",
    "PIL",
    "networkx",
]

a = Analysis(
    ["..\\src\\vhf_processor\\main.py"],
    pathex=["..\\src", ".."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
