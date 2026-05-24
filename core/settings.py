import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_str(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def get_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if value in (None, ""):
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_camera_registry() -> dict[str, dict[str, str]]:
    cameras = {}
    prefixes = {
        "CAMERA_DOOR_67B": "door_67b",
        "CAMERA_AI_PM_1": "ai_pm_1",
        "CAMERA_AI_PM_2": "ai_pm_2",
    }
    for prefix, fallback_id in prefixes.items():
        camera_id = get_str(f"{prefix}_ID", fallback_id)
        cameras[camera_id] = {
            "camera_id": camera_id,
            "name": get_str(f"{prefix}_NAME", camera_id),
            "ip": get_str(f"{prefix}_IP"),
            "rtsp": get_str(f"{prefix}_RTSP"),
        }
    return cameras
