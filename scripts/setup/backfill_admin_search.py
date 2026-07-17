from __future__ import annotations

import argparse
import os

from google.cloud import firestore


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill normalized email fields used by PRANA Admin search")
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    parser.add_argument("--apply", action="store_true", help="Write changes. Without this flag the command is dry-run.")
    args = parser.parse_args()
    if not args.project:
        parser.error("Set --project or GOOGLE_CLOUD_PROJECT")

    db = firestore.Client(project=args.project)
    pending = []
    for snapshot in db.collection("users").stream():
        data = snapshot.to_dict()
        email = str(data.get("email") or "").strip()
        normalized = email.lower()
        if normalized and data.get("email_lower") != normalized:
            pending.append((snapshot.reference, normalized))

    print(f"Users requiring update: {len(pending)}")
    if not args.apply:
        print("Dry-run only. Run again with --apply to write changes.")
        return 0

    for start in range(0, len(pending), 400):
        batch = db.batch()
        for reference, normalized in pending[start:start + 400]:
            batch.update(reference, {"email_lower": normalized})
        batch.commit()
    print("Backfill complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
