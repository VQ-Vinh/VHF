from __future__ import annotations

import base64
import hashlib
import platform
import socket
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from prana_core.backend.credential_store import CredentialStore


class DeviceIdentity:
    def __init__(self, store: CredentialStore):
        self.store = store
        device_id = self.store.get("device_id")
        private_value = self.store.get("device_private_key")
        if not device_id or not private_value:
            private = Ed25519PrivateKey.generate()
            raw = private.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
            device_id = uuid.uuid4().hex
            self.store.set("device_id", device_id)
            self.store.set("device_private_key", base64.b64encode(raw).decode("ascii"))
        else:
            raw = base64.b64decode(private_value)
            private = Ed25519PrivateKey.from_private_bytes(raw)
        self.id = device_id
        self._private = private

    @property
    def public_key(self) -> str:
        raw = self._private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return base64.b64encode(raw).decode("ascii")

    @property
    def name(self) -> str:
        return socket.gethostname() or "PRANA ELEX device"

    @property
    def platform(self) -> str:
        return f"{platform.system()} {platform.machine()}"

    def sign(self, message: bytes) -> str:
        return base64.b64encode(self._private.sign(message)).decode("ascii")
