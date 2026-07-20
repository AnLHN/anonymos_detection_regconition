from __future__ import annotations

import subprocess
import sys
import socket
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"


def run_step(label: str, command: list[str], cwd: Path = ROOT) -> None:
    print(f"[roi-smoke] {label}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def backend_is_running() -> bool:
    try:
        with socket.create_connection(("localhost", 8000), timeout=2):
            return True
    except OSError:
        return False


def redis_is_running() -> bool:
    try:
        with socket.create_connection(("localhost", 6379), timeout=2):
            return True
    except OSError:
        return False


def main() -> None:
    python = sys.executable
    run_step("backend camera zones contract", [python, "scripts/dev/validate_camera_zones_contract.py"])
    run_step("frontend LiveMonitor ROI contract", [python, "scripts/dev/validate_live_monitor_roi_contract.py"])
    run_step("no double overlay contract", [python, "scripts/dev/validate_live_monitor_no_double_overlay.py"])
    run_step(
        "python compile",
        [
            python,
            "-m",
            "py_compile",
            "backend/cameras/router.py",
            "ai_worker/camera_worker.py",
            "ai_worker/zone_manager.py",
            "scripts/dev/validate_camera_zones_contract.py",
            "scripts/dev/validate_live_monitor_roi_contract.py",
            "scripts/dev/validate_live_monitor_no_double_overlay.py",
        ],
    )
    run_step("frontend typecheck", ["npm", "run", "typecheck"], FRONTEND_DIR)
    if backend_is_running():
        run_step("runtime raw overlay probe", [python, "scripts/dev/validate_live_monitor_frontend_overlay_runtime.py"])
    else:
        print("[roi-smoke] runtime raw overlay probe skipped: backend is not running", flush=True)
    if redis_is_running():
        run_step("redis overlay payload probe", [python, "scripts/dev/validate_redis_overlay_payload.py"])
    else:
        print("[roi-smoke] redis overlay payload probe skipped: redis is not running", flush=True)
    print("live_monitor_roi_smoke: ok", flush=True)


if __name__ == "__main__":
    main()
