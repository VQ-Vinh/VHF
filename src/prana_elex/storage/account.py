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


def _merge_storage(source: Path, target: Path) -> None:
    """Move non-conflicting files from source into target without overwriting."""
    target.mkdir(parents=True, exist_ok=True)
    for item in tuple(source.iterdir()):
        destination = target / item.name
        if not destination.exists():
            item.replace(destination)
        elif item.is_dir() and destination.is_dir():
            _merge_storage(item, destination)
        else:
            logger.warning("Preserved account-scoped file because shared storage already contains %s", destination)
    try:
        source.rmdir()
    except OSError:
        pass


def prepare_data_root(data_root: str | Path, uid: str) -> Path:
    """Return the selected data root and migrate this account's old nested storage."""
    root = Path(data_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    account_root = root / "accounts" / safe_account_key(uid)
    account_storage = account_root / "VHF_Storage"
    shared_storage = root / "VHF_Storage"

    if account_storage.exists():
        if shared_storage.exists():
            _merge_storage(account_storage, shared_storage)
        else:
            account_storage.replace(shared_storage)
        logger.info("Migrated account-scoped local storage into the selected Data folder")

    for directory in (account_root, root / "accounts"):
        try:
            directory.rmdir()
        except OSError:
            pass
    return root
