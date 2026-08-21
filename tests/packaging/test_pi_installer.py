from __future__ import annotations

import ast
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "install.sh"
SERVICE = ROOT / "apps" / "linux" / "packaging" / "debian" / "prana-station.service"
RELEASE = ROOT / "release-pi.sh"


class RaspberryPiInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = INSTALLER.read_text(encoding="utf-8")

    def test_provisions_as_the_user_that_runs_the_service(self) -> None:
        # The credential store keys off XDG_CONFIG_HOME. Provisioning as root
        # would mint an identity under /root that the service never loads, so
        # the printed QR would pair a station that stays offline forever.
        unit = SERVICE.read_text(encoding="utf-8")
        config_home = re.search(
            r"Environment=XDG_CONFIG_HOME=(\S+)", unit
        ).group(1)
        service_user = re.search(r"^User=(\S+)", unit, re.MULTILINE).group(1)

        self.assertIn('sudo -u "$SERVICE_USER"', self.script)
        self.assertIn(f'SERVICE_USER="{service_user}"', self.script)
        self.assertIn(f'SERVICE_CONFIG_HOME="{config_home}"', self.script)
        self.assertIn('env "XDG_CONFIG_HOME=$SERVICE_CONFIG_HOME"', self.script)

        # Every invocation, once line continuations are folded away, must carry
        # both the user switch and the config home.
        folded = re.sub(r"\\\n\s*", " ", self.script)
        calls = [
            line for line in folded.splitlines()
            if "prana-station-provision" in line and not line.strip().startswith("#")
        ]
        self.assertTrue(calls, "installer must provision the device")
        for line in calls:
            self.assertIn("sudo -u", line)
            self.assertIn("XDG_CONFIG_HOME", line)

    def test_label_output_path_is_absolute(self) -> None:
        # provision() defaults --output to the relative "prana-station-label",
        # which under sudo -u would land in the caller's working directory.
        self.assertIn('LABEL_DIR="/var/lib/prana-elex/label"', self.script)
        self.assertIn('--output "$LABEL_DIR"', self.script)

    def test_a_relative_deb_path_is_made_absolute(self) -> None:
        # apt treats a relative path as a package name and splits it on "/", so
        # "--deb installers/linux/x.deb" fails with "Unable to locate package
        # installers/linux" instead of installing the file.
        self.assertIn('DEB_PATH="$(readlink -f "$DEB_PATH")"', self.script)
        resolve = self.script.index('readlink -f "$DEB_PATH"')
        self.assertLess(
            resolve,
            self.script.index('apt-get install -y "$DEB_PATH"'),
            "the path must be resolved before apt sees it",
        )
        # The checksum must cover the same file apt installs.
        self.assertLess(resolve, self.script.index("sha256sum"))

    def test_package_is_verified_before_it_is_installed(self) -> None:
        self.assertIn("set -euo pipefail", self.script)
        self.assertIn("sha256sum", self.script)
        # postinst runs as root, so a tampered package must never reach apt.
        first_hash = self.script.index("sha256sum")
        install = self.script.index('apt-get install -y "$DEB_PATH"')
        self.assertLess(first_hash, install)

    def test_refuses_the_wrong_platform(self) -> None:
        self.assertIn('[[ "$(id -u)" -eq 0 ]]', self.script)
        self.assertIn("aarch64", self.script)
        self.assertIn('[[ "$(uname -s)" == "Linux" ]]', self.script)

    def test_accepts_the_releases_the_package_is_built_for(self) -> None:
        # The installer must not warn on a release build.sh happily builds on.
        build = (
            ROOT / "apps" / "linux" / "packaging" / "build.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("bookworm|trixie", build)
        self.assertIn("bookworm|trixie", self.script)

    def test_carries_no_secrets_and_downloads_over_https(self) -> None:
        lowered = self.script.lower()
        for needle in ("private key", "gcs-service-account", "ghp_", "authorization:"):
            self.assertNotIn(needle, lowered)
        for url in re.findall(r"https?://[^\s\"']+", self.script):
            self.assertTrue(url.startswith("https://"), url)

    def test_cleans_up_its_download_directory(self) -> None:
        self.assertIn("mktemp -d", self.script)
        self.assertIn("trap cleanup EXIT", self.script)


class ShellEntryPointModeTests(unittest.TestCase):
    """Git mode bits, not file contents.

    Windows checkouts cannot express the executable bit, so a script committed
    as 100644 looks fine locally and fails only on a fresh Linux clone with
    "Permission denied" -- exactly where there is no repository to repair it.
    """

    ENTRY_POINTS = (
        "buildlinux",
        "install.sh",
        "release-pi.sh",
        "apps/linux/build.sh",
        "apps/linux/run.sh",
        "apps/linux/packaging/build.sh",
        "scripts/setup/setup.sh",
    )

    @staticmethod
    def _modes(*patterns: str) -> dict[str, str]:
        listing = subprocess.run(
            ["git", "ls-files", "-s", *patterns],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        modes = {}
        for line in listing.splitlines():
            meta, path = line.split("	", 1)
            modes[path] = meta.split()[0]
        return modes

    def test_shell_entry_points_are_committed_executable(self) -> None:
        modes = self._modes(*self.ENTRY_POINTS)
        for path in self.ENTRY_POINTS:
            self.assertIn(path, modes, f"{path} is not tracked")
            self.assertEqual(modes[path], "100755", f"{path} is not executable")

    def test_every_tracked_shell_script_is_executable(self) -> None:
        offenders = sorted(
            path for path, mode in self._modes("*.sh").items() if mode == "100644"
        )
        self.assertEqual(offenders, [], "shell scripts committed without +x")


def _calls_main(body: list[ast.stmt]) -> bool:
    """Whether running this block as a script would call main().

    Accepts either a bare module-level call or one guarded by __main__; both
    execute under PyInstaller, and the repo uses each style somewhere.
    """
    for node in body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "main"
        ):
            return True
        if isinstance(node, ast.If) and _calls_main(node.body):
            return True
    return False


class FrozenEntryPointTests(unittest.TestCase):
    """Every PyInstaller spec must point at a script that actually runs main().

    A frozen bundle executes its entry file as a script, so an entry module that
    only defines main() exits 0 having done nothing. systemd then reports a
    service that started and stopped cleanly, with no error to go on.
    """

    SPECS = (
        "apps/linux/packaging/PRANA_ELEX.spec",
        "apps/windows/packaging/PRANA_Station.spec",
        "apps/windows/packaging/PRANA_ELEX.spec",
    )

    def test_spec_entry_scripts_invoke_main(self) -> None:
        for name in self.SPECS:
            with self.subTest(spec=name):
                spec = (ROOT / name).read_text(encoding="utf-8")
                match = re.search(
                    r'Analysis\(\s*\[str\(PROJECT_ROOT / "([^"]+)"\)\]', spec
                )
                self.assertIsNotNone(match, "cannot find the Analysis entry script")
                entry = ROOT / match.group(1)
                self.assertTrue(entry.is_file(), f"{entry} does not exist")
                tree = ast.parse(entry.read_text(encoding="utf-8"))
                self.assertTrue(
                    _calls_main(tree.body),
                    f"{match.group(1)} never calls main() when run as a script",
                )


class BuildBackendSeedingTests(unittest.TestCase):
    """Every script that pairs a fresh venv with --no-build-isolation.

    That flag tells pip the build backend is already present, but Python 3.12
    stopped seeding setuptools into new venvs. Bookworm's 3.11 hid this; Trixie
    ships 3.13, where the editable install dies with
    "Cannot import 'setuptools.build_meta'".
    """

    SCRIPTS = (
        "apps/linux/packaging/build.sh",
        "apps/windows/packaging/build.bat",
        "scripts/setup/setup.sh",
        "scripts/setup/setup.bat",
    )

    def test_no_build_isolation_is_always_preceded_by_a_seeded_backend(self) -> None:
        for name in self.SCRIPTS:
            with self.subTest(script=name):
                lines = [
                    line.strip()
                    for line in (ROOT / name).read_text(encoding="utf-8").splitlines()
                ]
                code = [
                    (index, line)
                    for index, line in enumerate(lines)
                    if not line.startswith(("#", "REM ", "::"))
                ]
                seeds = [i for i, line in code if "pip setuptools wheel" in line]
                isolated = [i for i, line in code if "--no-build-isolation" in line]

                self.assertTrue(isolated, "script no longer uses --no-build-isolation")
                self.assertTrue(seeds, "setuptools is never installed")
                # Seeding afterwards does not help the install that already failed.
                self.assertLess(
                    min(seeds),
                    min(isolated),
                    "setuptools must be seeded before the editable install",
                )


class RaspberryPiReleaseScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.script = RELEASE.read_text(encoding="utf-8")

    def test_publishes_the_artifacts_install_sh_expects(self) -> None:
        # install.sh looks for a *_arm64.deb asset and its .sha256 sidecar.
        # Publishing the package without the checksum silently downgrades every
        # later install to an unverified download.
        self.assertIn('DEB="installers/linux/prana-elex_${VERSION}_arm64.deb"', self.script)
        self.assertIn('"$DEB" "$DEB.sha256"', self.script)
        self.assertIn('[[ -f "$DEB.sha256" ]]', self.script)

    def test_version_comes_from_the_single_source_of_truth(self) -> None:
        self.assertIn("packages/prana_core/src/prana_core/VERSION", self.script)
        self.assertNotIn("1.1.0", self.script)

    def test_refuses_to_build_as_root_on_the_wrong_machine(self) -> None:
        self.assertIn("set -euo pipefail", self.script)
        self.assertIn('[[ "$(id -u)" -ne 0 ]]', self.script)
        self.assertIn("aarch64", self.script)
        self.assertIn("gh auth status", self.script)

    def test_reruns_do_not_fail_on_an_existing_tag(self) -> None:
        self.assertIn("gh release view", self.script)
        self.assertIn("--clobber", self.script)


if __name__ == "__main__":
    unittest.main()
