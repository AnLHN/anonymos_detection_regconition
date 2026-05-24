import sys
import time
from urllib.parse import quote

import cv2

from core.settings import get_str

CAMERA_ID = get_str("CAMERA_DOOR_67B_ID", "door_67b")
IP = get_str("CAMERA_DOOR_67B_IP", "camera-ip")
USERNAME = get_str("CAMERA_DOOR_67B_USERNAME", "admin")
PASSWORD = get_str("CAMERA_DOOR_67B_PASSWORD", "")
PORT = 554

PATHS = [
    "/Streaming/Channels/101",
    "/Streaming/Channels/102",
    "/cam/realmonitor?channel=1&subtype=0",
    "/cam/realmonitor?channel=1&subtype=1",
    "/live/ch00_0",
    "/live/ch00_1",
    "/h264/ch1/main/av_stream",
    "/h264/ch1/sub/av_stream",
    "/stream1",
    "/stream2",
]


def masked(url: str) -> str:
    if not PASSWORD:
        return url
    return url.replace(quote(PASSWORD, safe=""), "***").replace(PASSWORD, "***")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not PASSWORD:
        raise SystemExit("Missing CAMERA_DOOR_67B_PASSWORD in .env")
    encoded_password = quote(PASSWORD, safe="")
    for path in PATHS:
        url = f"rtsp://{USERNAME}:{encoded_password}@{IP}:{PORT}{path}"
        print("Trying:", masked(url))
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        start = time.time()
        ok = False
        frame = None
        while time.time() - start < 5:
            ok, frame = cap.read()
            if ok and frame is not None:
                break
        cap.release()
        if ok and frame is not None:
            print("OK:", masked(url))
            print("Frame shape:", frame.shape)
            return
        print("Failed")
    raise SystemExit("No working RTSP path found from common candidates.")


if __name__ == "__main__":
    main()
