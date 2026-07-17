from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.packaging.common.validate_client_config import validate


class ClientBuildConfigTests(unittest.TestCase):
    def test_production_values_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "client.toml"
            path.write_text(
                '[backend]\napi_url="https://REPLACE_WITH_API"\nfirebase_api_key=""\n',
                encoding="utf-8",
            )
            self.assertTrue(validate(path))
            path.write_text(
                '[backend]\napi_url="https://api.example.run.app"\nfirebase_api_key="public-key"\n',
                encoding="utf-8",
            )
            self.assertEqual(validate(path), [])


if __name__ == "__main__":
    unittest.main()
