from __future__ import annotations

import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "apps" / "windows" / "packaging" / "installer"


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

    def test_brand_artwork_is_generated_from_the_shared_master(self) -> None:
        """The icon tile is the brand navy, not the retired hand-drawn slate."""
        from PIL import Image

        icon = Image.open(INSTALLER / "assets" / "prana-elex.ico")
        icon.size = (256, 256)
        corner_in = icon.convert("RGBA").getpixel((40, 128))
        self.assertEqual(corner_in[:3], (13, 43, 79))  # #0D2B4F
        banner = Image.open(INSTALLER / "assets" / "wizard-banner.png").convert("RGB")
        self.assertEqual(banner.getpixel((10, 10)), (13, 43, 79))

    def test_desktop_brand_assets_have_one_generator(self) -> None:
        self.assertFalse((INSTALLER / "assets" / "generate_assets.py").exists())
        generator = (ROOT / "tools/packaging/generate_brand_assets.py").read_text(encoding="utf-8")
        self.assertIn('print("Windows desktop")', generator)
        self.assertIn("apps/windows/packaging/installer/assets", generator)

    def test_runtime_icon_is_the_installer_icon(self) -> None:
        """Window, taskbar and tray must show exactly what the installer shows."""
        runtime = ROOT / "apps/windows/src/prana_windows/ui/resources/prana-elex.ico"
        self.assertEqual(runtime.read_bytes(), (INSTALLER / "assets" / "prana-elex.ico").read_bytes())

    def test_pyinstaller_bundles_runtime_brand_assets(self) -> None:
        spec = (ROOT / "apps/windows/packaging/PRANA_ELEX.spec").read_text(encoding="utf-8")
        self.assertIn("ui/resources/logo_mark.png", spec)
        self.assertIn("ui/resources/prana-elex.ico", spec)

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
        self.assertIn("parents[2]", spec)

    def test_pyinstaller_bundles_the_brand_fonts(self) -> None:
        """Without this the frozen app silently falls back to Segoe UI."""
        spec = (ROOT / "apps/windows/packaging/PRANA_ELEX.spec").read_text(encoding="utf-8")
        self.assertIn("ui/resources/fonts", spec)
        self.assertIn(".ttf", spec)

    def test_build_outputs_are_platform_scoped(self) -> None:
        script = (ROOT / "apps" / "windows" / "packaging" / "build.bat").read_text(
            encoding="utf-8"
        )
        self.assertIn("build\\buildwin\\work", script)
        self.assertIn("build\\buildwin\\dist", script)
        self.assertIn("installers\\windows", script)
        self.assertIn("PRANA_Station.spec", script)
        self.assertIn("PRANA_Station\\PRANA_Station.exe", script)
        self.assertNotIn("release\\", script)

    def test_installer_bundles_and_autostarts_station_agent(self) -> None:
        script = (INSTALLER / "PRANA_ELEX.iss").read_text(encoding="utf-8")
        self.assertIn("build\\buildwin\\dist\\PRANA_Station\\*", script)
        self.assertIn("{userstartup}\\PRANA Station", script)
        self.assertIn("PRANA_Station\\PRANA_Station.exe", script)

        spec = (INSTALLER.parent / "PRANA_Station.spec").read_text(encoding="utf-8")
        self.assertIn("station_frozen_entry.py", spec)
        self.assertIn("apps/windows/config/default.toml", spec)
        self.assertIn('excludes=["PySide6"', spec)

    def test_build_installs_local_packages_without_isolation(self) -> None:
        script = (ROOT / "apps" / "windows" / "packaging" / "build.bat").read_text(
            encoding="utf-8"
        )
        self.assertEqual(script.count("--no-build-isolation -e"), 2)

    def test_windows_cli_gui_entrypoint_stays_in_windows_app(self) -> None:
        cli = (ROOT / "apps" / "windows" / "src" / "prana_windows" / "cli.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("from prana_windows.desktop import main as desktop_main", cli)
        self.assertNotIn("from prana_core.app.desktop", cli)

    def test_dev_desktop_entrypoint_bypasses_cli_prompts(self) -> None:
        desktop = (ROOT / "apps" / "windows" / "src" / "prana_windows" / "desktop.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("run_app()", desktop)
        self.assertNotIn("select_capture_mode", desktop)


if __name__ == "__main__":
    unittest.main()
