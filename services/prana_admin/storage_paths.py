"""Where a Station's recordings land in Cloud Storage.

The admin image only copies ``services/prana_admin`` (see its Dockerfile), so it
cannot import the API's helper at runtime. This is a deliberate copy of
``services.prana_api.google_services.station_storage_folder``; the two are held
together by ``tests/admin/test_station_storage_paths.py``, which fails the build
if they ever disagree.
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


def station_storage_prefix(station_name: str, station_id: str) -> str:
    """Bucket prefix an operator can paste straight into the GCS console."""
    return f"{STORAGE_ROOT}/{station_storage_folder(station_name, station_id)}/"
