from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_account_key(uid: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", uid):
        return uid
    return hashlib.sha256(uid.encode("utf-8")).hexdigest()


def prepare_account_data_root(data_root: str | Path, uid: str) -> Path:
    """Return the account root and migrate the pre-account storage once."""
    root = Path(data_root).expanduser().resolve()
    account_root = root / "accounts" / safe_account_key(uid)
    legacy_storage = root / "VHF_Storage"
    account_storage = account_root / "VHF_Storage"

    if legacy_storage.exists() and not account_storage.exists():
        account_root.mkdir(parents=True, exist_ok=True)
        legacy_storage.replace(account_storage)
        logger.info("Migrated legacy local storage into account-scoped storage")
    else:
        account_root.mkdir(parents=True, exist_ok=True)
        if legacy_storage.exists() and account_storage.exists():
            logger.warning("Legacy storage was preserved because account storage already exists")
    return account_root
