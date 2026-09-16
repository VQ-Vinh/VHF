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


def test_operator_console_cannot_be_given_a_firestore_shortcut() -> None:
    """The fleet console must stay REST-only.

    A `fleet_operator` reads Stations it does not own. The tempting "fix" for
    console latency is to widen these rules so it can use a listener instead of
    polling; that would hand every operator direct, unaudited, unentitled read
    access to other tenants' data. Ownership stays the only condition here, and
    result documents stay closed to every client.
    """
    rules = Path("infra/firebase/firestore.rules").read_text(encoding="utf-8")
    assert "fleet_operator" not in rules
    assert "operator" not in rules
    # Reads are granted by uid equality alone -- no role or claim escape hatch.
    assert rules.count("request.auth.uid == userId") == 2
    assert "request.auth.token" not in rules
    # Transcripts are served by prana-api so plan entitlements still apply.
    assert "allow read, write: if false;" in rules
