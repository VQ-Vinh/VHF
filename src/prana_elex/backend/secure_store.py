from __future__ import annotations

import json
import sys

from prana_elex.config.user_settings import get_user_config_dir


SERVICE_NAME = "PRANA ELEX"


class SecureStore:
    """OS credential store with a Linux-only 0600 fallback.

    Windows must have a working Credential Manager backend; unencrypted fallback
    is deliberately disabled there. Raspberry Pi prefers Secret Service and may
    fall back to an owner-only file when no keyring daemon is available.
    """

    def __init__(self):
        self._fallback_path = get_user_config_dir() / "auth.json"

    @staticmethod
    def _keyring():
        try:
            import keyring

            return keyring
        except Exception:
            return None

    def get(self, key: str) -> str | None:
        keyring = self._keyring()
        if keyring is not None:
            try:
                value = keyring.get_password(SERVICE_NAME, key)
                if value is not None:
                    return value
            except Exception:
                pass
        return self._fallback().get(key)

    def set(self, key: str, value: str) -> None:
        keyring = self._keyring()
        if keyring is not None:
            try:
                keyring.set_password(SERVICE_NAME, key, value)
                return
            except Exception:
                pass
        if sys.platform == "win32":
            raise RuntimeError("Windows Credential Manager is unavailable; credentials were not saved")
        data = self._fallback()
        data[key] = value
        self._write_fallback(data)

    def delete(self, key: str) -> None:
        keyring = self._keyring()
        if keyring is not None:
            try:
                keyring.delete_password(SERVICE_NAME, key)
            except Exception:
                pass
        data = self._fallback()
        if key in data:
            del data[key]
            self._write_fallback(data)

    def _fallback(self) -> dict[str, str]:
        if not self._fallback_path.exists():
            return {}
        if sys.platform == "win32":
            return {}
        try:
            value = json.loads(self._fallback_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write_fallback(self, data: dict[str, str]) -> None:
        self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Secure credential storage is unavailable")
        self._fallback_path.parent.chmod(0o700)
        self._fallback_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._fallback_path.chmod(0o600)
