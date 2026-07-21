from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.prana_api.auth import FirebaseSession, Identity, require_firebase_session
from services.prana_api.config import Settings
from services.prana_api.google_auth import (
    AuthRateLimiter,
    FirestoreAuthRateLimiter,
    GoogleAuthBroker,
)
from services.prana_api.main import (
    app,
    enforce_google_auth_rate,
    get_google_auth_broker,
)
from services.prana_api.models import FirebaseSessionResponse, GoogleAuthorizationRequest


AUTHORIZATION = GoogleAuthorizationRequest(
    code="one-time-code",
    code_verifier="v" * 64,
    redirect_uri="http://127.0.0.1:4567/oauth2/callback",
)


class GoogleAuthBrokerTests(unittest.TestCase):
    def _settings(self) -> Settings:
        return Settings(
            firebase_web_api_key="firebase-key",
            google_desktop_oauth_client_id=(
                "123456789-example.apps.googleusercontent.com"
            ),
            google_desktop_oauth_client_secret="desktop-secret",
        )

    def test_exchange_keeps_secret_server_side_and_returns_firebase_session(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(
                    200,
                    json={"id_token": "google-id", "access_token": "google-access"},
                )
            if request.url.host == "openidconnect.googleapis.com":
                return httpx.Response(
                    200,
                    json={"email": "user@gmail.com", "email_verified": True},
                )
            return httpx.Response(
                200,
                json={
                    "idToken": "firebase-id",
                    "refreshToken": "firebase-refresh",
                    "expiresIn": "3600",
                    "email": "user@gmail.com",
                    "localId": "uid-1",
                    "isNewUser": True,
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        response = GoogleAuthBroker(self._settings(), client).exchange(AUTHORIZATION)
        client.close()

        token_body = requests[0].content.decode("utf-8")
        self.assertIn("client_secret=desktop-secret", token_body)
        self.assertIn("code_verifier=", token_body)
        self.assertEqual(response.refresh_token, "firebase-refresh")
        self.assertNotIn("google-access", response.model_dump_json())
        self.assertNotIn("desktop-secret", response.model_dump_json())

    def test_link_rejects_different_email_before_firebase(self) -> None:
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.host == "oauth2.googleapis.com":
                return httpx.Response(
                    200,
                    json={"id_token": "google-id", "access_token": "google-access"},
                )
            return httpx.Response(
                200,
                json={"email": "different@gmail.com", "email_verified": True},
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        with self.assertRaises(HTTPException) as mismatch:
            GoogleAuthBroker(self._settings(), client).exchange(
                AUTHORIZATION,
                firebase_id_token="firebase-id",
                expected_email="user@gmail.com",
            )
        client.close()
        self.assertEqual(mismatch.exception.detail["code"], "GOOGLE_EMAIL_MISMATCH")
        self.assertEqual(len(requests), 2)

    def test_request_validation_and_rate_limit(self) -> None:
        with self.assertRaises(ValidationError):
            GoogleAuthorizationRequest(
                code="code",
                code_verifier="!" * 64,
                redirect_uri="https://attacker.example/callback",
            )
        limiter = AuthRateLimiter(1)
        limiter.check()
        with self.assertRaises(HTTPException) as limited:
            limiter.check()
        self.assertEqual(limited.exception.status_code, 429)

    def test_local_rate_limiter_has_one_bounded_queue(self) -> None:
        limiter = AuthRateLimiter(2)
        limiter.check()
        limiter.check()
        self.assertEqual(len(limiter._requests), 2)
        with self.assertRaises(HTTPException):
            limiter.check()


class _Snapshot:
    def __init__(self, values: dict):
        self._values = values
        self.exists = bool(values)

    def to_dict(self) -> dict:
        return dict(self._values)


class _Document:
    def __init__(self, values: dict):
        self.values = values

    def get(self, transaction=None):
        return _Snapshot(self.values)


class _Transaction:
    def set(self, document: _Document, values: dict) -> None:
        document.values.clear()
        document.values.update(values)


class _Firestore:
    def __init__(self):
        self.values: dict = {}
        self.document_ref = _Document(self.values)

    def collection(self, name: str):
        return self

    def document(self, name: str):
        return self.document_ref

    def transaction(self):
        return _Transaction()


class FirestoreAuthRateLimiterTests(unittest.TestCase):
    def test_limit_is_shared_between_instances_and_resets_next_minute(self) -> None:
        database = _Firestore()
        current = [datetime(2026, 7, 21, 9, 15, tzinfo=timezone.utc)]
        first = FirestoreAuthRateLimiter(database, 2, clock=lambda: current[0])
        second = FirestoreAuthRateLimiter(database, 2, clock=lambda: current[0])

        with patch("services.prana_api.google_auth.firestore.transactional", lambda fn: fn):
            first.check()
            second.check()
            with self.assertRaises(HTTPException) as limited:
                first.check()
            self.assertEqual(limited.exception.status_code, 429)
            self.assertEqual(limited.exception.headers["Retry-After"], "60")

            current[0] = datetime(2026, 7, 21, 9, 16, tzinfo=timezone.utc)
            first.check()
        self.assertEqual(database.values["count"], 1)

    def test_firestore_failure_fails_closed(self) -> None:
        database = _Firestore()
        database.transaction = lambda: (_ for _ in ()).throw(RuntimeError("offline"))
        limiter = FirestoreAuthRateLimiter(database, 300)
        with patch("services.prana_api.google_auth.firestore.transactional", lambda fn: fn):
            with self.assertRaises(HTTPException) as unavailable:
                limiter.check()
        self.assertEqual(unavailable.exception.status_code, 503)
        self.assertEqual(
            unavailable.exception.detail["code"], "GOOGLE_AUTH_UNAVAILABLE"
        )


class FakeBroker:
    def __init__(self):
        self.calls: list[dict] = []

    def exchange(self, authorization, **kwargs):
        self.calls.append({"authorization": authorization, **kwargs})
        return FirebaseSessionResponse(
            id_token="firebase-id",
            refresh_token="firebase-refresh",
            expires_in=3600,
            email="user@gmail.com",
            uid="uid-1",
        )


class GoogleAuthEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.broker = FakeBroker()
        app.dependency_overrides[get_google_auth_broker] = lambda: self.broker
        app.dependency_overrides[enforce_google_auth_rate] = lambda: None
        app.dependency_overrides[require_firebase_session] = lambda: FirebaseSession(
            identity=Identity(
                uid="uid-1", email="user@gmail.com", email_verified=True
            ),
            id_token="existing-firebase-id",
        )
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_exchange_is_public_but_link_uses_verified_firebase_session(self) -> None:
        payload = AUTHORIZATION.model_dump()
        exchanged = self.client.post(
            "/v1/auth/google/exchange",
            json=payload,
        )
        linked = self.client.post(
            "/v1/auth/google/link",
            json=payload,
        )
        self.assertEqual(exchanged.status_code, 200, exchanged.text)
        self.assertEqual(linked.status_code, 200, linked.text)
        self.assertEqual(self.broker.calls[0], {"authorization": AUTHORIZATION})
        self.assertEqual(
            self.broker.calls[1]["firebase_id_token"], "existing-firebase-id"
        )
        self.assertEqual(self.broker.calls[1]["expected_email"], "user@gmail.com")


if __name__ == "__main__":
    unittest.main()
