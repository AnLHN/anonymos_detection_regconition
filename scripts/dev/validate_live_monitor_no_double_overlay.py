from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LIVE_MONITOR = ROOT / "frontend" / "src" / "components" / "LiveMonitor.tsx"
CAMERA_WORKER = ROOT / "ai_worker" / "camera_worker.py"
CAMERA_ROUTER = ROOT / "backend" / "cameras" / "router.py"
ANNOTATED_STREAM = ROOT / "backend" / "cameras" / "annotated_stream.py"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def function_call_names(function: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.add(node.func.attr)
    return names


def main() -> None:
    live_monitor = LIVE_MONITOR.read_text(encoding="utf-8")
    router_source = CAMERA_ROUTER.read_text(encoding="utf-8")
    stream_source = ANNOTATED_STREAM.read_text(encoding="utf-8")
    worker_source = CAMERA_WORKER.read_text(encoding="utf-8")
    worker_tree = ast.parse(worker_source)

    assert_true("/raw.mjpeg" in live_monitor, "LiveMonitor production should fetch raw MJPEG")
    assert_true("/mjpeg`" not in live_monitor and "/mjpeg?" not in live_monitor, "LiveMonitor should not fetch annotated/debug MJPEG")
    assert_true("function StreamOverlay" in live_monitor, "LiveMonitor should render frontend overlay")
    assert_true("function TrackOverlay" in live_monitor, "LiveMonitor should render track overlay")

    assert_true("raw_mjpeg_frames" in stream_source, "backend stream module should expose raw_mjpeg_frames")
    assert_true("annotated_mjpeg_frames" in stream_source, "backend stream module should retain annotated debug stream")
    assert_true("overlay: bool = Query(True" in router_source, "mjpeg endpoint should keep overlay query")
    assert_true("frame_iter = annotated_mjpeg_frames if overlay else raw_mjpeg_frames" in router_source, "overlay=0 should select raw stream")

    functions = {node.name: node for node in ast.walk(worker_tree) if isinstance(node, ast.FunctionDef)}
    assert_true("publish_stream_frame" in functions, "CameraWorker.publish_stream_frame should exist")
    assert_true("build_debug_annotated_frame" in functions, "CameraWorker.build_debug_annotated_frame should exist")

    publish_calls = function_call_names(functions["publish_stream_frame"])
    debug_calls = function_call_names(functions["build_debug_annotated_frame"])
    assert_true("draw_tracks" not in publish_calls, "publish_stream_frame should not draw tracks directly")
    assert_true("draw_zones" not in publish_calls, "publish_stream_frame should not draw zones directly")
    assert_true("build_debug_annotated_frame" in publish_calls, "publish_stream_frame should only use debug annotation helper conditionally")
    assert_true("draw_tracks" in debug_calls, "debug annotation helper should keep draw_tracks")
    assert_true("draw_zones" in debug_calls, "debug annotation helper should keep draw_zones")
    assert_true("self.config.debug_annotated_stream" in worker_source, "debug annotation should be gated by debug_annotated_stream")

    print("live_monitor_no_double_overlay: ok")


if __name__ == "__main__":
    main()
