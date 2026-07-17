from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prana_elex.config import autostart, user_settings
from prana_elex.backend.secure_store import SecureStore


class LinuxUserConfigTests(unittest.TestCase):
    def test_windows_all_users_settings_fall_back_to_program_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local = Path(temporary) / "local"
            program_data = Path(temporary) / "program-data"
            machine_settings = program_data / "PRANA ELEX" / "settings.json"
            machine_settings.parent.mkdir(parents=True)
            machine_settings.write_text('{"data_dir": "D:/Dữ liệu PRANA"}', encoding="utf-8")
            with (
                patch.dict(os.environ, {"LOCALAPPDATA": str(local), "PROGRAMDATA": str(program_data)}),
                patch.object(sys, "platform", "win32"),
            ):
                self.assertEqual(user_settings.load_settings()["data_dir"], "D:/Dữ liệu PRANA")

    def test_frozen_linux_settings_are_private_and_use_xdg(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": temporary}),
                patch.object(sys, "platform", "linux"),
                patch.object(sys, "frozen", True, create=True),
            ):
                user_settings.save_settings("/tmp/data")
                path = Path(temporary) / "prana-elex" / "settings.json"
                self.assertTrue(path.is_file())
                self.assertEqual(user_settings.load_settings()["data_dir"], "/tmp/data")
                self.assertNotIn("credentials_path", user_settings.load_settings())
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_ui_locale_is_persisted_without_losing_data_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": temporary}),
                patch.object(sys, "platform", "linux"),
            ):
                user_settings.save_settings("/tmp/prana-data")
                user_settings.save_settings(ui_locale="vi")
                settings = user_settings.load_settings()
                self.assertEqual(settings["data_dir"], "/tmp/prana-data")
                self.assertEqual(settings["ui_locale"], "vi")

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

    def test_linux_secret_fallback_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(os.environ, {"XDG_CONFIG_HOME": temporary}),
                patch.object(sys, "platform", "linux"),
                patch.object(SecureStore, "_keyring", return_value=None),
            ):
                store = SecureStore()
                store.set("refresh_token", "refresh-value")
                path = Path(temporary) / "prana-elex" / "auth.json"
                self.assertEqual(store.get("refresh_token"), "refresh-value")
                self.assertNotIn("password", path.read_text(encoding="utf-8").lower())
                if os.name == "posix":
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
