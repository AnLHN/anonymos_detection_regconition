import argparse
import subprocess
import sys

from core.settings import get_camera_registry, get_float, get_int, get_str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run camera by camera_id from .env registry.")
    parser.add_argument("camera_id", nargs="?", default=get_str("DEFAULT_CAMERA_ID", "door_67b"))
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    cameras = get_camera_registry()
    camera = cameras.get(args.camera_id)
    if not camera or not camera.get("rtsp"):
        raise SystemExit(f"Camera not found or missing RTSP in .env: {args.camera_id}")

    command = [
        sys.executable,
        "ai_worker/run_webcam.py",
        "--camera-id",
        camera["camera_id"],
        "--source",
        camera["rtsp"],
        "--width",
        str(get_int("DEFAULT_DISPLAY_WIDTH", 1280)),
        "--height",
        str(get_int("DEFAULT_DISPLAY_HEIGHT", 720)),
        "--ai-interval",
        str(get_float("DEFAULT_AI_INTERVAL", 0.7)),
        "--reconnect-delay",
        str(get_float("DEFAULT_RECONNECT_DELAY", 5.0)),
        "--window",
        camera["name"],
    ]
    print("Running camera:", camera["camera_id"], camera["name"])
    subprocess.run(command, check=False)


if __name__ == "__main__":
    main()
