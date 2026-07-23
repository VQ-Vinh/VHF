from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prana_linux.credential_store import LinuxCredentialStore


class LinuxPlatformTests(unittest.TestCase):
    def test_secret_fallback_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": temporary}),
                patch.object(LinuxCredentialStore, "_keyring", return_value=None),
            ):
                store = LinuxCredentialStore()
                store.set("station_private_key", "private-value")
                path = Path(temporary) / "prana-elex" / "auth.json"
                self.assertEqual(store.get("station_private_key"), "private-value")
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_headless_package_has_systemd_service_and_no_desktop_file(self) -> None:
        root = Path("apps/linux/packaging")
        unit = (root / "debian/prana-station.service").read_text(encoding="utf-8")
        manifest = Path("apps/linux/pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("ExecStart=/usr/bin/prana-station", unit)
        self.assertNotIn("PySide6", manifest)
        self.assertFalse((root / "debian/prana-elex.desktop").exists())

    def test_linux_pyinstaller_spec_resolves_repository_root(self) -> None:
        spec = Path("apps/linux/packaging/PRANA_ELEX.spec").read_text(encoding="utf-8")
        self.assertIn("parents[2]", spec)
        self.assertIn("apps/linux/config/default.toml", spec)

    def test_linux_build_outputs_are_platform_scoped(self) -> None:
        script = Path("apps/linux/packaging/build.sh").read_text(encoding="utf-8")
        self.assertIn("build/buildlinux/work", script)
        self.assertIn("build/buildlinux/dist", script)
        self.assertIn("installers/linux", script)
        self.assertNotIn("release/linux-arm64", script)


if __name__ == "__main__":
    unittest.main()
