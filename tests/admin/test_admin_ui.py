from __future__ import annotations

import unittest
import inspect
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from services.prana_admin.main import (
    CSRF_COOKIE,
    _decode_cursor,
    _operator,
    _render,
    _csrf_token,
    _station_stop_transition,
    _station_transfer_data,
    app,
    templates,
)


class _PlanSnapshot:
    exists = True

    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return dict(self._data)


class _PlanRef:
    def __init__(self, data):
        self.data = data

    def get(self):
        return _PlanSnapshot(self.data)

    def update(self, updates):
        self.data.update(updates)


class _Collection:
    def __init__(self, db, name):
        self.db = db
        self.name = name

    def document(self, document_id=None):
        if self.name == "plans":
            return self.db.plan_ref
        return _AuditRef(self.db)

    def add(self, value):
        self.db.audit.append(value)


class _AuditRef:
    def __init__(self, db):
        self.db = db


class _Batch:
    def __init__(self, db):
        self.db = db

    def update(self, ref, updates):
        ref.update(updates)

    def set(self, ref, value):
        ref.db.audit.append(value)

    def commit(self):
        return None


class _PlanDb:
    def __init__(self):
        self.plan_ref = _PlanRef({
            "name": "Free", "audio_seconds_limit": 600,
            "requests_per_minute": 30, "max_concurrency": 2,
            "max_devices": 2, "sort_order": 10,
        })
        self.audit = []

    def collection(self, name):
        return _Collection(self, name)

    def batch(self):
        return _Batch(self)


class AdminUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def csrf(self, email: str = "operator@example.com") -> str:
        token = _csrf_token(email)
        self.client.cookies.set(CSRF_COOKIE, token)
        return token

    def test_iap_is_required_and_locale_cookie_is_safe(self) -> None:
        self.assertEqual(self.client.get("/").status_code, 401)
        response = self.client.get("/locale/vi?next=/users", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/users")
        self.assertIn("prana_admin_locale=vi", response.headers["set-cookie"])

        unsafe = self.client.get("/locale/en?next=//example.com", follow_redirects=False)
        self.assertEqual(unsafe.headers["location"], "/")

    def test_development_identity_cannot_bypass_iap_on_cloud_run(self) -> None:
        with patch.dict("os.environ", {"PRANA_ADMIN_ENV": "development", "PRANA_ADMIN_DEV_EMAIL": "dev@example.com"}, clear=True):
            self.assertEqual(_operator(None), "dev@example.com")
        with patch.dict("os.environ", {"PRANA_ADMIN_ENV": "development", "PRANA_ADMIN_DEV_EMAIL": "dev@example.com",
                                        "K_SERVICE": "prana-admin"}, clear=True):
            with self.assertRaises(Exception):
                _operator(None)

    def test_templates_compile_and_dashboard_renders_in_both_languages(self) -> None:
        for name in (
            "base.html", "dashboard.html", "users.html", "user_detail.html",
            "plans.html", "stations.html", "station_detail.html", "audit.html",
            "error.html",
        ):
            templates.get_template(name)

        scope = {"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": [],
                 "scheme": "https", "server": ("testserver", 443)}
        english = _render(Request(scope), "dashboard.html", "operator@example.com", "Dashboard", "dashboard",
                          metrics={"total": 1, "active": 1, "pending": 0, "audio_minutes": 2.5},
                          attention=[], activity=[])
        english_html = english.body.decode()
        self.assertIn("Operations overview", english_html)
        self.assertIn(
            'href="/static/admin.css?v=admin-production-2"',
            english_html,
        )

        vietnamese_scope = dict(scope)
        vietnamese_scope["headers"] = [(b"cookie", b"prana_admin_locale=vi")]
        vietnamese = _render(Request(vietnamese_scope), "dashboard.html", "operator@example.com", "Dashboard",
                             "dashboard", metrics={"total": 1, "active": 1, "pending": 0, "audio_minutes": 2.5},
                             attention=[], activity=[])
        self.assertIn("Tổng quan vận hành", vietnamese.body.decode())

    def test_admin_theme_matches_android_brand_palette(self) -> None:
        css = (
            Path(__file__).resolve().parents[2]
            / "services"
            / "prana_admin"
            / "static"
            / "admin.css"
        ).read_text(encoding="utf-8").lower()

        expected_tokens = {
            "--navy-900": "#0d2b4f",
            "--canvas": "#f2f7fc",
            "--surface": "#ffffff",
            "--text": "#0d2b4f",
            "--text-muted": "#607983",
            "--border": "#d4e2e5",
            "--border-strong": "#b9cdd2",
            "--accent": "#123f7e",
            "--accent-bright": "#4e8fd5",
            "--accent-soft": "#eaf2fb",
            "--danger": "#b12f40",
        }
        for token, value in expected_tokens.items():
            self.assertIn(f"{token}: {value};", css)

        for legacy_teal in ("#087f8c", "#005e68", "#35a5af"):
            self.assertNotIn(legacy_teal, css)
        self.assertIn(
            "outline: 3px solid rgb(18 63 126 / 55%);",
            css,
        )

    def test_admin_brand_and_status_colors_meet_contrast_targets(self) -> None:
        def luminance(color: str) -> float:
            channels = [
                int(color[index : index + 2], 16) / 255
                for index in (1, 3, 5)
            ]
            linear = [
                value / 12.92
                if value <= 0.04045
                else ((value + 0.055) / 1.055) ** 2.4
                for value in channels
            ]
            return (
                0.2126 * linear[0]
                + 0.7152 * linear[1]
                + 0.0722 * linear[2]
            )

        def contrast(foreground: str, background: str) -> float:
            lighter, darker = sorted(
                (luminance(foreground), luminance(background)),
                reverse=True,
            )
            return (lighter + 0.05) / (darker + 0.05)

        pairs = (
            ("#ffffff", "#123f7e"),
            ("#0d2b4f", "#ffffff"),
            ("#607983", "#ffffff"),
            ("#d5e2f0", "#0d2b4f"),
            ("#b9cde5", "#0d2b4f"),
            ("#16704a", "#e3f4eb"),
            ("#8a5708", "#fff2d4"),
            ("#b12f40", "#fbeaec"),
        )
        for foreground, background in pairs:
            self.assertGreaterEqual(
                contrast(foreground, background),
                4.5,
                f"{foreground} on {background}",
            )
        self.assertGreaterEqual(
            contrast("#7d95b8", "#ffffff"),
            3,
            "focus indicator on white",
        )

    def test_operational_pages_render_structured_data(self) -> None:
        scope = {"type": "http", "method": "GET", "path": "/users", "query_string": b"", "headers": [],
                 "scheme": "https", "server": ("testserver", 443)}
        request = Request(scope)
        plans = [{"id": "free", "name": "Free", "monthly_audio_seconds": 600,
                  "audio_seconds_limit": 600, "availability": "available",
                  "requests_per_minute": 30, "max_devices": 2, "max_concurrency": 2}]
        user = {"email": "customer@example.com", "status": "pending_payment", "plan_id": "starter",
                "expires": "2026-08-20 10:00", "email_verified": True}

        users = _render(request, "users.html", "operator@example.com", "Users", "users",
                        users=[{"uid": "uid-1", **user}], plans=plans,
                        statuses=("registered", "email_verified", "pending_payment", "active", "expired", "suspended"),
                        filters={"q": "", "status": "", "plan": ""}, cursor="", first_query="", next_query="")
        users_html = users.body.decode()
        self.assertIn("Pending payment", users_html)
        self.assertIn('class="filter-bar"', users_html)

        detail = _render(request, "user_detail.html", "operator@example.com", "User", "users",
                         uid="uid-1", user=user, plans=plans,
                         devices=[{"id": "device-1", "name": "Bridge PC", "active": True}],
                         usage=[{"period": "2026-07", "minutes": 12.5, "requests": 17}])
        detail_html = detail.body.decode()
        self.assertIn("Account overview", detail_html)
        self.assertIn("Bridge PC", detail_html)

        plan_page = _render(request, "plans.html", "operator@example.com", "Plans", "plans", plans=plans)
        plan_html = plan_page.body.decode()
        self.assertIn("Changes apply immediately", plan_html)
        self.assertIn('action="/plans/free"', plan_html)
        self.assertIn('name="daily_minutes"', plan_html)
        self.assertIn('name="live_log_limit"', plan_html)
        self.assertIn('name="history_unlock_delay_days"', plan_html)
        self.assertIn("data-plan-edit", plan_html)
        self.assertIn("data-plan-form", plan_html)
        self.assertIn('type="submit" data-plan-preview disabled', plan_html)
        self.assertIn('required disabled', plan_html)

    def test_plan_limits_can_be_updated_with_audit(self) -> None:
        db = _PlanDb()
        headers = {"X-Goog-Authenticated-User-Email": "accounts.google.com:operator@example.com"}
        with patch("services.prana_admin.main._db", return_value=db):
            response = self.client.post(
                "/plans/free",
                headers=headers,
                data={
                    "name": "Free Daily", "daily_minutes": 15,
                    "requests_per_minute": 45, "max_concurrency": 3,
                    "max_devices": 2, "sort_order": 10,
                    "live_log_limit": 10, "history_unlock_delay_days": 1,
                    "csrf_token": self.csrf(),
                },
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(db.plan_ref.data["audio_seconds_limit"], 900)
        self.assertEqual(db.plan_ref.data["monthly_audio_seconds"], 900)
        self.assertEqual(db.plan_ref.data["quota_period"], "daily")
        self.assertEqual(db.plan_ref.data["live_log_limit"], 10)
        self.assertEqual(db.plan_ref.data["history_unlock_delay_days"], 1)
        self.assertEqual(db.audit[0]["action"], "plan.update")

        with patch("services.prana_admin.main._db", return_value=db):
            invalid_limit = self.client.post(
                "/plans/free",
                headers=headers,
                data={
                    "name": "Free", "daily_minutes": 10,
                    "requests_per_minute": 30, "max_concurrency": 11,
                    "max_devices": 2, "sort_order": 10,
                    "csrf_token": self.csrf(),
                },
            )
        self.assertEqual(invalid_limit.status_code, 422)
        self.assertEqual(db.plan_ref.data["max_concurrency"], 3)

        invalid = self.client.post(
            "/plans/not-editable",
            headers=headers,
            data={
                "name": "Custom", "daily_minutes": 10,
                "requests_per_minute": 30, "max_concurrency": 2,
                "max_devices": 2, "sort_order": 50,
                "csrf_token": self.csrf(),
            },
        )
        self.assertEqual(invalid.status_code, 404)

    def test_mutations_require_matching_csrf_cookie_and_form_token(self) -> None:
        headers = {
            "X-Goog-Authenticated-User-Email":
                "accounts.google.com:operator@example.com"
        }
        data = {
            "name": "Free", "daily_minutes": 10,
            "requests_per_minute": 30, "max_concurrency": 2,
            "max_devices": 2, "sort_order": 10,
        }
        missing = self.client.post("/plans/free", headers=headers, data=data)
        self.assertEqual(missing.status_code, 422)
        token = self.csrf()
        wrong = self.client.post(
            "/plans/free",
            headers=headers,
            data={**data, "csrf_token": token + "x"},
        )
        self.assertEqual(wrong.status_code, 403)

        other = _csrf_token("other@example.com")
        self.client.cookies.set(CSRF_COOKIE, other)
        wrong_operator = self.client.post(
            "/plans/free",
            headers=headers,
            data={**data, "csrf_token": other},
        )
        self.assertEqual(wrong_operator.status_code, 403)

        expired = _csrf_token("operator@example.com", now=1)
        self.client.cookies.set(CSRF_COOKIE, expired)
        expired_response = self.client.post(
            "/plans/free",
            headers=headers,
            data={**data, "csrf_token": expired},
        )
        self.assertEqual(expired_response.status_code, 403)

    def test_production_requires_non_empty_admin_allowlist(self) -> None:
        with patch.dict(
            "os.environ",
            {"K_SERVICE": "prana-admin", "PRANA_ADMIN_ALLOWED_EMAILS": ""},
            clear=True,
        ):
            with self.assertRaises(Exception):
                _operator("accounts.google.com:operator@example.com")

    def test_admin_uses_plan_collection_atomic_audit_and_aggregate_counts(self) -> None:
        import services.prana_admin.main as admin

        transfer_source = inspect.getsource(admin.transfer_station)
        dashboard_source = inspect.getsource(admin.dashboard)
        status_source = inspect.getsource(admin.set_status)
        self.assertIn('collection("plans")', transfer_source)
        self.assertNotIn('collection("subscription_plans")', transfer_source)
        self.assertIn("_write_audit", transfer_source)
        self.assertIn("_aggregate_count", dashboard_source)
        self.assertNotIn('collection("users").stream()', dashboard_source)
        self.assertIn('not user.get("plan_id")', status_source)

    def test_station_and_audit_templates_render_operational_data(self) -> None:
        scope = {
            "type": "http", "method": "GET", "path": "/stations",
            "query_string": b"", "headers": [], "scheme": "https",
            "server": ("testserver", 443),
        }
        request = Request(scope)
        station = {
            "id": "station-1", "name": "Bridge", "owner_email": "owner@example.com",
            "online": False, "last_error": "AUDIO_DEVICE_UNAVAILABLE",
            "capture_state": "error", "last_seen": "2026-07-28 10:00",
            "platform": "Windows", "desired_state": {"generation": 3},
            "observed_generation": 2,
        }
        listing = _render(
            request, "stations.html", "operator@example.com", "Stations",
            "stations", stations=[station],
            filters={"q": "", "state": "", "platform": "", "error": ""},
            cursor="", first_query="", next_query="",
        )
        self.assertIn("Bridge", listing.body.decode())
        audit = _render(
            request, "audit.html", "operator@example.com", "Audit", "audit",
            entries=[{
                "action": "station.stop", "operator": "operator@example.com",
                "when": "2026-07-28", "target_uid": "uid-1",
                "details_json": '{"station_id":"station-1"}',
            }],
            filters={
                "operator_filter": "", "action": "", "target": "",
                "date_from": "", "date_to": "",
            },
            cursor="", first_query="", next_query="",
        )
        self.assertIn("Station stop requested", audit.body.decode())

    def test_cursor_rejects_invalid_values(self) -> None:
        self.assertEqual(_decode_cursor("not-a-valid-cursor"), "")

    def test_station_transfer_stops_capture_and_resets_projection(self) -> None:
        ready, stop_update = _station_stop_transition(
            {
                "capture_state": "recording",
                "observed_generation": 7,
                "desired_state": {"running": True, "generation": 7, "target_language": "vi"},
            }
        )
        self.assertFalse(ready)
        self.assertFalse(stop_update["desired_state"]["running"])
        self.assertEqual(stop_update["desired_state"]["generation"], 8)

        ready, repeated_update = _station_stop_transition(
            {
                "capture_state": "recording",
                "observed_generation": 7,
                "desired_state": {"running": False, "generation": 8, "target_language": "vi"},
            }
        )
        self.assertFalse(ready)
        self.assertIsNone(repeated_update)

        ready, stop_update = _station_stop_transition(
            {
                "capture_state": "idle",
                "observed_generation": 8,
                "desired_state": {"running": False, "generation": 8, "target_language": "vi"},
            }
        )
        self.assertTrue(ready)
        self.assertIsNone(stop_update)

        registry_update, projection = _station_transfer_data(
            "station-1",
            {
                "name": "Bridge Pi", "platform": "Linux aarch64",
                "desired_state": {"running": False, "generation": 8, "target_language": "vi"},
            },
        )
        self.assertFalse(registry_update["desired_state"]["running"])
        self.assertEqual(registry_update["desired_state"]["generation"], 8)
        self.assertEqual(projection["station_id"], "station-1")
        self.assertFalse(projection["online"])


if __name__ == "__main__":
    unittest.main()
