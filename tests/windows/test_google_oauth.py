from __future__ import annotations

import threading
import time
import unittest
import unittest.mock
from urllib.parse import parse_qs, urlparse

import httpx

from prana_core.backend import google_oauth
from prana_core.backend.auth import FirebaseAuthClient
from prana_core.backend.client import BackendClient
from prana_core.backend.google_oauth import (
    GoogleOAuthAuthorization,
    GoogleOAuthError,
    GoogleOAuthSession,
)


CLIENT_ID = "123456789-example.apps.googleusercontent.com"


class MemoryStore:
    def __init__(self):
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def delete(self, key: str) -> None:
        self.values.pop(key, None)


class GoogleOAuthTests(unittest.TestCase):
    def test_authorization_uses_pkce_loopback_and_account_chooser(self) -> None:
        session = GoogleOAuthSession(CLIENT_ID, timeout=0.01)
        query = parse_qs(urlparse(session.authorization_url).query)
        self.assertEqual(urlparse(session.redirect_uri).hostname, "127.0.0.1")
        self.assertEqual(query["scope"], ["openid email profile"])
        self.assertEqual(query["prompt"], ["select_account"])
        self.assertEqual(query["access_type"], ["online"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertNotIn("client_secret", query)
        session.cancel()
        with self.assertRaisesRegex(GoogleOAuthError, "cancelled"):
            session.wait()

    def test_callback_rejects_bad_state_and_returns_code_for_backend(self) -> None:
        session = GoogleOAuthSession(CLIENT_ID, timeout=2)
        state = parse_qs(urlparse(session.authorization_url).query)["state"][0]
        results: list[GoogleOAuthAuthorization] = []

        worker = threading.Thread(target=lambda: results.append(session.wait()))
        worker.start()
        time.sleep(0.05)
        bad = httpx.get(f"{session.redirect_uri}?state=wrong&code=bad", timeout=2)
        self.assertEqual(bad.status_code, 400)
        self.assertTrue(worker.is_alive())
        good = httpx.get(
            f"{session.redirect_uri}?state={state}&code=one-time-code", timeout=2
        )
        self.assertEqual(good.status_code, 200)
        self.assertNotIn("one-time-code", good.text)
        worker.join(2)

        self.assertEqual(results[0].code, "one-time-code")
        self.assertEqual(results[0].redirect_uri, session.redirect_uri)
        self.assertGreaterEqual(len(results[0].code_verifier), 43)

    def test_timeout_port_and_browser_failures_have_stable_codes(self) -> None:
        session = GoogleOAuthSession(CLIENT_ID, timeout=0)
        with self.assertRaises(GoogleOAuthError) as timed_out:
            session.wait()
        self.assertEqual(timed_out.exception.code, "GOOGLE_AUTH_TIMEOUT")

        with unittest.mock.patch.object(
            google_oauth,
            "_LoopbackServer",
            side_effect=OSError("port unavailable"),
        ):
            with self.assertRaises(GoogleOAuthError) as unavailable:
                GoogleOAuthSession(CLIENT_ID)
        self.assertEqual(unavailable.exception.code, "GOOGLE_CALLBACK_UNAVAILABLE")

        session = GoogleOAuthSession(CLIENT_ID, timeout=1)
        session.cancel("GOOGLE_BROWSER_FAILED", "Browser failed")
        with self.assertRaises(GoogleOAuthError) as failed:
            session.wait()
        self.assertEqual(failed.exception.code, "GOOGLE_BROWSER_FAILED")


class FirebaseGoogleSessionTests(unittest.TestCase):
    def test_only_firebase_session_is_persisted(self) -> None:
        store = MemoryStore()
        auth = FirebaseAuthClient("firebase-key", store=store)  # type: ignore[arg-type]
        created = auth.accept_firebase_session(
            {
                "id_token": "firebase-id",
                "refresh_token": "firebase-refresh",
                "expires_in": 3600,
                "email": "user@gmail.com",
                "is_new_user": True,
            }
        )
        self.assertTrue(created)
        self.assertEqual(
            store.values,
            {"refresh_token": "firebase-refresh", "email": "user@gmail.com"},
        )
        self.assertNotIn("google", str(store.values).lower())

    def test_backend_client_sends_pkce_material_and_accepts_firebase_session(self) -> None:
        backend = BackendClient("https://api.example.com", "firebase-key")
        store = MemoryStore()
        backend.auth.store = store  # type: ignore[assignment]
        authorization = GoogleOAuthAuthorization(
            code="one-time-code",
            code_verifier="v" * 64,
            redirect_uri="http://127.0.0.1:4567/oauth2/callback",
        )
        response = httpx.Response(
            200,
            json={
                "id_token": "firebase-id",
                "refresh_token": "firebase-refresh",
                "expires_in": 3600,
                "email": "user@gmail.com",
                "is_new_user": False,
            },
        )
        with unittest.mock.patch(
            "prana_core.backend.client.httpx.post", return_value=response
        ) as post:
            self.assertFalse(backend.sign_in_with_google(authorization))
        request = post.call_args
        self.assertEqual(
            request.args[0], "https://api.example.com/v1/auth/google/exchange"
        )
        self.assertEqual(request.kwargs["json"]["code_verifier"], "v" * 64)
        self.assertNotIn("client_secret", request.kwargs["json"])
        self.assertEqual(store.get("refresh_token"), "firebase-refresh")


if __name__ == "__main__":
    unittest.main()
