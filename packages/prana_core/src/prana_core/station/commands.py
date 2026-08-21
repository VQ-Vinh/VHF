from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Callable

from prana_core.audio.base import AudioBackend
from prana_core.backend.credential_store import CredentialStore
from prana_core.common.logger import configure_utf8_stdio, setup_logger
from prana_core.config.schema import AppConfig, load_config
from prana_core.station.client import StationApiClient
from prana_core.station.identity import StationIdentity
from prana_core.station.label import grouped, print_ascii_qr, qr_payload, write_label
from prana_core.station.runtime import StationRuntime
from prana_core.station.ptt import NullPttController, PttController


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
    ptt_controller_factory: Callable[[AppConfig], PttController] | None = None,
) -> None:
    configure_utf8_stdio()
    config, client = create_station_client(config_path, data_dir, store)
    setup_logger(level=config.general.log_level, console_level="INFO")
    print(f"PRANA ELEX Station {client.identity.id}")
    print("The station stores no Firebase user session. Press Ctrl+C to stop.")
    try:
        ptt_controller = (
            ptt_controller_factory(config)
            if ptt_controller_factory is not None
            else NullPttController()
        )
        StationRuntime(
            config,
            client,
            audio_backend_factory,
            ptt_controller,
        ).run_forever()
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
    payload = qr_payload(setup_id, activation_code)
    print(f"Station ID: {client.identity.id}")
    print(f"Setup ID: {setup_id}")
    print(f"Activation code: {grouped(activation_code)}")
    print(f"QR: {payload}")
    # A headless install has no other way to show the owner what to scan.
    print()
    if not print_ascii_qr(payload):
        print("Console cannot draw the QR; scan the PNG label instead.")
    print(f"PNG label: {png_path.resolve()}")
    print(f"SVG label: {svg_path.resolve()}")
    print("Keep the label private until the device is delivered.")
