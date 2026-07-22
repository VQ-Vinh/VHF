from __future__ import annotations

import argparse
from pathlib import Path

from prana_elex.common.logger import setup_logger
from prana_elex.config.schema import load_config
from prana_elex.station.client import StationApiClient
from prana_elex.station.runtime import StationRuntime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PRANA ELEX in cloud-controlled station mode")
    parser.add_argument("--config", type=Path, default=Path("config/default.toml"))
    parser.add_argument("--data-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config, base_dir=args.data_dir)
    setup_logger(level=config.general.log_level, console_level="INFO")
    if not config.backend.api_url:
        raise SystemExit("backend.api_url is required for Station Mode")
    client = StationApiClient(config.backend.api_url, config.backend.timeout_seconds)
    print(f"PRANA ELEX Station {client.identity.id}")
    print("The station stores no Firebase user session. Press Ctrl+C to stop.")
    try:
        StationRuntime(config, client).run_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
