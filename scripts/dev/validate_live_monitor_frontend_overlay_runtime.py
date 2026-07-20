from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
USERNAME = os.getenv("ADMIN_SUPER_USERNAME", "admin_super")
PASSWORD = os.getenv("ADMIN_SUPER_PASSWORD", "ntc123!@#")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("ROI_RUNTIME_PROBE_TIMEOUT_SECONDS", "10"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def request_json(path: str, token: str | None = None, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        raise AssertionError(f"{method} {path} failed: {error.code} {raw}") from error


def read_stream_prefix(path: str, token: str, byte_count: int = 4096) -> bytes:
    request = urllib.request.Request(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read(byte_count)
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        raise AssertionError(f"GET {path} failed: {error.code} {raw}") from error


def validate_track(track: dict[str, Any]) -> None:
    assert_true("track_id" in track, "track should include track_id")
    assert_true(isinstance(track.get("label"), str), "track label should be a string")
    assert_true(track.get("status") in {"known", "unknown", "unverified"}, f"unexpected track status: {track.get('status')}")
    assert_true(track.get("score") is None or isinstance(track.get("score"), (int, float)), "track score should be number or null")
    assert_true(isinstance(track.get("bbox"), list), "track bbox should be a list")
    if track["bbox"]:
        assert_true(len(track["bbox"]) == 4, f"track bbox should have 4 values: {track['bbox']}")
        assert_true(all(isinstance(value, int) for value in track["bbox"]), f"track bbox values should be ints: {track['bbox']}")
    assert_true(isinstance(track.get("zone"), str), "track zone should be a string")


def main() -> None:
    login = request_json("/auth/login", method="POST", payload={"username": USERNAME, "password": PASSWORD})
    token = login["access_token"]
    runtime = request_json("/cameras/runtime", token=token)
    assert_true(isinstance(runtime, list), "/cameras/runtime should return a list")
    assert_true(len(runtime) > 0, "/cameras/runtime should include active RTSP cameras")

    ready_rows = [row for row in runtime if row.get("source_width") and row.get("source_height")]
    assert_true(ready_rows, "at least one runtime camera should have source_width/source_height metadata")
    row = ready_rows[0]
    camera_id = row["camera_id"]
    assert_true(isinstance(row.get("frame_id"), int), "runtime row should include numeric frame_id")
    assert_true(int(row["source_width"]) > 0, "source_width should be positive")
    assert_true(int(row["source_height"]) > 0, "source_height should be positive")
    assert_true(isinstance(row.get("zones"), dict), "runtime row should expose zones object")
    assert_true(isinstance(row.get("tracks"), list), "runtime row should expose tracks list")
    for track in row["tracks"]:
        validate_track(track)

    single_meta = request_json(f"/cameras/{camera_id}/meta", token=token)
    assert_true(single_meta["camera_id"] == camera_id, "single-camera meta should match camera_id")
    assert_true(isinstance(single_meta.get("frame_id"), int), "single-camera meta should include numeric frame_id")
    assert_true(int(single_meta.get("source_width") or 0) > 0, "single-camera meta source_width should be positive")
    assert_true(int(single_meta.get("source_height") or 0) > 0, "single-camera meta source_height should be positive")
    assert_true(isinstance(single_meta.get("tracks"), list), "single-camera meta should expose tracks list")
    assert_true(isinstance(single_meta.get("zones"), dict), "single-camera meta should expose zones object")
    for track in single_meta["tracks"]:
        validate_track(track)

    stream_prefix = read_stream_prefix(f"/cameras/{camera_id}/raw.mjpeg", token)
    assert_true(b"--frame" in stream_prefix, "raw MJPEG should include multipart frame boundary")
    assert_true(b"Content-Type: image/jpeg" in stream_prefix, "raw MJPEG should include jpeg content type")
    query_stream_prefix = read_stream_prefix(f"/cameras/{camera_id}/mjpeg?overlay=0", token)
    assert_true(b"--frame" in query_stream_prefix, "overlay=0 MJPEG should include multipart frame boundary")
    assert_true(b"Content-Type: image/jpeg" in query_stream_prefix, "overlay=0 MJPEG should include jpeg content type")

    print(
        json.dumps(
            {
                "camera_id": camera_id,
                "frame_id": row.get("frame_id"),
                "source_width": row.get("source_width"),
                "source_height": row.get("source_height"),
                "tracks_count": row.get("tracks_count"),
                "single_meta_frame_id": single_meta.get("frame_id"),
                "raw_mjpeg": "ok",
                "mjpeg_overlay_0": "ok",
            },
            ensure_ascii=False,
        )
    )
    print("live_monitor_frontend_overlay_runtime: ok")


if __name__ == "__main__":
    main()
