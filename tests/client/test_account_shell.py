from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prana_elex.backend.auth import FirebaseAuthClient
from prana_elex.backend.client import BackendApiError, BackendClient
from prana_elex.storage.account import prepare_data_root

try:
    from PySide6.QtWidgets import QApplication
    from prana_elex.config.schema import AppConfig
    from prana_elex.ui.account import AccountController, AccountState
    from prana_elex.ui.pages.account import AuthPage
    from prana_elex.ui.i18n import language
    from prana_elex.ui.main_window import MainWindow
except ModuleNotFoundError as exc:
    if not (exc.name or "").startswith("PySide6"):
        raise
    AccountController = None  # type: ignore[assignment]
    AccountState = None  # type: ignore[assignment]
    AuthPage = None  # type: ignore[assignment]
    language = None  # type: ignore[assignment]
    QApplication = None  # type: ignore[assignment]
    AppConfig = None  # type: ignore[assignment]
    MainWindow = None  # type: ignore[assignment]


class _FakeAuth:
    def __init__(self, has_session: bool = True):
        self.has_session = has_session
        self.email = "user@example.com"

    def sign_out(self) -> None:
        self.has_session = False


class _FakeBackend:
    def __init__(self, profile: dict | None = None, error: Exception | None = None):
        self.auth = _FakeAuth()
        self.profile = profile or {}
        self.error = error
        self.registered = False

    def me(self) -> dict:
        if self.error:
            raise self.error
        return self.profile

    def ensure_device(self):
        if self.error:
            raise self.error
        self.registered = True
        return object()

    def reset_registration(self) -> None:
        self.registered = False

    def sign_out(self) -> None:
        self.auth.sign_out()
        self.registered = False


@unittest.skipIf(AccountController is None, "PySide6 is not installed in this test environment")
class AccountControllerTests(unittest.TestCase):
    @staticmethod
    def _profile(status: str = "active", verified: bool = True) -> dict:
        return {
            "uid": "user-1",
            "email": "user@example.com",
            "email_verified": verified,
            "status": status,
            "usage": {"used_audio_seconds": 60, "remaining_audio_seconds": 540},
        }

    def test_active_profile_registers_device_and_enters_translation_state(self) -> None:
        backend = _FakeBackend(self._profile())
        controller = AccountController(backend)  # type: ignore[arg-type]
        controller._load_profile()
        self.assertEqual(controller.state, AccountState.ACTIVE)
        self.assertTrue(backend.registered)

    def test_inactive_and_revoked_accounts_enter_restricted_state(self) -> None:
        backend = _FakeBackend(self._profile("suspended"))
        controller = AccountController(backend)  # type: ignore[arg-type]
        controller._load_profile()
        self.assertEqual(controller.state, AccountState.RESTRICTED)

        backend = _FakeBackend(self._profile(), BackendApiError("DEVICE_REVOKED", "Device is revoked", 403))
        controller = AccountController(backend)  # type: ignore[arg-type]
        controller._load_profile()
        self.assertEqual(controller.state, AccountState.RESTRICTED)

    def test_network_error_keeps_session_and_enters_offline_state(self) -> None:
        backend = _FakeBackend(error=BackendApiError("NETWORK_ERROR", "offline"))
        controller = AccountController(backend)  # type: ignore[arg-type]
        controller._load_profile()
        self.assertEqual(controller.state, AccountState.OFFLINE)
        self.assertTrue(backend.auth.has_session)

    def test_password_reset_uses_firebase_oob_flow(self) -> None:
        auth = FirebaseAuthClient("public-api-key")
        with patch.object(auth, "_identity", return_value={}) as identity:
            auth.request_password_reset("user@example.com")
        identity.assert_called_once_with(
            "sendOobCode", {"requestType": "PASSWORD_RESET", "email": "user@example.com"}
        )

    def test_backend_sign_out_keeps_device_identity_and_resets_registration(self) -> None:
        client = BackendClient("https://api.example.com", "public-api-key")
        device = object()
        client.device = device  # type: ignore[assignment]
        client._registered = True
        with patch.object(client.auth, "sign_out") as sign_out:
            client.sign_out()
        sign_out.assert_called_once()
        self.assertIs(client.device, device)
        self.assertFalse(client._registered)


class AccountStorageTests(unittest.TestCase):
    def test_account_scoped_storage_moves_back_to_selected_data_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested_file = root / "accounts" / "uid-first" / "VHF_Storage" / "audio" / "sample.wav"
            nested_file.parent.mkdir(parents=True)
            nested_file.write_bytes(b"wav")

            data_root = prepare_data_root(root, "uid-first")
            self.assertEqual(data_root, root.resolve())
            self.assertEqual((root / "VHF_Storage" / "audio" / "sample.wav").read_bytes(), b"wav")
            self.assertFalse((root / "accounts").exists())

    def test_all_accounts_use_the_selected_data_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(prepare_data_root(root, "uid-first"), root.resolve())
            self.assertEqual(prepare_data_root(root, "uid-second"), root.resolve())


@unittest.skipIf(MainWindow is None, "PySide6 is not installed in this test environment")
class AccountShellUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_auth_page_has_room_for_forms_and_actions(self) -> None:
        page = AuthPage()
        self.assertGreaterEqual(page.card.minimumWidth(), 680)
        self.assertGreaterEqual(page.card.minimumHeight(), 520)
        self.assertGreaterEqual(page._tabs.minimumHeight(), 310)
        page.close()

    def test_auth_page_switches_language_without_recreation(self) -> None:
        page = AuthPage()
        language.set_locale("vi")
        self.app.processEvents()
        self.assertEqual(page._sign_in.text(), "Đăng nhập")
        self.assertEqual(page._forgot_password.text(), "Quên mật khẩu")
        language.set_locale("en")
        self.app.processEvents()
        self.assertEqual(page._sign_in.text(), "Sign In")
        page.close()

    def test_main_window_switches_pages_without_closing_on_sign_out(self) -> None:
        class FakeOrchestrator:
            is_running = False

            def __init__(self, config, backend):
                self.config = config
                self.backend = backend

            def shutdown(self, timeout=15):
                return True

            def stop(self):
                return None

        profile = AccountControllerTests._profile()
        backend = _FakeBackend(profile)
        controller = AccountController(backend)  # type: ignore[arg-type]
        config = AppConfig.from_toml("config/profiles/windows-device.toml")
        with tempfile.TemporaryDirectory() as temporary:
            with patch("prana_elex.ui.main_window.PipelineOrchestrator", FakeOrchestrator):
                window = MainWindow(config, account_controller=controller, data_root=temporary)
                window._on_account_state(AccountState.SIGNED_OUT, {}, "")
                self.assertIs(window._stack.currentWidget(), window._auth_page)

                window._on_account_state(AccountState.ACTIVE, profile, "")
                self.assertIs(window._stack.currentWidget(), window._translation_page)
                self.assertEqual(window._active_uid, "user-1")

                window._finish_sign_out()
                self.assertIs(window._stack.currentWidget(), window._auth_page)
                self.assertFalse(backend.auth.has_session)
                window.close()


if __name__ == "__main__":
    unittest.main()
