import time

import cv2
import numpy as np
import redis

from backend.config import MJPEG_REDIS_POLL_INTERVAL, MJPEG_WAITING_FRAME_INTERVAL, REDIS_URL

_BOUNDARY = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
_STREAM_CLIENT: redis.Redis | None = None


def annotated_mjpeg_frames(camera_id: str, _source_url: str, _config: dict | None = None):
    client = redis_client()
    last_frame = None
    last_waiting_frame_at = 0.0
    waiting_frame = build_waiting_frame(camera_id)
    while True:
        try:
            frame = client.get(annotated_frame_key(camera_id))
        except redis.RedisError:
            frame = None

        if frame and frame != last_frame:
            last_frame = frame
            yield mjpeg_part(frame)
        elif not frame and time.time() - last_waiting_frame_at >= MJPEG_WAITING_FRAME_INTERVAL:
            last_waiting_frame_at = time.time()
            yield mjpeg_part(waiting_frame)
        time.sleep(MJPEG_REDIS_POLL_INTERVAL)


def get_latest_camera_frame(camera_id: str, _source_url: str | None = None, _config: dict | None = None, timeout: float = 10.0):
    client = redis_client()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            frame_jpeg = client.get(raw_frame_key(camera_id))
        except redis.RedisError:
            frame_jpeg = None
        if frame_jpeg:
            frame = decode_jpeg(frame_jpeg)
            if frame is not None:
                return frame
        time.sleep(MJPEG_REDIS_POLL_INTERVAL)
    return None


def ensure_camera_worker(camera_id: str, _source_url: str, _config: dict | None = None) -> None:
    return None


def stop_camera_worker(camera_id: str) -> None:
    return None


def redis_client() -> redis.Redis:
    global _STREAM_CLIENT
    if _STREAM_CLIENT is None:
        _STREAM_CLIENT = redis.Redis.from_url(REDIS_URL, decode_responses=False)
    return _STREAM_CLIENT


def mjpeg_part(payload: bytes) -> bytes:
    return _BOUNDARY + str(len(payload)).encode() + b"\r\n\r\n" + payload + b"\r\n"


def decode_jpeg(payload: bytes):
    buffer = np.frombuffer(payload, dtype=np.uint8)
    return cv2.imdecode(buffer, cv2.IMREAD_COLOR)


def build_waiting_frame(camera_id: str) -> bytes:
    frame = np.full((720, 1280, 3), (245, 250, 251), dtype=np.uint8)
    for x in range(0, 1280, 48):
        cv2.line(frame, (x, 0), (x, 720), (226, 240, 243), 1)
    for y in range(0, 720, 48):
        cv2.line(frame, (0, y), (1280, y), (226, 240, 243), 1)
    cv2.rectangle(frame, (70, 250), (1210, 470), (255, 255, 255), -1)
    cv2.rectangle(frame, (70, 250), (1210, 470), (190, 220, 226), 2)
    cv2.putText(frame, "Waiting for camera worker frame", (120, 345), cv2.FONT_HERSHEY_SIMPLEX, 1.15, (31, 77, 92), 2)
    cv2.putText(frame, camera_id, (120, 405), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (91, 109, 124), 2)
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not ok:
        return b""
    return encoded.tobytes()


def raw_frame_key(camera_id: str) -> str:
    return f"camera:{camera_id}:latest_raw_jpeg"


def annotated_frame_key(camera_id: str) -> str:
    return f"camera:{camera_id}:latest_annotated_jpeg"
