from __future__ import annotations

import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "packaging" / "windows" / "installer"


class WindowsInstallerDefinitionTests(unittest.TestCase):
    def test_brand_assets_have_expected_formats(self) -> None:
        icon = (INSTALLER / "assets" / "prana-elex.ico").read_bytes()
        reserved, image_type, count = struct.unpack_from("<HHH", icon)
        self.assertEqual((reserved, image_type, count), (0, 1, 5))

        banner = (INSTALLER / "assets" / "wizard-banner.png").read_bytes()
        self.assertEqual(banner[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", banner[16:24])
        self.assertEqual((width, height), (430, 824))
        self.assertAlmostEqual(width / height, 164 / 314, places=2)

        logo = (INSTALLER / "assets" / "wizard-logo.png").read_bytes()
        self.assertEqual(struct.unpack(">II", logo[16:24]), (116, 116))

    def test_installer_is_branded_bilingual_and_keeps_data(self) -> None:
        script = (INSTALLER / "PRANA_ELEX.iss").read_text(encoding="utf-8")
        self.assertIn("WizardStyle=modern windows11 includetitlebar", script)
        self.assertIn('Name: "english"', script)
        self.assertIn('Name: "vietnamese"', script)
        self.assertIn("CreateCustomPage", script)
        self.assertEqual(script.count("CreateCustomPage("), 1)
        self.assertIn("DisableDirPage=yes", script)
        self.assertIn("UsePreviousAppDir=no", script)
        self.assertIn("LocationsPageTitle", script)
        self.assertIn("AppFolderLabel", script)
        self.assertIn("DataFolderLabel", script)
        self.assertIn("ReadyApplicationFolder", script)
        self.assertIn("UpdateReadyMemo", script)
        self.assertIn("{param:DATADIR|}", script)
        self.assertIn("WizardForm.DirEdit.Text := AppPath", script)
        self.assertIn("IsPathInside(DataPath, AppPath)", script)
        self.assertIn("IsPathInside(AppPath, DataPath)", script)
        self.assertIn("DataRetentionNote", script)
        self.assertNotIn("DataPageTitle", script)
        self.assertNotIn("gcs-service-account", script.lower())

        vietnamese = (INSTALLER / "languages" / "Vietnamese.isl").read_text(encoding="utf-8")
        self.assertIn("LanguageName=Tiếng Việt", vietnamese)
        self.assertIn("LanguageID=$042A", vietnamese)
        self.assertIn("ConfirmUninstall=", vietnamese)

    def test_pyinstaller_uses_the_same_icon(self) -> None:
        spec = (INSTALLER.parent / "PRANA_ELEX.spec").read_text(encoding="utf-8")
        self.assertIn("installer/assets/prana-elex.ico", spec)


if __name__ == "__main__":
    unittest.main()
