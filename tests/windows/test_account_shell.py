from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


from prana_core.backend.auth import FirebaseAuthClient, FirebaseAuthError
from prana_core.backend.client import BackendApiError, BackendClient
from prana_core.storage.account import prepare_data_root

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QSignalSpy
    from prana_core.config.schema import AppConfig
    from prana_windows.ui.account import AccountController, AccountState
    from prana_windows.ui.components.chat_feed import ChatFeed
    from prana_windows.ui.pages.account import AuthPage
    from prana_windows.ui.pages.account_center import AccountCenterPage
    from prana_windows.ui.pages.plans import PlansPage
    from prana_windows.ui.i18n import language
    from prana_windows.ui.main_window import MainWindow
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
    AccountCenterPage = None  # type: ignore[assignment]
    PlansPage = None  # type: ignore[assignment]
    ChatFeed = None  # type: ignore[assignment]
    QSignalSpy = None  # type: ignore[assignment]


class _FakeAuth:
    def __init__(self, has_session: bool = True):
        self.has_session = has_session
        self.email = "user@example.com"
        self.google_enabled = False

    def sign_out(self) -> None:
        self.has_session = False

    def provider_ids(self) -> list[str]:
        return []


class _FakeBackend:
    def __init__(self, profile: dict | None = None, error: Exception | None = None):
        self.auth = _FakeAuth()
        self.profile = profile or {}
        self.error = error
        self.registered = False
        self.devices = [
            {
                "id": "device-current",
                "name": "Current PC",
                "platform": "Windows AMD64",
                "active": True,
            }
        ]
        self.revoked: list[str] = []
        self.me_calls = 0

    @property
    def local_device_id(self) -> str:
        return "device-current"

    def me(self) -> dict:
        self.me_calls += 1
        if self.error:
            raise self.error
        return self.profile

    def ensure_device(self):
        if self.error:
            raise self.error
        self.registered = True
        return object()

    def list_devices(self) -> list[dict]:
        if self.error:
            raise self.error
        return self.devices

    def revoke_device(self, device_id: str) -> None:
        self.revoked.append(device_id)
        for device in self.devices:
            if device["id"] == device_id:
                device["active"] = False

    def list_plans(self) -> list[dict]:
        return [
            {"id": "free", "name": "Free", "audio_seconds_limit": 600,
             "quota_period": "daily", "availability": "available", "sort_order": 10,
             "requests_per_minute": 30, "max_concurrency": 2, "max_devices": 2},
            {"id": "plus", "name": "Plus", "audio_seconds_limit": 3600,
             "quota_period": "daily", "availability": "coming_soon", "sort_order": 20,
             "requests_per_minute": 30, "max_concurrency": 2, "max_devices": 2},
            {"id": "pro", "name": "Pro", "audio_seconds_limit": 10800,
             "quota_period": "daily", "availability": "coming_soon", "sort_order": 30,
             "requests_per_minute": 30, "max_concurrency": 2, "max_devices": 2},
        ]

    def select_plan(self, plan_id: str) -> dict:
        self.profile = {**self.profile, "status": "active", "plan_id": plan_id}
        return self.profile

    def reset_registration(self) -> None:
        self.registered = False

    def sign_out(self) -> None:
        self.auth.sign_out()
        self.registered = False


@unittest.skipIf(AccountController is None, "PySide6 is not installed in this test environment")
class AccountControllerTests(unittest.TestCase):
    @staticmethod
    def _wait_for_spy(spy, count: int = 1) -> None:
        deadline = time.monotonic() + 1.0
        while spy.count() < count and time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.01)
        if spy.count() < count:
            raise AssertionError(f"Expected {count} signal emissions, got {spy.count()}")

    @staticmethod
    def _profile(status: str = "active", verified: bool = True) -> dict:
        return {
            "uid": "user-1",
            "email": "user@example.com",
            "email_verified": verified,
            "status": status,
            "plan_id": "starter",
            "usage": {
                "used_audio_seconds": 60,
                "remaining_audio_seconds": 540,
                "monthly_audio_seconds": 600,
            },
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

    def test_expired_auth_returns_to_login(self) -> None:
        backend = _FakeBackend(error=FirebaseAuthError("Session expired"))
        controller = AccountController(backend)  # type: ignore[arg-type]
        controller._load_profile()
        self.assertEqual(controller.state, AccountState.SIGNED_OUT)
        self.assertFalse(backend.auth.has_session)

    def test_account_center_loads_details_without_losing_session_on_network_error(self) -> None:
        app = QApplication.instance() or QApplication([])
        backend = _FakeBackend(self._profile())
        controller = AccountController(backend)  # type: ignore[arg-type]
        changed = QSignalSpy(controller.details_changed)
        loading = QSignalSpy(controller.details_loading)
        controller.load_account_center()
        self._wait_for_spy(changed)
        self._wait_for_spy(loading, 2)
        self.assertEqual(changed.at(0)[0]["email"], "user@example.com")
        self.assertEqual(changed.at(0)[1][0]["id"], "device-current")
        self.assertEqual(changed.at(0)[2], [])

        backend.error = BackendApiError("NETWORK_ERROR", "offline")
        errors = QSignalSpy(controller.details_error)
        controller.load_account_center()
        self._wait_for_spy(errors)
        self._wait_for_spy(loading, 4)
        self.assertTrue(backend.auth.has_session)

        backend.error = FirebaseAuthError("Session expired")
        states = QSignalSpy(controller.state_changed)
        controller.load_account_center()
        self._wait_for_spy(states)
        self.assertEqual(controller.state, AccountState.SIGNED_OUT)
        self.assertFalse(backend.auth.has_session)
        self.assertIsNotNone(app)

    def test_password_reset_uses_firebase_oob_flow(self) -> None:
        auth = FirebaseAuthClient("public-api-key")
        with patch.object(auth, "_identity", return_value={}) as identity:
            auth.request_password_reset("user@example.com")
        identity.assert_called_once_with(
            "sendOobCode", {"requestType": "PASSWORD_RESET", "email": "user@example.com"}
        )

    def test_plan_polling_does_not_reload_profile(self) -> None:
        app = QApplication.instance() or QApplication([])
        backend = _FakeBackend(self._profile())
        controller = AccountController(backend)  # type: ignore[arg-type]
        changed = QSignalSpy(controller.plans_changed)
        controller.load_plans()
        self._wait_for_spy(changed)
        self.assertEqual(backend.me_calls, 0)
        self.assertEqual(changed.at(0)[1][0]["id"], "free")
        self.assertIsNotNone(app)

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
        page = AuthPage(google_enabled=True)
        language.set_locale("vi")
        self.app.processEvents()
        self.assertEqual(page._sign_in.text(), "Đăng nhập")
        self.assertEqual(page._forgot_password.text(), "Quên mật khẩu")
        self.assertEqual(page._google.text(), "Tiếp tục với Google")
        language.set_locale("en")
        self.app.processEvents()
        self.assertEqual(page._sign_in.text(), "Sign In")
        self.assertEqual(page._google.text(), "Continue with Google")
        page.close()

    def test_google_button_is_shared_and_supports_cancel_state(self) -> None:
        page = AuthPage(google_enabled=True)
        requested = QSignalSpy(page.google_requested)
        cancelled = QSignalSpy(page.google_cancel_requested)
        page._google.click()
        self.assertEqual(requested.count(), 1)
        page.set_google_waiting(True)
        self.assertTrue(page._cancel_google.isVisible() or not page.isVisible())
        self.assertEqual(page._google.text(), "Waiting for Google sign-in…")
        page._cancel_google.click()
        self.assertEqual(cancelled.count(), 1)
        page.set_google_waiting(False)
        self.assertTrue(page._cancel_google.isHidden())
        page.close()

    def test_registration_password_policy_blocks_invalid_passwords(self) -> None:
        page = AuthPage()
        spy = QSignalSpy(page.sign_up_requested)
        page._register_email.setText("user@example.com")

        invalid_passwords = [
            "Ab1!",
            "abcdef!",
            "ABCDEF!",
            "Abcdef1",
            "12345!",
            "Abc1 x",
        ]
        for password in invalid_passwords:
            page._register_password.setText(password)
            self.assertFalse(page._create.isEnabled(), password)
            page._emit_sign_up()
        self.assertEqual(spy.count(), 0)

        page._register_password.setText("Abc1!x")
        self.assertTrue(page._create.isEnabled())
        self.assertTrue(all(page._password_checks("Ábc1!x").values()))
        page._emit_sign_up()
        self.assertEqual(spy.count(), 1)

        language.set_locale("vi")
        self.app.processEvents()
        self.assertIn("chữ cái viết hoa", page._password_requirements.text())
        language.set_locale("en")
        page.close()

    def test_translation_status_bar_does_not_show_latency(self) -> None:
        feed = ChatFeed()
        self.assertFalse(hasattr(feed, "_latency_label"))
        self.assertIsNotNone(feed._listening_label)
        self.assertIsNotNone(feed._gcs_label)
        feed.close()

    def test_account_center_localizes_usage_and_protects_current_device(self) -> None:
        page = AccountCenterPage(google_enabled=True)
        profile = AccountControllerTests._profile()
        devices = [
            {"id": "device-current", "name": "Current", "platform": "Windows", "active": True},
            {"id": "device-other", "name": "Other", "platform": "Linux", "active": True},
            {"id": "device-old", "name": "Old", "platform": "Windows", "active": False},
        ]
        page.set_profile(profile, devices, "device-current", ["password"])
        revoke_ids = {
            button.property("device_id")
            for button in page.findChildren(type(page._refresh))
            if button.property("device_id")
        }
        self.assertEqual(revoke_ids, {"device-other"})
        self.assertFalse(page._back.isHidden())
        self.assertIn("10.0 min total", page._usage_text.text())
        self.assertEqual(page._password_status.text(), "Available")
        self.assertFalse(page._link_google.isHidden())
        page.set_profile(profile, devices, "device-current", ["google.com", "password"])
        self.assertTrue(page._link_google.isHidden())
        self.assertEqual(page._google_status.text(), "Linked")

        language.set_locale("vi")
        self.app.processEvents()
        self.assertEqual(page._title.text(), "Trung tâm tài khoản")
        self.assertIn("Tổng 10.0 phút", page._usage_text.text())
        language.set_locale("en")
        page.set_profile(AccountControllerTests._profile("suspended"), devices, "device-current")
        self.assertTrue(page._back.isHidden())
        page.close()

    def test_plans_page_shows_current_and_disables_unreleased_tiers(self) -> None:
        page = PlansPage()
        plans = _FakeBackend().list_plans()
        page.set_data({"plan_id": "free"}, plans)
        buttons = page.findChildren(type(page._refresh))
        labels = [button.text() for button in buttons]
        self.assertIn("Your current plan", labels)
        self.assertEqual(labels.count("Coming soon"), 2)
        self.assertEqual(len(page.findChildren(type(page._title), "PlanName")), 3)
        values = {
            (label.property("plan_id"), label.property("field")): label.text()
            for label in page.findChildren(type(page._title), "PlanDetailValue")
        }
        self.assertEqual(values[("free", "requests_per_minute")], "30")
        self.assertEqual(values[("plus", "max_concurrency")], "2")
        self.assertEqual(values[("pro", "max_devices")], "2")

        updated = [dict(plan) for plan in plans]
        updated[0].update({
            "name": "Free Updated", "audio_seconds_limit": 1_200,
            "requests_per_minute": 40, "max_concurrency": 3,
            "max_devices": 4, "sort_order": 40,
        })
        page.set_data({"plan_id": "free"}, updated)
        self.app.processEvents()
        self.assertEqual(page._plans[0]["id"], "plus")
        self.assertEqual(page._plans[-1]["name"], "Free Updated")
        free_values = {
            label.property("field"): label.text()
            for label in page._card_widgets[-1].findChildren(
                type(page._title), "PlanDetailValue"
            )
        }
        self.assertEqual(free_values, {
            "requests_per_minute": "40",
            "max_concurrency": "3",
            "max_devices": "4",
        })

        page.resize(1_120, 720)
        page.show()
        self.app.processEvents()
        self.assertEqual(page._column_count, 3)
        page.resize(760, 720)
        self.app.processEvents()
        self.assertEqual(page._column_count, 2)
        page.resize(540, 720)
        self.app.processEvents()
        self.assertEqual(page._column_count, 1)
        page.set_message("Offline", True)
        self.assertEqual(len(page._card_widgets), 3)
        language.set_locale("vi")
        self.app.processEvents()
        self.assertIn("Chọn gói", page._title.text())
        language.set_locale("en")
        page.close()



    def test_main_window_switches_console_pages_without_closing_on_sign_out(self) -> None:
        """The console has no local pipeline; page flow is all that changes."""
        profile = AccountControllerTests._profile()
        profile["fleet_operator"] = True
        backend = _FakeBackend(profile)
        controller = AccountController(backend)  # type: ignore[arg-type]
        config = AppConfig.from_toml("apps/windows/config/default.toml")
        window = MainWindow(config, account_controller=controller)

        window._on_account_state(AccountState.SIGNED_OUT, {}, "")
        self.assertIs(window._stack.currentWidget(), window._auth_page)

        window._on_account_state(AccountState.ACTIVE, profile, "")
        controller.state = AccountState.ACTIVE
        self.assertIs(window._stack.currentWidget(), window._fleet_page)

        with patch.object(controller, "load_account_center") as load_details:
            window.open_account_center()
            self.assertIs(window._stack.currentWidget(), window._account_center)
            load_details.assert_called_once()
            window._close_account_center()
            self.assertIs(window._stack.currentWidget(), window._fleet_page)

            with patch.object(controller, "load_plans") as load_plans:
                window.open_plans()
                self.assertIs(window._stack.currentWidget(), window._plans_page)
                load_plans.assert_called_once()
            window._back_to_account_center()
            self.assertIs(window._stack.currentWidget(), window._account_center)
            window._close_account_center()

            window._on_account_state(
                AccountState.RESTRICTED,
                AccountControllerTests._profile("suspended"),
                "",
            )
            self.assertIs(window._stack.currentWidget(), window._account_center)
            self.assertTrue(window._account_center._back.isHidden())

        window._finish_sign_out()
        self.assertIs(window._stack.currentWidget(), window._auth_page)
        self.assertFalse(backend.auth.has_session)
        window.close()

    def test_account_without_operator_rights_gets_an_explanation(self) -> None:
        """A valid non-operator account is a normal state, not an error."""
        profile = AccountControllerTests._profile()
        profile["fleet_operator"] = False
        backend = _FakeBackend(profile)
        controller = AccountController(backend)  # type: ignore[arg-type]
        config = AppConfig.from_toml("apps/windows/config/default.toml")
        window = MainWindow(config, account_controller=controller)
        window._on_account_state(AccountState.ACTIVE, profile, "")
        self.assertIs(window._stack.currentWidget(), window._not_operator_page)
        window.close()


if __name__ == "__main__":
    unittest.main()
