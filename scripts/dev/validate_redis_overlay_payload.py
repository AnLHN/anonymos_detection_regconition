from __future__ import annotations

import json
import os
from typing import Any

import redis


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MIN_READY_CAMERAS = int(os.getenv("ROI_REDIS_MIN_READY_CAMERAS", "1"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def decode_meta(payload: bytes, key: bytes) -> dict[str, Any]:
    try:
        meta = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AssertionError(f"invalid JSON meta at {key!r}: {error}") from error
    assert_true(isinstance(meta, dict), f"meta should be object at {key!r}")
    return meta


def validate_track(track: dict[str, Any], camera_id: str) -> None:
    assert_true("track_id" in track, f"{camera_id}: track should include track_id")
    assert_true(isinstance(track.get("label"), str), f"{camera_id}: track label should be string")
    assert_true(track.get("status") in {"known", "unknown", "unverified"}, f"{camera_id}: invalid track status {track.get('status')!r}")
    assert_true(track.get("score") is None or isinstance(track.get("score"), (int, float)), f"{camera_id}: score should be number or null")
    bbox = track.get("bbox")
    assert_true(isinstance(bbox, list), f"{camera_id}: bbox should be list")
    assert_true(len(bbox) == 4, f"{camera_id}: bbox should have 4 values")
    assert_true(all(isinstance(value, int) for value in bbox), f"{camera_id}: bbox values should be ints")
    assert_true(isinstance(track.get("zone"), str), f"{camera_id}: zone should be string")


def validate_zones(zones: Any, camera_id: str) -> None:
    assert_true(isinstance(zones, dict), f"{camera_id}: zones should be object")
    for zone_name, polygon in zones.items():
        assert_true(isinstance(zone_name, str) and zone_name.strip(), f"{camera_id}: zone name should be non-empty")
        assert_true(isinstance(polygon, list), f"{camera_id}: zone polygon should be list")
        assert_true(len(polygon) >= 3, f"{camera_id}: zone polygon should have at least 3 points")
        for point in polygon:
            assert_true(isinstance(point, list) and len(point) == 2, f"{camera_id}: zone point should be [x, y]")
            assert_true(all(isinstance(value, int) for value in point), f"{camera_id}: zone point values should be ints")


def validate_camera_payload(client: redis.Redis, meta_key: bytes) -> dict[str, Any]:
    payload = client.get(meta_key)
    assert_true(isinstance(payload, bytes), f"missing meta payload for {meta_key!r}")
    meta = decode_meta(payload, meta_key)
    camera_id = str(meta.get("camera_id") or "")
    assert_true(camera_id, f"{meta_key!r}: camera_id should be present")
    assert_true(isinstance(meta.get("frame_id"), int), f"{camera_id}: frame_id should be int")
    assert_true(isinstance(meta.get("source_width"), int) and meta["source_width"] > 0, f"{camera_id}: source_width should be positive int")
    assert_true(isinstance(meta.get("source_height"), int) and meta["source_height"] > 0, f"{camera_id}: source_height should be positive int")
    assert_true(isinstance(meta.get("created_at"), str) and meta["created_at"], f"{camera_id}: created_at should be string")
    assert_true(isinstance(meta.get("tracks"), list), f"{camera_id}: tracks should be list")
    assert_true("zones" in meta, f"{camera_id}: zones should be present")
    validate_zones(meta["zones"], camera_id) if meta["zones"] else assert_true(isinstance(meta["zones"], dict), f"{camera_id}: zones should be object")
    for track in meta["tracks"]:
        assert_true(isinstance(track, dict), f"{camera_id}: track should be object")
        validate_track(track, camera_id)

    raw = client.get(f"camera:{camera_id}:latest_raw_jpeg")
    assert_true(isinstance(raw, bytes) and raw.startswith(b"\xff\xd8"), f"{camera_id}: raw JPEG should exist")
    annotated = client.get(f"camera:{camera_id}:latest_annotated_jpeg")
    assert_true(isinstance(annotated, bytes) and annotated.startswith(b"\xff\xd8"), f"{camera_id}: annotated/debug JPEG should exist")
    return {
        "camera_id": camera_id,
        "frame_id": meta["frame_id"],
        "source_width": meta["source_width"],
        "source_height": meta["source_height"],
        "tracks_count": len(meta["tracks"]),
        "zones_count": len(meta["zones"]),
    }


def main() -> None:
    client = redis.Redis.from_url(REDIS_URL, decode_responses=False, socket_connect_timeout=2, socket_timeout=2)
    meta_keys = sorted(client.scan_iter("camera:*:latest_meta"))
    assert_true(len(meta_keys) >= MIN_READY_CAMERAS, f"expected at least {MIN_READY_CAMERAS} camera meta keys, got {len(meta_keys)}")
    rows = [validate_camera_payload(client, key) for key in meta_keys]
    print(json.dumps({"redis_overlay_payload": "ok", "cameras": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
