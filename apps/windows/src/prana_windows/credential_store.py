from __future__ import annotations


SERVICE_NAME = "PRANA ELEX"


class WindowsCredentialStore:
    """Credential Manager-backed storage with no plaintext fallback."""

    @staticmethod
    def _keyring():
        try:
            import keyring

            return keyring
        except Exception as exc:
            raise RuntimeError("Windows Credential Manager is unavailable") from exc

    def get(self, key: str) -> str | None:
        try:
            return self._keyring().get_password(SERVICE_NAME, key)
        except Exception:
            return None

    def set(self, key: str, value: str) -> None:
        try:
            self._keyring().set_password(SERVICE_NAME, key, value)
        except Exception as exc:
            raise RuntimeError(
                "Windows Credential Manager is unavailable; credentials were not saved"
            ) from exc

    def delete(self, key: str) -> None:
        try:
            self._keyring().delete_password(SERVICE_NAME, key)
        except Exception:
            pass
