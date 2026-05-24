import argparse
import sys
import threading
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(SYSTEM_DIR))

from alert_manager import AlertManager
from face_pipeline import FaceRecognitionPipeline
from tracker import CentroidTracker
from unknown_event_detector import UnknownEventDetector
from zone_manager import ZoneManager


COLORS = {
    "known": (0, 255, 0),
    "unknown": (0, 0, 255),
    "unverified": (0, 255, 255),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run realtime camera/RTSP Known/Unknown detection.")
    parser.add_argument("--source", default=None, help="Camera source: webcam index like 0 or RTSP URL")
    parser.add_argument("--camera", type=int, default=0, help="Backward-compatible OpenCV camera index when --source is not set")
    parser.add_argument("--camera-id", default=None, help="Camera ID used for zones/events, e.g. webcam_0 or gate_01")
    parser.add_argument("--reconnect-delay", type=float, default=3.0, help="Seconds to wait before reconnecting failed stream")
    parser.add_argument("--ai-interval", type=float, default=0.5, help="Seconds between AI processing runs")
    parser.add_argument("--width", type=int, default=1280, help="Display window max width")
    parser.add_argument("--height", type=int, default=720, help="Display window max height")
    parser.add_argument("--process-width", type=int, default=0, help="Deprecated: detection uses original frame; kept for compatibility")
    parser.add_argument("--window", default="Unknown Detection", help="OpenCV window title")
    return parser.parse_args()


def resolve_source(args: argparse.Namespace):
    if args.source is None:
        return args.camera
    if str(args.source).isdigit():
        return int(args.source)
    return args.source


def open_capture(source):
    if isinstance(source, int):
        return cv2.VideoCapture(source, cv2.CAP_DSHOW)
    return cv2.VideoCapture(source, cv2.CAP_FFMPEG)


def camera_info(cap) -> dict:
    return {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
    }


class CameraFrameReader:
    def __init__(self, source, reconnect_delay: float) -> None:
        self.source = source
        self.reconnect_delay = reconnect_delay
        self.lock = threading.Lock()
        self.latest_frame = None
        self.read_fps = 0.0
        self.camera_fps = 0.0
        self.info = {"width": 0, "height": 0, "fps": 0.0}
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

    def _run(self) -> None:
        cap = None
        last_read_time = time.time()
        while self.running:
            if cap is None or not cap.isOpened():
                cap = open_capture(self.source)
                if not cap.isOpened():
                    time.sleep(self.reconnect_delay)
                    continue
                self.info = camera_info(cap)
                if self.info["fps"] and self.info["fps"] > 0:
                    self.camera_fps = self.info["fps"]

            ok, frame = cap.read()
            if not ok:
                cap.release()
                cap = None
                time.sleep(self.reconnect_delay)
                continue

            now = time.time()
            elapsed = now - last_read_time
            if elapsed > 0:
                self.read_fps = 0.9 * self.read_fps + 0.1 * (1.0 / elapsed)
            last_read_time = now

            with self.lock:
                self.latest_frame = frame

        if cap is not None:
            cap.release()


def resize_display(frame, width: int, height: int):
    if width <= 0 or height <= 0:
        return frame, 1.0, 1.0
    source_height, source_width = frame.shape[:2]
    scale = min(width / source_width, height / source_height)
    target_width = int(source_width * scale)
    target_height = int(source_height * scale)
    if target_width == source_width and target_height == source_height:
        return frame, 1.0, 1.0
    resized = cv2.resize(frame, (target_width, target_height))
    return resized, target_width / source_width, target_height / source_height


def draw_tracks(frame, tracks, scale_x: float = 1.0, scale_y: float = 1.0) -> None:
    for track in tracks.values():
        if not track.history:
            continue
        status = track.voted_status()
        color = COLORS.get(status, (255, 255, 255))
        x1, x2 = int(track.bbox[0] * scale_x), int(track.bbox[2] * scale_x)
        y1, y2 = int(track.bbox[1] * scale_y), int(track.bbox[3] * scale_y)
        score = track.best_score()
        score_text = "" if score is None else f" {score:.3f}"
        zone_text = "" if track.zone == "none" else f" [{track.zone}]"
        label = f"ID {track.track_id}: {track.voted_label()}{score_text}{zone_text}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    source = resolve_source(args)
    camera_id = args.camera_id or (f"webcam_{source}" if isinstance(source, int) else "rtsp_0")
    reader = CameraFrameReader(source, args.reconnect_delay)
    reader.start()

    pipeline = FaceRecognitionPipeline()
    tracker = CentroidTracker()
    zone_manager = ZoneManager()
    unknown_detector = UnknownEventDetector()
    alert_manager = AlertManager()
    last_warning_text = ""
    last_ai_time = 0.0
    ai_fps = 0.0

    print(f"Camera started: camera_id={camera_id} source={source}")
    print("Pipeline: reader thread keeps latest frame; AI runs on latest frame by interval")
    print("Press q to quit.")
    cv2.namedWindow(args.window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(args.window, args.width, args.height)

    try:
        while True:
            frame = reader.get_frame()
            if frame is None:
                time.sleep(0.03)
                continue

            now = time.time()
            if now - last_ai_time >= args.ai_interval:
                ai_start = time.time()
                results = pipeline.process_image(frame.copy())
                tracker.update(results)
                for track in list(tracker.tracks.values()):
                    track.zone = zone_manager.get_zone(camera_id, track.bbox)
                    warning = unknown_detector.update_track(track)
                    if warning:
                        event = alert_manager.save_unknown_warning(frame, warning, camera_id)
                        last_warning_text = f"WARNING {event['warning_level']}: {event['warning_type']} track={event['track_id']}"
                        print(last_warning_text, event["event_id"])
                ai_elapsed = time.time() - ai_start
                if ai_elapsed > 0:
                    ai_fps = 1.0 / ai_elapsed
                last_ai_time = now

            display_frame, display_scale_x, display_scale_y = resize_display(frame, args.width, args.height)
            zone_manager.draw_zones(display_frame, camera_id, 1 / display_scale_x if display_scale_x else 1.0)
            draw_tracks(display_frame, tracker.tracks, display_scale_x, display_scale_y)

            cv2.putText(
                display_frame,
                f"FPS: {reader.read_fps:.1f}",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            if last_warning_text:
                cv2.putText(display_frame, last_warning_text, (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow(args.window, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        reader.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
