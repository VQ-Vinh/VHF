from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.packaging.validate_client_config import validate


STATION_CONFIG = """[backend]
api_url = "https://api.example.run.app"
firebase_api_key = ""
google_oauth_client_id = ""
"""

PLACEHOLDER_CONFIG = """[backend]
api_url = "https://REPLACE_WITH_API"
"""


class ClientBuildConfigTests(unittest.TestCase):
    def test_production_values_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.toml"
            path.write_text(
                '[backend]\napi_url="https://REPLACE_WITH_API"\nfirebase_api_key=""\ngoogle_oauth_client_id=""\n',
                encoding="utf-8",
            )
            self.assertTrue(validate(path))
            path.write_text(
                '[backend]\napi_url="https://api.example.run.app"\nfirebase_api_key="public-key"\ngoogle_oauth_client_id="123-example.apps.googleusercontent.com"\n',
                encoding="utf-8",
            )
            self.assertEqual(validate(path), [])

    def test_the_station_build_needs_no_sign_in_credentials(self):
        # The Pi station authenticates with an Ed25519 signature per request and
        # never signs a user in, so requiring these forced a credential into a
        # bundle that has no use for it.
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.toml"
            path.write_text(
                STATION_CONFIG,
                encoding="utf-8",
            )
            self.assertEqual(validate(path, "linux-arm64"), [])
            # The same file is still rejected for a build that does sign in.
            self.assertTrue(validate(path, "windows"))

    def test_the_station_build_still_needs_a_real_api_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.toml"
            path.write_text(
                PLACEHOLDER_CONFIG,
                encoding="utf-8",
            )
            self.assertTrue(validate(path, "linux-arm64"))

    def test_the_shipped_station_config_carries_no_credentials(self):
        root = Path(__file__).resolve().parents[2]
        config = root / "apps/linux/config/default.toml"
        self.assertEqual(validate(config, "linux-arm64"), [])
        text = config.read_text(encoding="utf-8")
        self.assertNotIn("AIza", text)


if __name__ == "__main__":
    unittest.main()
