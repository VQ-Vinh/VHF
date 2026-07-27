from __future__ import annotations

import hashlib
import json


def normalize_audio_devices(
    devices: list[dict],
    loopbacks: list[dict] | None = None,
) -> tuple[list[dict], dict[str, int]]:
    """Return public, stable device descriptors and their current local indices."""
    normalized: list[dict] = []
    index_by_id: dict[str, int] = {}
    collisions: dict[str, int] = {}

    def append(raw: dict, mode: str) -> None:
        identity = "|".join(
            [
                mode,
                str(raw.get("host_api", "")),
                str(raw.get("name", "")),
                str(raw.get("inputs", 0)),
                str(raw.get("outputs", 0)),
                str(int(raw.get("sr", 0) or 0)),
            ]
        )
        ordinal = collisions.get(identity, 0)
        collisions[identity] = ordinal + 1
        device_id = hashlib.sha256(f"{identity}|{ordinal}".encode()).hexdigest()[:32]
        normalized.append(
            {
                "id": device_id,
                "name": str(raw.get("name") or "Audio device"),
                "mode": mode,
                "input_channels": int(raw.get("inputs", 0) or 0),
                "output_channels": int(raw.get("outputs", 0) or 0),
                "sample_rate": int(raw.get("sr", 0) or 0),
                "host_api": str(raw.get("host_api") or ""),
            }
        )
        index_by_id[device_id] = int(raw["index"])

    for item in devices:
        if int(item.get("inputs", 0) or 0) > 0:
            append(item, "device")
    for item in loopbacks or []:
        value = dict(item)
        value.setdefault("inputs", 1)
        value.setdefault("outputs", 0)
        append(value, "loopback")
    return normalized, index_by_id


def capability_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
