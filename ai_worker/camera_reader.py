from collections import deque
import threading
import time

import cv2


def resolve_source(source: str) -> str:
    source_url = str(source).strip()
    if not source_url.lower().startswith(("rtsp://", "rtsps://")):
        raise ValueError("Only RTSP camera sources are supported")
    return source_url


def open_capture(source):
    resolved_source = resolve_source(source)
    return cv2.VideoCapture(resolved_source, cv2.CAP_FFMPEG)


def camera_info(cap) -> dict:
    return {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
    }


class CameraFrameReader:
    def __init__(self, source, reconnect_delay: float) -> None:
        self.source = resolve_source(source)
        self.reconnect_delay = reconnect_delay
        self.lock = threading.Lock()
        self.latest_frame = None
        self.latest_frame_id = 0
        self.read_fps = 0.0
        self.camera_fps = 0.0
        self.info = {"width": 0, "height": 0, "fps": 0.0}
        self._read_timestamps: deque[float] = deque()
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def get_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def get_frame_with_id(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy(), self.latest_frame_id

    def _run(self) -> None:
        cap = None
        while self.running:
            if cap is None or not cap.isOpened():
                cap = open_capture(self.source)
                if not cap.isOpened():
                    time.sleep(self.reconnect_delay)
                    continue
                self.info = camera_info(cap)
                if self.info["fps"] and self.info["fps"] > 0:
                    self.camera_fps = self.info["fps"]
                self._read_timestamps.clear()

            ok, frame = cap.read()
            if not ok:
                cap.release()
                cap = None
                time.sleep(self.reconnect_delay)
                continue

            now = time.monotonic()
            self.read_fps = self._rolling_read_fps(now)

            with self.lock:
                self.latest_frame_id += 1
                self.latest_frame = frame

        if cap is not None:
            cap.release()

    def _rolling_read_fps(self, now: float, window_seconds: float = 5.0) -> float:
        self._read_timestamps.append(now)
        cutoff = now - window_seconds
        while self._read_timestamps and self._read_timestamps[0] < cutoff:
            self._read_timestamps.popleft()
        if len(self._read_timestamps) < 2:
            return 0.0
        elapsed = self._read_timestamps[-1] - self._read_timestamps[0]
        if elapsed <= 0:
            return 0.0
        fps = (len(self._read_timestamps) - 1) / elapsed
        if self.camera_fps > 0:
            fps = min(fps, self.camera_fps)
        return max(0.0, fps)
