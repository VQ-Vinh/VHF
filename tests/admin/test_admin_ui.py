from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.requests import Request

from services.prana_admin.main import _decode_cursor, _operator, _render, app, templates


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
        plans = [{"id": "starter", "name": "Starter", "monthly_audio_seconds": 6000,
                  "requests_per_minute": 30}]
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
        self.assertIn("Configured plans", plan_html)
        self.assertIn("100", plan_html)

    def test_cursor_rejects_invalid_values(self) -> None:
        self.assertEqual(_decode_cursor("not-a-valid-cursor"), "")


if __name__ == "__main__":
    unittest.main()
