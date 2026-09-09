"""Render synthetic UI fixtures without connecting to Firebase or an API.

Run from the repo root: python -m tests.admin.responsive_fixtures
"""
from pathlib import Path
from shutil import copytree
import re
from html import escape, unescape
from urllib.parse import urlsplit

from starlette.requests import Request

from services.prana_admin.main import _error_response, _render


def preview_html(body: bytes, locale: str, page: str) -> bytes:
    """Resolve navigation to fixture files, without changing deployed templates."""
    def replace_link(match: re.Match[str]) -> str:
        target = urlsplit(unescape(match.group(2)))
        selected_locale = locale
        if target.path.startswith('/locale/'):
            selected_locale = target.path.rsplit('/', 1)[-1]
            destination = page
        elif target.path == '/':
            destination = 'dashboard'
        elif target.path in ('/users', '/stations', '/plans', '/audit'):
            destination = target.path[1:]
        elif target.path.startswith('/users/'):
            destination = 'user_detail'
        elif target.path.startswith('/stations/'):
            destination = 'station_detail'
        else:
            return match.group(0)
        return f'{match.group(1)}"/{escape(selected_locale)}-{destination}.html"'

    html = re.sub(r'(<a\b[^>]*?\bhref=)"([^"]*)"', replace_link, body.decode('utf-8'))
    return html.encode('utf-8')


def render_fixtures(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    copytree(Path("services/prana_admin/static"), output / "static", dirs_exist_ok=True)
    email = "synthetic.operator.with.a.long.account.name@example.invalid"
    station = {
        "id": "station-" + "x" * 80, "name": "Synthetic station with a long display name for responsive testing",
        "owner_email": email, "online": False, "active": True,
        "last_error": "AUDIO_DEVICE_UNAVAILABLE", "capture_state": "error",
        "last_seen": "2026-09-08 10:00", "platform": "Linux",
        "desired_state": {"generation": 3}, "observed_generation": 2,
        "storage_prefix": "stations/" + "x" * 100,
    }
    activity = [{"action": "station.stop", "operator": email, "when": "2026-09-08 10:00",
                 "target_uid": "u" * 80, "details_json": '{"station_id":"' + "x" * 100 + '"}'}]
    plans = [{"id": "free", "name": "Synthetic Free Plan", "monthly_audio_seconds": 600,
              "audio_seconds_limit": 600, "availability": "available", "requests_per_minute": 30,
              "max_devices": 2, "max_concurrency": 2, "max_stations": 2, "sort_order": 10,
              "history_past_days": 7, "tx_max_recording_seconds": 60}]
    user = {"email": email, "status": "pending_payment", "plan_id": "free",
            "expires": "2026-09-20 10:00", "email_verified": True}
    pagination = {"cursor": "", "first_query": "", "next_query": ""}
    pages = {
        "dashboard": {"metrics": {"total": 1234, "active": 1000, "pending": 234, "audio_minutes": 12345.6},
                      "attention": [station], "activity": activity},
        "users": {"users": [{"uid": "u" * 80, **user}], "plans": plans,
                  "statuses": ("registered", "pending_payment", "active", "suspended"),
                  "filters": {"q": "", "status": "", "plan": ""}, **pagination},
        "user_detail": {"uid": "u" * 80, "user": user, "plans": plans, "stations": [station],
                        "devices": [{"id": "d" * 80, "name": station["name"], "active": False}],
                        "usage": [{"period": "2026-09", "minutes": 1234.5, "requests": 17000}],
                        "timeline": activity},
        "stations": {"stations": [station], "filters": {"q": "", "state": "", "platform": "", "error": ""}, **pagination},
        "station_detail": {"station": station, "transfers": activity},
        "plans": {"plans": plans},
        "audit": {"entries": activity, "filters": {"operator_filter": "", "action": "", "target": "",
                  "date_from": "", "date_to": ""}, **pagination},
    }
    for locale in ("vi", "en"):
        request = Request({"type": "http", "method": "GET", "path": "/", "query_string": b"",
                           "headers": [(b"cookie", f"prana_admin_locale={locale}".encode())],
                           "scheme": "http", "server": ("localhost", 8875)})
        for name, context in pages.items():
            active_nav = {'user_detail': 'users', 'station_detail': 'stations'}.get(name, name)
            response = _render(request, name + ".html", email, name, active_nav, **context)
            (output / f"{locale}-{name}.html").write_bytes(preview_html(response.body, locale, name))
        error = _error_response(request, 403, "Synthetic error")
        (output / f"{locale}-error.html").write_bytes(preview_html(error.body, locale, 'error'))


if __name__ == "__main__":
    render_fixtures(Path("build/buildapp/responsive-web"))
