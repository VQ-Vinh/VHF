from __future__ import annotations

import argparse
import hashlib
import secrets
from pathlib import Path

from prana_elex.config.schema import load_config
from prana_elex.station.client import StationApiClient
from prana_elex.station.label import grouped, qr_payload, write_label


ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision and print a PRANA ELEX station label")
    parser.add_argument("--config", type=Path, default=Path("config/default.toml"))
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=Path("prana-station-label"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config, base_dir=args.data_dir)
    if not config.backend.api_url:
        raise SystemExit("backend.api_url is required for station provisioning")
    client = StationApiClient(config.backend.api_url, config.backend.timeout_seconds)
    store = client.identity.store
    activation_code = store.get("station_activation_code")
    if not activation_code:
        activation_code = "".join(secrets.choice(ALPHABET) for _ in range(16))
        store.set("station_activation_code", activation_code)
    activation_hash = hashlib.sha256(
        f"{client.identity.id}:{activation_code}".encode("utf-8")
    ).hexdigest()
    provisioned = client.provision(activation_hash)
    setup_id = str(provisioned["setup_id"])
    store.set("station_setup_id", setup_id)
    store.set("station_provisioned", "1")
    png_path, svg_path = write_label(args.output, setup_id, activation_code)
    print(f"Station ID: {client.identity.id}")
    print(f"Setup ID: {setup_id}")
    print(f"Activation code: {grouped(activation_code)}")
    print(f"QR: {qr_payload(setup_id, activation_code)}")
    print(f"PNG label: {png_path.resolve()}")
    print(f"SVG label: {svg_path.resolve()}")
    print("Keep the label private until the device is delivered.")
