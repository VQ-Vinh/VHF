from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.packaging.common.validate_release import validate


class ReleaseValidatorTests(unittest.TestCase):
    def _windows_bundle(self, root: Path) -> Path:
        bundle = root / "PRANA_ELEX"
        for relative in (
            "PRANA_ELEX.exe",
            "_internal/config/windows-device.toml",
            "_internal/prana_elex/ui/resources/styles.qss",
            "_internal/prana_elex/ui/resources/google-g.svg",
        ):
            path = bundle / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".toml":
                path.write_text(
                    '[backend]\napi_url = "https://api.example.run.app"\nfirebase_api_key = "public-key"\ngoogle_oauth_client_id = "123-example.apps.googleusercontent.com"\n',
                    encoding="utf-8",
                )
            else:
                path.touch()
        return bundle

    def test_valid_windows_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(validate("windows", self._windows_bundle(Path(temporary))), 0)

    def test_credentials_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = self._windows_bundle(Path(temporary))
            (bundle / "gcs-service-account.json").touch()
            self.assertEqual(validate("windows", bundle), 1)

    def test_placeholder_backend_config_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = self._windows_bundle(Path(temporary))
            config = bundle / "_internal/config/windows-device.toml"
            config.write_text(
                '[backend]\napi_url = "https://REPLACE_WITH_PRANA_API_URL"\nfirebase_api_key = ""\ngoogle_oauth_client_id = ""\n',
                encoding="utf-8",
            )
            self.assertEqual(validate("windows", bundle), 1)


if __name__ == "__main__":
    unittest.main()
