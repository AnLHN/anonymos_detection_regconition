from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LIVE_MONITOR = ROOT / "frontend" / "src" / "components" / "LiveMonitor.tsx"
ADMIN_SHELL = ROOT / "frontend" / "src" / "components" / "AdminShell.tsx"
API = ROOT / "frontend" / "src" / "lib" / "api.ts"
TYPES = ROOT / "frontend" / "src" / "lib" / "types.ts"
GLOBALS_CSS = ROOT / "frontend" / "src" / "app" / "globals.css"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_contains(source: str, tokens: list[str], label: str) -> None:
    for token in tokens:
        assert_true(token in source, f"{label} should contain token: {token}")


def assert_not_contains(source: str, tokens: list[str], label: str) -> None:
    for token in tokens:
        assert_true(token not in source, f"{label} should not contain token: {token}")


def main() -> None:
    live_monitor = LIVE_MONITOR.read_text(encoding="utf-8")
    admin_shell = ADMIN_SHELL.read_text(encoding="utf-8")
    api = API.read_text(encoding="utf-8")
    types = TYPES.read_text(encoding="utf-8")
    globals_css = GLOBALS_CSS.read_text(encoding="utf-8")

    assert_contains(
        live_monitor,
        [
            "currentUser?: CurrentUser | null",
            "const canEditZones = Number(currentUser?.role || 0) >= 9",
            "canEditZones={canEditZones}",
            "/raw.mjpeg",
            "OVERLAY_META_POLL_INTERVAL_MS",
            "getCameraMeta(token, cameraId)",
            "getCameraZones(token, cameraId)",
            "updateCameraZones(token, cameraId, nextZones)",
            "function StreamOverlay",
            "function TrackOverlay",
            "runtime={displayRuntime}",
            "runtimeSourceSize(displayRuntime, frameSize)",
            "viewBox={`0 0 ${frameWidth} ${frameHeight}`}",
            "preserveAspectRatio=\"none\"",
            "setFrameSize({ width: bitmap.width, height: bitmap.height })",
            "draftPoints.length < 3",
            "knownRuntimeTracks(runtime)",
        ],
        "LiveMonitor",
    )
    assert_not_contains(
        live_monitor,
        [
            "normalizedRuntimeTracks(runtime).filter((track) => track.status !== 'known'",
            "Unknown</strong>",
            "Unverified</strong>",
        ],
        "LiveMonitor",
    )

    assert_contains(
        admin_shell,
        ["<LiveMonitor token={token} cameras={cameras} currentUser={currentUser} />"],
        "AdminShell",
    )

    assert_contains(
        api,
        [
            "CameraZones",
            "export function getCameraMeta",
            "export function getCameraZones",
            "`/cameras/${encodeURIComponent(cameraId)}/zones`",
            "export function updateCameraZones",
            "body: JSON.stringify({ zones })",
        ],
        "api.ts",
    )

    assert_contains(
        types,
        [
            "export type ZonePoint = [number, number];",
            "export type CameraZones = Record<string, ZonePoint[]>;",
        ],
        "types.ts",
    )

    assert_contains(
        globals_css,
        [
            ".ops-roi-toggle",
            ".ops-stream-overlay",
            ".ops-track-overlay",
            ".ops-track-overlay.is-unknown",
            ".ops-track-overlay.is-unverified",
            ".ops-roi-zone polygon",
            ".ops-roi-zone.is-restricted",
            ".ops-roi-zone.is-custom",
            ".ops-roi-zone.is-draft",
            ".ops-roi-toolbar",
            ".ops-detection-pill.is-unknown",
            ".ops-detection-pill.is-unverified",
        ],
        "globals.css",
    )

    print("live_monitor_roi_contract: ok")


if __name__ == "__main__":
    main()
