from __future__ import annotations

from services.prana_api.models import Plan


PLAN_CATALOG = (
    Plan(
        id="free",
        name="Free",
        audio_seconds_limit=600,
        quota_period="daily",
        availability="available",
        sort_order=10,
        monthly_audio_seconds=600,
        requests_per_minute=30,
        max_concurrency=2,
        max_devices=2,
    ),
    Plan(
        id="plus",
        name="Plus",
        audio_seconds_limit=3_600,
        quota_period="daily",
        availability="coming_soon",
        sort_order=20,
        monthly_audio_seconds=3_600,
        requests_per_minute=30,
        max_concurrency=2,
        max_devices=2,
    ),
    Plan(
        id="pro",
        name="Pro",
        audio_seconds_limit=10_800,
        quota_period="daily",
        availability="coming_soon",
        sort_order=30,
        monthly_audio_seconds=10_800,
        requests_per_minute=30,
        max_concurrency=2,
        max_devices=2,
    ),
)

PLAN_BY_ID = {plan.id: plan for plan in PLAN_CATALOG}


def firestore_plan_data(plan: Plan) -> dict:
    return plan.model_dump(exclude={"id"}, mode="python")


__all__ = ["PLAN_BY_ID", "PLAN_CATALOG", "firestore_plan_data"]
