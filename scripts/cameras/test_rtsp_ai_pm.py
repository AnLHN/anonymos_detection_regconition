import sys
import time
from urllib.parse import quote

import cv2

from core.settings import get_str

IP = get_str("CAMERA_AI_PM_1_IP", "camera-ip")
USERNAME = get_str("CAMERA_AI_PM_USERNAME", "admin")
PASSWORD = get_str("CAMERA_AI_PM_PASSWORD", "")


def build_urls() -> list[tuple[str, str]]:
    if not PASSWORD:
        raise SystemExit("Missing CAMERA_AI_PM_PASSWORD in .env")
    encoded_password = quote(PASSWORD, safe="")
    return [
        ("ai_pm_1", f"rtsp://{USERNAME}:{encoded_password}@{IP}:554/Streaming/Channels/101"),
        ("ai_pm_1_sub", f"rtsp://{USERNAME}:{encoded_password}@{IP}:554/Streaming/Channels/102"),
        ("ai_pm_2", f"rtsp://{USERNAME}:{encoded_password}@{IP}:554/Streaming/Channels/201"),
        ("ai_pm_2_sub", f"rtsp://{USERNAME}:{encoded_password}@{IP}:554/Streaming/Channels/202"),
        ("ai_pm_2_alt_301", f"rtsp://{USERNAME}:{encoded_password}@{IP}:554/Streaming/Channels/301"),
        ("ai_pm_2_alt_302", f"rtsp://{USERNAME}:{encoded_password}@{IP}:554/Streaming/Channels/302"),
    ]


def mask(url: str) -> str:
    return url.replace(quote(PASSWORD, safe=""), "***").replace(PASSWORD, "***")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for camera_id, url in build_urls():
        print("Trying", camera_id, mask(url))
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        start = time.time()
        ok = False
        frame = None
        while time.time() - start < 5:
            ok, frame = cap.read()
            if ok and frame is not None:
                break
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if ok and frame is not None:
            print("OK", camera_id, "shape", frame.shape, "fps", fps)
        else:
            print("FAILED", camera_id)


if __name__ == "__main__":
    main()
