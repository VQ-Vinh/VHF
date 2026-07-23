from __future__ import annotations

import base64
import platform
import socket
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prana_core.backend.credential_store import CredentialStore


class StationIdentity:
    """Persistent Ed25519 identity, separate from the legacy desktop device."""

    def __init__(self, store: CredentialStore):
        self.store = store
        station_id = self.store.get("station_id")
        private_value = self.store.get("station_private_key")
        if not station_id or not private_value:
            private = Ed25519PrivateKey.generate()
            raw = private.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
            station_id = uuid.uuid4().hex
            self.store.set("station_id", station_id)
            self.store.set("station_private_key", base64.b64encode(raw).decode("ascii"))
        else:
            private = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_value))
        self.id = station_id
        self._private = private

    @property
    def public_key(self) -> str:
        raw = self._private.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")

    @property
    def name(self) -> str:
        return socket.gethostname() or "PRANA ELEX station"

    @property
    def platform(self) -> str:
        return f"{platform.system()} {platform.machine()}"

    def sign(self, message: bytes) -> str:
        return base64.b64encode(self._private.sign(message)).decode("ascii")
