import time
import os
import signal
import site
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import redis

from backend.config import MJPEG_REDIS_POLL_INTERVAL, MJPEG_WAITING_FRAME_INTERVAL, REDIS_URL
from backend.database.postgres import fetch_one

_BOUNDARY = b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
_STREAM_CLIENT: redis.Redis | None = None
ROOT_DIR = Path(__file__).resolve().parents[2]
RUNTIME_DIR = ROOT_DIR / ".runtime"
WORKER_PID_FILE = RUNTIME_DIR / "worker.pid"
WORKER_LOG_FILE = RUNTIME_DIR / "worker.log"


def annotated_mjpeg_frames(camera_id: str, _source_url: str, _config: dict | None = None):
    yield from redis_mjpeg_frames(camera_id, annotated_frame_key(camera_id))


def raw_mjpeg_frames(camera_id: str, _source_url: str, _config: dict | None = None):
    yield from redis_mjpeg_frames(camera_id, raw_frame_key(camera_id))


def redis_mjpeg_frames(camera_id: str, frame_key: str):
    client = redis_client()
    last_frame = None
    last_waiting_frame_at = 0.0
    waiting_frame = build_waiting_frame(camera_id)
    while True:
        try:
            frame = client.get(frame_key)
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


def ensure_camera_worker(camera_id: str, _source_url: str, _config: dict | None = None, restart: bool = False) -> None:
    clear_camera_runtime_state(camera_id)
    if restart:
        restart_worker_fleet()
        return
    if not worker_is_running():
        start_worker_fleet()


def stop_camera_worker(camera_id: str) -> None:
    clear_camera_runtime_state(camera_id)
    restart_worker_fleet()


def worker_is_running() -> bool:
    pid = read_worker_pid()
    return pid is not None and process_is_running(pid)


def read_worker_pid() -> int | None:
    try:
        value = WORKER_PID_FILE.read_text(encoding="utf-8").strip()
        return int(value) if value else None
    except (OSError, ValueError):
        return None


def process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def restart_worker_fleet() -> None:
    stop_worker_fleet()
    if has_active_rtsp_cameras():
        start_worker_fleet()


def start_worker_fleet() -> None:
    if worker_is_running():
        return
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    env = worker_env()
    command = [sys.executable, str(ROOT_DIR / "scripts" / "cameras" / "run_worker.py")]
    log_handle = WORKER_LOG_FILE.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=str(ROOT_DIR),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    WORKER_PID_FILE.write_text(str(process.pid), encoding="utf-8")


def stop_worker_fleet(timeout_seconds: float = 5.0) -> None:
    pid = read_worker_pid()
    if pid is None:
        return
    if process_is_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + timeout_seconds
        while time.time() < deadline and process_is_running(pid):
            time.sleep(0.1)
        if process_is_running(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
    try:
        WORKER_PID_FILE.unlink()
    except OSError:
        pass


def has_active_rtsp_cameras() -> bool:
    row = fetch_one(
        """
        SELECT 1
        FROM camera_sources
        WHERE is_active = true
          AND source_type = 'rtsp'
          AND (source_url LIKE 'rtsp://%%' OR source_url LIKE 'rtsps://%%')
        LIMIT 1
        """
    )
    return bool(row)


def clear_camera_runtime_state(camera_id: str) -> None:
    try:
        redis_client().delete(
            raw_frame_key(camera_id),
            annotated_frame_key(camera_id),
            f"camera:{camera_id}:latest_meta",
            f"camera:{camera_id}:status",
        )
    except redis.RedisError:
        pass


def worker_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("INSIGHTFACE_DEVICE", "cuda")
    site_packages = site.getsitepackages()[0]
    library_paths = [
        str(Path(site_packages) / "tensorrt_libs"),
        str(Path(site_packages) / "nvidia" / "cudnn" / "lib"),
        "/usr/local/cuda/targets/sbsa-linux/lib",
        str(Path(site_packages) / "nvidia" / "cu13" / "lib"),
    ]
    current_ld_path = env.get("LD_LIBRARY_PATH")
    if current_ld_path:
        library_paths.append(current_ld_path)
    env["LD_LIBRARY_PATH"] = ":".join(library_paths)
    return env


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
