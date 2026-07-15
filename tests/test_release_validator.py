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
            "_internal/config/default.toml",
            "_internal/prana_elex/ui/resources/styles.qss",
        ):
            path = bundle / relative
            path.parent.mkdir(parents=True, exist_ok=True)
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


if __name__ == "__main__":
    unittest.main()
