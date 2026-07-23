from __future__ import annotations

import argparse
from pathlib import Path

from prana_core.station.commands import provision_station, run_station
from prana_windows.audio.wasapi import WASAPIBackend
from prana_windows.credential_store import WindowsCredentialStore


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "default.toml"


def _parser(provision: bool = False) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PRANA ELEX Windows Station")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--data-dir", type=Path, default=None)
    if provision:
        parser.add_argument("--output", type=Path, default=Path("prana-station-label"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    run_station(args.config, args.data_dir, WindowsCredentialStore(), WASAPIBackend)


def provision() -> None:
    args = _parser(provision=True).parse_args()
    provision_station(args.config, args.data_dir, args.output, WindowsCredentialStore())
