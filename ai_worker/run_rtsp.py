import argparse
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
SYSTEM_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(SYSTEM_DIR))

from alert_manager import AlertManager
from camera_reader import CameraFrameReader
from face_pipeline import FaceRecognitionPipeline
from tracker import CentroidTracker
from unknown_event_detector import UnknownEventDetector
from visualization import draw_tracks
from zone_manager import ZoneManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run realtime RTSP Known/Unknown detection.")
    parser.add_argument("--source", required=True, help="RTSP URL")
    parser.add_argument("--camera-id", default="rtsp_0", help="Camera ID used for zones/events, e.g. gate_01")
    parser.add_argument("--reconnect-delay", type=float, default=3.0, help="Seconds to wait before reconnecting failed stream")
    parser.add_argument("--ai-interval", type=float, default=0.5, help="Seconds between AI processing runs")
    parser.add_argument("--width", type=int, default=1280, help="Display window max width")
    parser.add_argument("--height", type=int, default=720, help="Display window max height")
    parser.add_argument("--process-width", type=int, default=0, help="Deprecated: detection uses original frame; kept for compatibility")
    parser.add_argument("--window", default="Unknown Detection", help="OpenCV window title")
    return parser.parse_args()


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


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    reader = CameraFrameReader(args.source, args.reconnect_delay)
    reader.start()

    pipeline = FaceRecognitionPipeline()
    tracker = CentroidTracker()
    zone_manager = ZoneManager()
    unknown_detector = UnknownEventDetector()
    alert_manager = AlertManager()
    last_warning_text = ""
    last_ai_time = 0.0

    print(f"RTSP camera started: camera_id={args.camera_id}")
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
                results = pipeline.process_image(frame.copy())
                tracker.update(results)
                for track in list(tracker.tracks.values()):
                    track.zone = zone_manager.get_zone(args.camera_id, track.bbox)
                    warning = unknown_detector.update_track(track, args.camera_id)
                    if warning:
                        event = alert_manager.save_unknown_warning(frame, warning, args.camera_id)
                        last_warning_text = f"WARNING {event['warning_level']}: {event['warning_type']} track={event['track_id']}"
                        print(last_warning_text, event["event_id"])
                last_ai_time = now

            display_frame, display_scale_x, display_scale_y = resize_display(frame, args.width, args.height)
            zone_manager.draw_zones(display_frame, args.camera_id, 1 / display_scale_x if display_scale_x else 1.0)
            draw_tracks(display_frame, tracker.tracks, display_scale_x, display_scale_y)
            cv2.putText(display_frame, f"FPS: {reader.read_fps:.1f}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
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
