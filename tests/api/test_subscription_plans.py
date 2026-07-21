from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from scripts.setup.bootstrap_subscription_plans import migration_decision
from services.prana_api.auth import Identity, require_identity
from services.prana_api.main import app, get_repository
from services.prana_api.memory_repository import MemoryRepository
from services.prana_api.models import Plan, UserAccount
from services.prana_api.plan_catalog import PLAN_BY_ID, PLAN_CATALOG
from services.prana_api.repository import identity_updates, usage_period, usage_reset_at


class SubscriptionPlanTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.repo.plans.update(PLAN_BY_ID)

    def test_catalog_limits_and_utc_reset(self):
        self.assertEqual(
            [plan.audio_seconds_limit for plan in PLAN_CATALOG],
            [600, 3_600, 10_800],
        )
        self.assertEqual(
            [plan.availability for plan in PLAN_CATALOG],
            ["available", "coming_soon", "coming_soon"],
        )
        now = datetime(2026, 7, 20, 23, 59, 59, tzinfo=timezone.utc)
        self.assertEqual(usage_period(PLAN_BY_ID["free"], now), "2026-07-20")
        self.assertEqual(
            usage_reset_at(PLAN_BY_ID["free"], now),
            datetime(2026, 7, 21, tzinfo=timezone.utc),
        )
        with self.assertRaises(ValueError):
            Plan(
                id="invalid", name="Invalid", audio_seconds_limit=600,
                requests_per_minute=30, max_concurrency=11, max_devices=2,
            )

    def test_verified_account_gets_free_but_suspended_stays_suspended(self):
        account = self.repo.sync_identity("new", "new@example.com", True)
        self.assertEqual((account.status, account.plan_id), ("active", "free"))
        self.assertTrue(account.subscription_active)

        self.repo.users["blocked"] = UserAccount(
            uid="blocked",
            email="blocked@example.com",
            email_verified=True,
            status="suspended",
            plan_id="free",
        )
        blocked = self.repo.sync_identity("blocked", "blocked@example.com", True)
        self.assertEqual(blocked.status, "suspended")

    def test_identity_sync_skips_unchanged_profile_and_preserves_suspend(self):
        unchanged = {
            "email": "user@example.com",
            "email_lower": "user@example.com",
            "email_verified": True,
            "status": "active",
            "plan_id": "free",
            "subscription_expires_at": None,
        }
        self.assertEqual(
            identity_updates(unchanged, "user@example.com", True),
            {},
        )
        suspended = {**unchanged, "status": "suspended"}
        updates = identity_updates(suspended, "user@example.com", True)
        self.assertNotIn("status", updates)
        self.assertNotIn("plan_id", updates)

    def test_daily_quota_accepts_600_seconds_then_rejects_more(self):
        plan = PLAN_BY_ID["free"]
        self.repo.reserve("u", plan, "r1", "one", 599)
        self.repo.settle_success("u", "r1", {"ok": True}, {})
        self.repo.reserve("u", plan, "r2", "two", 1)
        self.repo.settle_success("u", "r2", {"ok": True}, {})
        usage = self.repo.get_usage("u", plan)
        self.assertEqual(usage.used_audio_seconds, 600)
        self.assertEqual(usage.remaining_audio_seconds, 0)
        with self.assertRaises(HTTPException) as limited:
            self.repo.reserve("u", plan, "r3", "three", 1)
        self.assertEqual(limited.exception.detail["code"], "DAILY_QUOTA_EXCEEDED")
        self.assertIn("resets_at", limited.exception.detail)

    def test_paid_plans_cannot_be_selected(self):
        self.repo.users["u"] = UserAccount(
            uid="u",
            email="u@example.com",
            email_verified=True,
            status="active",
            plan_id="free",
        )
        with self.assertRaises(HTTPException) as unavailable:
            self.repo.select_plan("u", PLAN_BY_ID["plus"])
        self.assertEqual(unavailable.exception.detail["code"], "PLAN_NOT_AVAILABLE")

    def test_migration_is_idempotent_and_preserves_suspended(self):
        self.assertTrue(
            migration_decision({"email_verified": True, "status": "pending_payment"}).migrate
        )
        self.assertFalse(
            migration_decision({"email_verified": True, "status": "suspended"}).migrate
        )
        self.assertFalse(
            migration_decision({
                "email_verified": True,
                "status": "active",
                "plan_id": "free",
                "subscription_expires_at": None,
            }).migrate
        )


class SubscriptionPlanApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = MemoryRepository()
        self.repo.plans.update(PLAN_BY_ID)
        self.repo.users["u"] = UserAccount(
            uid="u",
            email="u@example.com",
            email_verified=True,
            status="active",
            plan_id="free",
        )
        app.dependency_overrides[get_repository] = lambda: self.repo
        app.dependency_overrides[require_identity] = lambda: Identity(
            uid="u", email="u@example.com", email_verified=True
        )
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_catalog_and_selection_contract(self):
        with patch.object(
            self.repo, "sync_identity", wraps=self.repo.sync_identity
        ) as sync_identity:
            catalog = self.client.get("/v1/plans")
        sync_identity.assert_not_called()
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.headers["cache-control"], "no-store")
        self.assertEqual([item["id"] for item in catalog.json()], ["free", "plus", "pro"])
        unavailable = self.client.post(
            "/v1/subscription/select", json={"plan_id": "pro"}
        )
        self.assertEqual(unavailable.status_code, 409)
        self.assertEqual(unavailable.json()["detail"]["code"], "PLAN_NOT_AVAILABLE")
        free = self.client.post(
            "/v1/subscription/select", json={"plan_id": "free"}
        )
        self.assertEqual(free.status_code, 200)
        self.assertEqual(free.json()["plan_id"], "free")


if __name__ == "__main__":
    unittest.main()
