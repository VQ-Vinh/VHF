from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Callable

from prana_core.audio.base import AudioBackend
from prana_core.backend.credential_store import CredentialStore
from prana_core.common.logger import setup_logger
from prana_core.config.schema import load_config
from prana_core.station.client import StationApiClient
from prana_core.station.identity import StationIdentity
from prana_core.station.label import grouped, qr_payload, write_label
from prana_core.station.runtime import StationRuntime


ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def create_station_client(
    config_path: Path,
    data_dir: Path | None,
    store: CredentialStore,
) -> tuple[object, StationApiClient]:
    config = load_config(config_path, base_dir=data_dir)
    if not config.backend.api_url:
        raise SystemExit("backend.api_url is required for Station Mode")
    identity = StationIdentity(store)
    client = StationApiClient(
        config.backend.api_url,
        identity,
        config.backend.timeout_seconds,
    )
    return config, client


def run_station(
    config_path: Path,
    data_dir: Path | None,
    store: CredentialStore,
    audio_backend_factory: Callable[[], AudioBackend],
) -> None:
    config, client = create_station_client(config_path, data_dir, store)
    setup_logger(level=config.general.log_level, console_level="INFO")
    print(f"PRANA ELEX Station {client.identity.id}")
    print("The station stores no Firebase user session. Press Ctrl+C to stop.")
    try:
        StationRuntime(config, client, audio_backend_factory).run_forever()
    except KeyboardInterrupt:
        pass


def provision_station(
    config_path: Path,
    data_dir: Path | None,
    output: Path,
    store: CredentialStore,
) -> None:
    _, client = create_station_client(config_path, data_dir, store)
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
    png_path, svg_path = write_label(output, setup_id, activation_code)
    print(f"Station ID: {client.identity.id}")
    print(f"Setup ID: {setup_id}")
    print(f"Activation code: {grouped(activation_code)}")
    print(f"QR: {qr_payload(setup_id, activation_code)}")
    print(f"PNG label: {png_path.resolve()}")
    print(f"SVG label: {svg_path.resolve()}")
    print("Keep the label private until the device is delivered.")
