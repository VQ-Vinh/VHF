from unittest.mock import Mock, patch

from prana_core.backend.client import BackendClient
from prana_core.backend.credential_store import MemoryCredentialStore


def test_ensure_device_uses_the_injected_credential_store() -> None:
    store = MemoryCredentialStore()
    response = Mock(is_error=False)
    client = BackendClient(
        "https://api.example.com",
        "public-key",
        credential_store=store,
    )

    with (
        patch.object(client, "_headers", return_value={"Authorization": "Bearer test"}),
        patch("prana_core.backend.client.httpx.post", return_value=response),
    ):
        identity = client.ensure_device()

    assert identity.id == store.get("device_id")
    assert store.get("device_private_key")
