from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
AI_WORKER_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AI_WORKER_DIR))

from backend.cameras import router as cameras_router
from backend.auth.security import CurrentUser, require_admin_super
from zone_manager import ZoneManager


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def route_dependency_names(path: str, method: str) -> list[str]:
    for route in cameras_router.router.routes:
        if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
            return [dependency.call.__name__ for dependency in route.dependant.dependencies if dependency.call]
    raise AssertionError(f"Route not found: {method} {path}")


def assert_bad_zones(value: Any, expected_detail: str) -> None:
    try:
        cameras_router.normalize_camera_zones(value)
    except HTTPException as exc:
        assert_true(exc.status_code == 400, f"expected 400, got {exc.status_code}")
        assert_true(expected_detail in str(exc.detail), f"expected detail containing {expected_detail!r}, got {exc.detail!r}")
        return
    raise AssertionError(f"invalid zones should be rejected: {value!r}")


def assert_forbidden(user: CurrentUser) -> None:
    try:
        require_admin_super(user)
    except HTTPException as exc:
        assert_true(exc.status_code == 403, f"expected 403 for role {user.role}")
        return
    raise AssertionError(f"role {user.role} should not pass require_admin_super")


def main() -> None:
    get_dependencies = route_dependency_names("/cameras/{camera_id}/zones", "GET")
    patch_dependencies = route_dependency_names("/cameras/{camera_id}/zones", "PATCH")
    meta_dependencies = route_dependency_names("/cameras/{camera_id}/meta", "GET")
    raw_mjpeg_dependencies = route_dependency_names("/cameras/{camera_id}/raw.mjpeg", "GET")
    assert_true("require_admin_super" not in get_dependencies, "GET zones must not require admin_super")
    assert_true("require_admin_super" in patch_dependencies, "PATCH zones must require admin_super")
    assert_true("require_admin_super" not in meta_dependencies, "camera meta must not require admin_super")
    assert_true("require_admin_super" not in raw_mjpeg_dependencies, "raw MJPEG must not require admin_super")

    router_source = (ROOT / "backend" / "cameras" / "router.py").read_text(encoding="utf-8")
    worker_source = (ROOT / "ai_worker" / "camera_worker.py").read_text(encoding="utf-8")
    stream_source = (ROOT / "backend" / "cameras" / "annotated_stream.py").read_text(encoding="utf-8")
    assert_true('"source_width"' in router_source and '"source_height"' in router_source, "runtime should expose source dimensions")
    assert_true('"zones": zones' in router_source, "runtime should expose zones metadata")
    assert_true("def get_camera_runtime_meta" in router_source, "backend should expose per-camera runtime meta")
    assert_true("raw_mjpeg_frames" in stream_source, "backend should expose raw MJPEG frames")
    assert_true("overlay: bool = Query(True" in router_source, "mjpeg endpoint should support overlay query")
    assert_true("frame_iter = annotated_mjpeg_frames if overlay else raw_mjpeg_frames" in router_source, "overlay=0 should use raw MJPEG frames")
    assert_true('"source_width": source_width' in worker_source, "worker meta should publish source_width")
    assert_true('"source_height": source_height' in worker_source, "worker meta should publish source_height")
    assert_true('"zones": self.zone_manager.to_payload()' in worker_source, "worker meta should publish zones")
    assert_true("debug_annotated_stream" in worker_source, "worker should keep annotated drawing behind debug flag")

    assert_forbidden(CurrentUser(username="viewer", role=0, role_name="viewer", permissions=()))
    assert_forbidden(CurrentUser(username="operator", role=1, role_name="operator", permissions=("cameras:read",)))
    assert_forbidden(CurrentUser(username="admin", role=5, role_name="admin", permissions=("cameras:update",)))

    allowed = CurrentUser(username="admin_super", role=9, role_name="admin_super", permissions=())
    assert_true(require_admin_super(allowed) == allowed, "admin_super should pass require_admin_super")

    zones = cameras_router.normalize_camera_zones(
        {
            "gate": [[10.2, 11.8], [90, 10], [90, 90], [10, 90]],
            "restricted_area": [[100, 100], [180, 100], [180, 180]],
        }
    )
    assert_true(zones["gate"][0] == [10, 12], "zone points should round to integers")

    normalized_config = cameras_router.normalize_camera_config(
        {
            "always_on": True,
            "ai_interval": 0.2,
            "stream_publish_fps": 15,
            "zones": zones,
        }
    )
    assert_true(normalized_config["always_on"] is True, "always_on should be preserved")
    assert_true(normalized_config["ai_interval"] == 0.2, "ai_interval should be preserved")
    assert_true(normalized_config["stream_publish_fps"] == 15, "stream_publish_fps should be preserved")
    assert_true(normalized_config["mjpeg_idle_timeout"] == 0, "always_on should set mjpeg_idle_timeout")
    assert_true(normalized_config["zones"] == zones, "zones should be normalized and preserved")

    assert_bad_zones([], "Zones must be an object")
    assert_bad_zones({"": [[1, 2], [3, 4], [5, 6]]}, "Zone name must not be empty")
    assert_bad_zones({"gate": [[1, 2], [3, 4]]}, "at least 3 points")
    assert_bad_zones({"gate": [[1, 2, 3], [3, 4], [5, 6]]}, "point must be [x, y]")
    assert_bad_zones({"gate": [["x", 2], [3, 4], [5, 6]]}, "coordinates must be numbers")

    manager = ZoneManager(zones)
    assert_true(manager.get_zone("ai_pm_1", (20, 20, 40, 40)) == "gate", "bbox center inside gate should match gate")
    assert_true(manager.get_zone("ai_pm_1", (220, 220, 260, 260)) == "none", "bbox outside zones should be none")

    invalid_manager = ZoneManager({"bad": [[1, 2], [3, 4]], "also_bad": "nope"})
    assert_true(invalid_manager.zones == {}, "worker should drop invalid polygons safely")

    print("camera_zones_contract: ok")


if __name__ == "__main__":
    main()
