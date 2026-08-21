"""Where a Station's recordings land in Cloud Storage.

Kept free of Google client imports so the repositories can build the folder
name without pulling in the storage or genai SDKs. ``services/prana_admin`` has
a deliberate copy of this rule, held in step by
``tests/admin/test_station_storage_paths.py``.
"""

from __future__ import annotations

STORAGE_ROOT = "VHF-Storage"


def station_storage_folder(station_name: str, station_id: str) -> str:
    """Return a readable, path-safe and collision-resistant Station folder."""
    cleaned = []
    previous_separator = False
    for character in station_name.strip():
        if character.isalnum() or character in {"-", "_", "."}:
            cleaned.append(character)
            previous_separator = False
        elif character.isspace() or character in {"/", "\\"}:
            if cleaned and not previous_separator:
                cleaned.append("-")
                previous_separator = True
    slug = "".join(cleaned).strip("-_.")[:64].rstrip("-_.")
    if not slug:
        slug = "PRANA-Station"
    return f"{slug}_{station_id[:8]}"
