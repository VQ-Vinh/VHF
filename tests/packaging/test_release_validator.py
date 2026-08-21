from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from types import SimpleNamespace
from unittest.mock import patch

from tools.packaging.validate_release import _validate_linux_dependencies, validate


class ReleaseValidatorTests(unittest.TestCase):
    def _windows_bundle(self, root: Path) -> Path:
        bundle = root / "PRANA_ELEX"
        for relative in (
            "PRANA_ELEX.exe",
            "_internal/config/default.toml",
            "_internal/prana_windows/ui/resources/styles.qss",
            "_internal/prana_windows/ui/resources/google-g.svg",
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
            config = bundle / "_internal/config/default.toml"
            config.write_text(
                '[backend]\napi_url = "https://REPLACE_WITH_PRANA_API_URL"\nfirebase_api_key = ""\ngoogle_oauth_client_id = ""\n',
                encoding="utf-8",
            )
            self.assertEqual(validate("windows", bundle), 1)


if __name__ == "__main__":
    unittest.main()


class LinuxDependencyCheckTests(unittest.TestCase):
    """The ldd sweep, which runs only on Linux.

    torch ships hashed copies of libgomp, libgfortran and the ARM compute
    kernels inside torch.libs/, resolved at run time from the bundle. Bare ldd
    cannot see them, so every Pi build failed validation on libraries that were
    sitting in the bundle all along.
    """

    def _run(self, ldd_lines: list[str], names: list[str]) -> list[str]:
        files = {name: Path(name) for name in names}
        completed = SimpleNamespace(stdout="\n".join(ldd_lines), stderr="")
        with (
            patch("tools.packaging.validate_release.platform.system", return_value="Linux"),
            patch("tools.packaging.validate_release._elf_machine", return_value=183),
            patch(
                "tools.packaging.validate_release.subprocess.run",
                return_value=completed,
            ),
        ):
            return _validate_linux_dependencies(files)

    def test_libraries_carried_in_the_bundle_are_not_missing(self) -> None:
        errors = self._run(
            ["\tlibgomp-947d5fa1.so.1.0.0 => not found"],
            ["PRANA_Station", "_internal/torch.libs/libgomp-947d5fa1.so.1.0.0"],
        )
        self.assertEqual(errors, [])

    def test_cuda_libraries_are_expected_to_be_absent(self) -> None:
        # torchaudio comes in through silero-vad, names the CUDA runtime even in
        # CPU builds, and reaches for it only on a GPU the station will not have.
        errors = self._run(
            [
                "	libcudart.so.13 => not found",
                "	libc10_cuda.so => not found",
                "	libtorch_cuda.so => not found",
            ],
            ["PRANA_Station"],
        )
        self.assertEqual(errors, [])

    def test_a_library_absent_from_the_bundle_still_fails(self) -> None:
        # The check must keep catching a real packaging gap, such as a system
        # library that Depends forgot to name.
        errors = self._run(
            ["\tlibasound.so.2 => not found"],
            ["PRANA_Station"],
        )
        self.assertTrue(errors)
        self.assertIn("libasound.so.2", errors[0])
