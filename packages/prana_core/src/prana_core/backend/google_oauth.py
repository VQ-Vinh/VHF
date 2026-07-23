from __future__ import annotations

import base64
import hashlib
import html
import secrets
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse


GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
class GoogleOAuthError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GoogleOAuthAuthorization:
    code: str
    code_verifier: str
    redirect_uri: str


class _LoopbackServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, state: str):
        self.expected_state = state
        self.authorization_code = ""
        self.oauth_error = ""
        self.completed = threading.Event()
        super().__init__(("127.0.0.1", 0), _CallbackHandler)


class _CallbackHandler(BaseHTTPRequestHandler):
    server: _LoopbackServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path != "/oauth2/callback":
            self._respond(404, "PRANA ELEX", "This callback URL is not valid.")
            return

        values = parse_qs(parsed.query)
        if values.get("state", [""])[0] != self.server.expected_state:
            self._respond(400, "PRANA ELEX", "The sign-in request could not be verified.")
            return

        error = values.get("error", [""])[0]
        code = values.get("code", [""])[0]
        if error:
            self.server.oauth_error = error
            self.server.completed.set()
            self._respond(400, "Google sign-in cancelled", "Return to the PRANA ELEX app.")
            return
        if not code:
            self._respond(400, "PRANA ELEX", "Google did not return an authorization code.")
            return

        self.server.authorization_code = code
        self.server.completed.set()
        self._respond(200, "Google sign-in complete", "You can close this tab and return to PRANA ELEX.")

    def log_message(self, _format: str, *_args) -> None:
        return

    def _respond(self, status: int, title: str, message: str) -> None:
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta http-equiv='Cache-Control' content='no-store'>"
            "<style>body{margin:0;background:#eaf1f4;color:#102f3a;font-family:Arial,sans-serif;}"
            ".card{max-width:520px;margin:12vh auto;padding:32px;background:#fff;border:1px solid #c9d8df;"
            "border-radius:16px;box-shadow:0 16px 40px rgba(16,47,58,.12)}"
            "h1{font-size:24px;margin:0 0 12px}p{line-height:1.55;color:#48636e}</style>"
            f"<title>{html.escape(title)}</title></head><body><main class='card'>"
            f"<h1>{html.escape(title)}</h1><p>{html.escape(message)}</p>"
            "</main></body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class GoogleOAuthSession:
    def __init__(
        self,
        client_id: str,
        timeout: float = 300.0,
    ):
        if not client_id.endswith(".apps.googleusercontent.com"):
            raise GoogleOAuthError("GOOGLE_OAUTH_NOT_CONFIGURED", "Google sign-in is not configured")
        self.client_id = client_id
        self.timeout = timeout
        self._state = secrets.token_urlsafe(32)
        self._code_verifier = secrets.token_urlsafe(64)
        self._cancelled = threading.Event()
        self._cancel_code = "GOOGLE_AUTH_CANCELLED"
        self._cancel_message = "Google sign-in was cancelled"
        try:
            self._server = _LoopbackServer(self._state)
        except OSError as exc:
            raise GoogleOAuthError(
                "GOOGLE_CALLBACK_UNAVAILABLE",
                "PRANA ELEX could not open the local Google sign-in callback",
            ) from exc
        self._server.timeout = 0.25
        self.redirect_uri = f"http://127.0.0.1:{self._server.server_port}/oauth2/callback"
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(self._code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        self.authorization_url = f"{GOOGLE_AUTHORIZATION_URL}?{urlencode({
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'state': self._state,
            'prompt': 'select_account',
            'access_type': 'online',
        })}"

    def wait(self) -> GoogleOAuthAuthorization:
        deadline = time.monotonic() + self.timeout
        try:
            while not self._server.completed.is_set():
                if self._cancelled.is_set():
                    raise GoogleOAuthError(self._cancel_code, self._cancel_message)
                if time.monotonic() >= deadline:
                    raise GoogleOAuthError("GOOGLE_AUTH_TIMEOUT", "Google sign-in timed out")
                self._server.handle_request()

            if self._server.oauth_error:
                code = (
                    "GOOGLE_AUTH_CANCELLED"
                    if self._server.oauth_error == "access_denied"
                    else "GOOGLE_AUTH_FAILED"
                )
                raise GoogleOAuthError(code, "Google sign-in was cancelled or denied")
            return GoogleOAuthAuthorization(
                code=self._server.authorization_code,
                code_verifier=self._code_verifier,
                redirect_uri=self.redirect_uri,
            )
        finally:
            self._server.server_close()

    def cancel(
        self,
        code: str = "GOOGLE_AUTH_CANCELLED",
        message: str = "Google sign-in was cancelled",
    ) -> None:
        self._cancel_code = code
        self._cancel_message = message
        self._cancelled.set()

__all__ = [
    "GoogleOAuthAuthorization",
    "GoogleOAuthError",
    "GoogleOAuthSession",
]
