# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

PROJECT_ROOT = Path(SPECPATH).resolve().parents[2]
datas = collect_data_files("silero_vad")
datas += [(str(PROJECT_ROOT / "apps/windows/config/default.toml"), "config")]
# prana_core reads this at import time via importlib.resources; without it
# the frozen app dies with FileNotFoundError before reaching main().
datas += [(str(PROJECT_ROOT / "packages/prana_core/src/prana_core/VERSION"), "prana_core")]

a = Analysis(
    [str(PROJECT_ROOT / "apps/windows/src/prana_windows/station_frozen_entry.py")],
    pathex=[
        str(PROJECT_ROOT / "packages/prana_core/src"),
        str(PROJECT_ROOT / "apps/windows/src"),
        str(PROJECT_ROOT),
    ],
    datas=datas,
    hiddenimports=[
        "httpx", "cryptography", "keyring", "keyring.backends.Windows",
        "silero_vad", "silero_vad.data", "webrtcvad", "pyaudiowpatch",
        "pydantic", "pydantic.v1",
    ],
    excludes=["PySide6", "qasync", "qtawesome", "matplotlib", "networkx"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="PRANA_Station",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False,
)
COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False, name="PRANA_Station",
)
