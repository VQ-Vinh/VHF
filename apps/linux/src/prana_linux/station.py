from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prana_core.station.commands import provision_station, run_station
from prana_linux.audio.pulse import PulseBackend
from prana_linux.credential_store import LinuxCredentialStore


def _default_config() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "config" / "default.toml"
    return Path(__file__).resolve().parents[2] / "config" / "default.toml"


def _parser(provision: bool = False) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PRANA ELEX Raspberry Pi Station")
    parser.add_argument("--config", type=Path, default=_default_config())
    parser.add_argument("--data-dir", type=Path, default=None)
    if provision:
        parser.add_argument("--output", type=Path, default=Path("prana-station-label"))
    return parser


def main() -> None:
    if "--provision" in sys.argv:
        sys.argv.remove("--provision")
        provision()
        return
    args = _parser().parse_args()
    run_station(args.config, args.data_dir, LinuxCredentialStore(), PulseBackend)


def provision() -> None:
    args = _parser(provision=True).parse_args()
    provision_station(args.config, args.data_dir, args.output, LinuxCredentialStore())
