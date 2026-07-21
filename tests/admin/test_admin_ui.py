from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from services.prana_admin.main import _decode_cursor, _operator, _render, app, templates


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
        return self.db.plan_ref

    def add(self, value):
        self.db.audit.append(value)


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


class AdminUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

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
        for name in ("base.html", "dashboard.html", "users.html", "user_detail.html", "plans.html"):
            templates.get_template(name)

        scope = {"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": [],
                 "scheme": "https", "server": ("testserver", 443)}
        english = _render(Request(scope), "dashboard.html", "operator@example.com", "Dashboard", "dashboard",
                          metrics={"total": 1, "active": 1, "pending": 0, "audio_minutes": 2.5},
                          attention=[], activity=[])
        self.assertIn("Operations overview", english.body.decode())

        vietnamese_scope = dict(scope)
        vietnamese_scope["headers"] = [(b"cookie", b"prana_admin_locale=vi")]
        vietnamese = _render(Request(vietnamese_scope), "dashboard.html", "operator@example.com", "Dashboard",
                             "dashboard", metrics={"total": 1, "active": 1, "pending": 0, "audio_minutes": 2.5},
                             attention=[], activity=[])
        self.assertIn("Tổng quan vận hành", vietnamese.body.decode())

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
                },
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(db.plan_ref.data["audio_seconds_limit"], 900)
        self.assertEqual(db.plan_ref.data["monthly_audio_seconds"], 900)
        self.assertEqual(db.plan_ref.data["quota_period"], "daily")
        self.assertEqual(db.audit[0]["action"], "plan.update")

        with patch("services.prana_admin.main._db", return_value=db):
            invalid_limit = self.client.post(
                "/plans/free",
                headers=headers,
                data={
                    "name": "Free", "daily_minutes": 10,
                    "requests_per_minute": 30, "max_concurrency": 11,
                    "max_devices": 2, "sort_order": 10,
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
            },
        )
        self.assertEqual(invalid.status_code, 404)

    def test_cursor_rejects_invalid_values(self) -> None:
        self.assertEqual(_decode_cursor("not-a-valid-cursor"), "")


if __name__ == "__main__":
    unittest.main()
