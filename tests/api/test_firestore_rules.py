from pathlib import Path


def test_mobile_can_only_read_own_station_projection() -> None:
    rules = Path("infra/firebase/firestore.rules").read_text(encoding="utf-8")
    assert "match /users/{userId}/stations/{stationId}" in rules
    assert "request.auth.uid == userId" in rules
    assert "allow write: if false" in rules
    assert "match /{document=**}" in rules


def test_station_private_collections_are_not_exposed() -> None:
    rules = Path("infra/firebase/firestore.rules").read_text(encoding="utf-8")
    assert "station_registry" not in rules
    assert "station_pairings" not in rules
