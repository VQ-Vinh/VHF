from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prana_elex.config import autostart, user_settings


class LinuxUserConfigTests(unittest.TestCase):
    def test_frozen_linux_settings_are_private_and_use_xdg(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": temporary}),
                patch.object(sys, "platform", "linux"),
                patch.object(sys, "frozen", True, create=True),
            ):
                user_settings.save_settings("/tmp/data", "/tmp/key.json")
                path = Path(temporary) / "prana-elex" / "settings.json"
                self.assertTrue(path.is_file())
                self.assertEqual(user_settings.load_settings()["data_dir"], "/tmp/data")
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_linux_autostart_is_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": temporary}),
                patch.object(sys, "platform", "linux"),
                patch.object(sys, "frozen", True, create=True),
            ):
                self.assertFalse(autostart.is_enabled())
                autostart.set_enabled(True)
                desktop = Path(temporary) / "autostart" / "prana-elex.desktop"
                self.assertIn("Exec=/usr/bin/prana-elex", desktop.read_text(encoding="utf-8"))
                self.assertTrue(autostart.is_enabled())
                autostart.set_enabled(False)
                self.assertFalse(desktop.exists())


if __name__ == "__main__":
    unittest.main()
