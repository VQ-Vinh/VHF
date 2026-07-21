from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from google.cloud import firestore

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.prana_api.plan_catalog import PLAN_CATALOG, firestore_plan_data


MIGRATION_OPERATOR = "migration:free-plan-v1"
LEGACY_PLAN_IDS = ("staging-test", "staging_test", "stagingtest")


@dataclass(frozen=True)
class MigrationDecision:
    migrate: bool
    reason: str


def migration_decision(user: dict) -> MigrationDecision:
    if not user.get("email_verified"):
        return MigrationDecision(False, "email_not_verified")
    if user.get("status") == "suspended":
        return MigrationDecision(False, "suspended")
    if (
        user.get("status") == "active"
        and user.get("plan_id") == "free"
        and user.get("subscription_expires_at") is None
    ):
        return MigrationDecision(False, "already_free")
    return MigrationDecision(True, "eligible")


def bootstrap(project: str, apply: bool = False) -> dict[str, int]:
    db = firestore.Client(project=project)
    users = list(db.collection("users").stream())
    decisions = [(snap, migration_decision(snap.to_dict())) for snap in users]
    counts = {
        "plans": len(PLAN_CATALOG),
        "migrate": sum(decision.migrate for _snap, decision in decisions),
        "skipped": sum(not decision.migrate for _snap, decision in decisions),
        "legacy_plans": sum(
            db.collection("plans").document(plan_id).get().exists
            for plan_id in LEGACY_PLAN_IDS
        ),
    }
    if not apply:
        return counts

    batch = db.batch()
    writes = 0
    for plan in PLAN_CATALOG:
        plan_ref = db.collection("plans").document(plan.id)
        if not plan_ref.get().exists:
            batch.set(plan_ref, firestore_plan_data(plan))
            writes += 1

    for plan_id in LEGACY_PLAN_IDS:
        plan_ref = db.collection("plans").document(plan_id)
        if plan_ref.get().exists:
            batch.delete(plan_ref)
            _audit_ref = db.collection("admin_audit").document()
            batch.set(_audit_ref, {
                "operator": MIGRATION_OPERATOR,
                "action": "plan.remove_legacy",
                "target_uid": plan_id,
                "details": {},
                "created_at": firestore.SERVER_TIMESTAMP,
            })
            writes += 2

    for snap, decision in decisions:
        if not decision.migrate:
            continue
        before = snap.to_dict()
        batch.update(snap.reference, {
            "status": "active",
            "plan_id": "free",
            "subscription_expires_at": None,
            "plan_migrated_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        })
        audit_ref = db.collection("admin_audit").document()
        batch.set(audit_ref, {
            "operator": MIGRATION_OPERATOR,
            "action": "subscription.migrate_free",
            "target_uid": snap.id,
            "details": {
                "previous_status": before.get("status"),
                "previous_plan_id": before.get("plan_id"),
            },
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        writes += 2
        if writes >= 400:
            batch.commit()
            batch = db.batch()
            writes = 0
    if writes:
        batch.commit()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed the PRANA ELEX plan catalog and migrate eligible users to Free."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag the command is a dry run.",
    )
    args = parser.parse_args()
    counts = bootstrap(args.project, apply=args.apply)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(
        f"[{mode}] plans={counts['plans']} migrate={counts['migrate']} "
        f"skipped={counts['skipped']} legacy_plans={counts['legacy_plans']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
