from collections import deque
import time
import threading
from dataclasses import dataclass
from typing import Any

import cv2
import redis

from alert_manager import AlertManager
from camera_reader import CameraFrameReader
from camera_source_repository import CameraSourceRepository
from config import (
    CAMERA_ZONE_RELOAD_INTERVAL_SECONDS,
    DEBUG_ANNOTATED_STREAM,
    DEFAULT_AI_INTERVAL,
    FACE_THRESHOLD,
    INSIGHTFACE_DET_SIZE,
    RECOGNITION_DETECTION_SCORE,
    RECOGNITION_MIN_FACE_HEIGHT,
    RECOGNITION_MIN_FACE_WIDTH,
    STREAM_PUBLISH_FPS,
    TRACKER_TYPE,
    TRACK_DETECTION_SCORE,
    TRACK_MIN_FACE_HEIGHT,
    TRACK_MIN_FACE_WIDTH,
)
from face_pipeline import FaceRecognitionPipeline
from metrics_service import MetricsService
from redis_frame_publisher import RedisFramePublisher
from tracker_factory import create_tracker
from unknown_event_detector import UnknownEventDetector
from visualization import draw_tracks
from zone_manager import ZoneManager


@dataclass(frozen=True)
class CameraWorkerConfig:
    camera_id: str
    source_url: str
    ai_interval: float = DEFAULT_AI_INTERVAL
    reconnect_delay: float = 5.0
    metrics_interval: float = 30.0
    stream_publish_fps: float = STREAM_PUBLISH_FPS
    zone_reload_interval: float = CAMERA_ZONE_RELOAD_INTERVAL_SECONDS
    debug_annotated_stream: bool = DEBUG_ANNOTATED_STREAM
    zones: dict[str, Any] | None = None

    @classmethod
    def from_camera_row(cls, row: dict[str, Any]) -> "CameraWorkerConfig":
        config = row.get("config") or {}
        return cls(
            camera_id=row["camera_id"],
            source_url=row["source_url"],
            ai_interval=float(config.get("ai_interval", DEFAULT_AI_INTERVAL)),
            reconnect_delay=float(config.get("reconnect_delay", 5.0)),
            metrics_interval=float(config.get("metrics_interval", 30.0)),
            stream_publish_fps=float(config.get("stream_publish_fps", STREAM_PUBLISH_FPS)),
            zone_reload_interval=float(config.get("zone_reload_interval", CAMERA_ZONE_RELOAD_INTERVAL_SECONDS)),
            debug_annotated_stream=parse_bool(config.get("debug_annotated_stream", DEBUG_ANNOTATED_STREAM)),
            zones=config.get("zones") or {},
        )


class CameraWorker:
    def __init__(self, config: CameraWorkerConfig) -> None:
        self.config = config
        self.reader = CameraFrameReader(config.source_url, config.reconnect_delay)
        self.pipeline = FaceRecognitionPipeline()
        self.tracker = create_tracker()
        self.zone_manager = ZoneManager(config.zones, config.camera_id)
        self.camera_repository = CameraSourceRepository()
        self.unknown_detector = UnknownEventDetector()
        self.alert_manager = AlertManager()
        self.metrics_service = MetricsService()
        self.frame_publisher = RedisFramePublisher()
        self.running = False
        self.state_lock = threading.Lock()
        self.ai_latency_ms = 0.0
        self.ai_processed_fps = 0.0

    def run(self) -> None:
        self.running = True
        self.reader.start()
        stream_thread = threading.Thread(target=self.publish_stream_loop, daemon=True)
        stream_thread.start()
        last_ai_time = 0.0
        last_metrics_time = 0.0
        last_zone_reload_time = 0.0
        last_ai_source_frame_id = 0
        ai_fps_meter = RollingFpsMeter()
        ai_latency_ms = 0.0
        self.metrics_service.update_camera_status(self.config.camera_id, "starting")
        print(f"Worker started: {self.config.camera_id}")
        print(
            "AI config:",
            f"det_size={INSIGHTFACE_DET_SIZE}",
            f"track_det={TRACK_DETECTION_SCORE}",
            f"recognition_det={RECOGNITION_DETECTION_SCORE}",
            f"reco_thresh={FACE_THRESHOLD}",
            f"track_min_face={TRACK_MIN_FACE_WIDTH}x{TRACK_MIN_FACE_HEIGHT}",
            f"recognition_min_face={RECOGNITION_MIN_FACE_WIDTH}x{RECOGNITION_MIN_FACE_HEIGHT}",
            f"tracker={TRACKER_TYPE}",
            f"ai_interval={self.config.ai_interval}",
        )

        failed = False
        try:
            while self.running:
                frame_payload = self.reader.get_frame_with_id()
                if frame_payload is None:
                    time.sleep(0.05)
                    continue
                frame, source_frame_id = frame_payload

                now = time.time()
                if self.config.zone_reload_interval > 0 and now - last_zone_reload_time >= self.config.zone_reload_interval:
                    self.reload_zones()
                    last_zone_reload_time = now

                should_process_ai = self.config.ai_interval <= 0 or now - last_ai_time >= self.config.ai_interval
                if should_process_ai and source_frame_id != last_ai_source_frame_id:
                    ai_start = time.time()
                    try:
                        results = self.pipeline.process_image(frame.copy())
                        ai_end = time.time()
                        ai_latency_ms = (ai_end - ai_start) * 1000
                        ai_processed_fps = clamp_model_fps(
                            ai_fps_meter.mark(ai_end),
                            self.reader.read_fps,
                            self.reader.camera_fps,
                        )
                        with self.state_lock:
                            self.tracker.update(results)
                            for track in list(self.tracker.tracks.values()):
                                track.zone = self.zone_manager.get_zone(self.config.camera_id, track.bbox)
                                self.resolve_track_if_needed(track)
                                warning = self.unknown_detector.update_track(track, self.config.camera_id)
                                if warning:
                                    event = self.alert_manager.save_unknown_warning(frame, warning, self.config.camera_id)
                                    self.unknown_detector.remember_unknown_warning(self.config.camera_id, warning, event["event_id"])
                                    track.mark_unknown_alert_sent(event["event_id"])
                                    print("warning", self.config.camera_id, event["warning_type"], event["event_id"])
                            self.ai_latency_ms = ai_latency_ms
                            self.ai_processed_fps = ai_processed_fps
                    except Exception as error:
                        ai_latency_ms = (time.time() - ai_start) * 1000
                        self.ai_latency_ms = ai_latency_ms
                        self.metrics_service.update_camera_status(
                            self.config.camera_id,
                            "degraded",
                            self.reader.read_fps,
                            self.reader.camera_fps,
                            ai_latency_ms,
                            f"AI pipeline error: {error}",
                        )
                        print("ai_pipeline_error", self.config.camera_id, error)
                    last_ai_time = now
                    last_ai_source_frame_id = source_frame_id

                    if now - last_metrics_time >= self.config.metrics_interval:
                        self.metrics_service.write_metric(self.config.camera_id, "read_fps", self.reader.read_fps, "fps")
                        self.metrics_service.write_metric(self.config.camera_id, "camera_fps", self.reader.camera_fps, "fps")
                        self.metrics_service.write_metric(self.config.camera_id, "ai_latency", ai_latency_ms, "ms")
                        self.metrics_service.write_metric(self.config.camera_id, "detected_faces", self.pipeline.last_stats["detected_faces"], "count")
                        self.metrics_service.write_metric(self.config.camera_id, "trackable_faces", self.pipeline.last_stats["trackable_faces"], "count")
                        self.metrics_service.write_metric(self.config.camera_id, "recognition_eligible_faces", self.pipeline.last_stats["recognition_eligible_faces"], "count")
                        self.metrics_service.write_metric(self.config.camera_id, "known_faces", self.pipeline.last_stats["known_faces"], "count")
                        self.metrics_service.write_metric(self.config.camera_id, "unknown_faces", self.pipeline.last_stats["unknown_faces"], "count")
                        self.metrics_service.write_metric(self.config.camera_id, "unverified_faces", self.pipeline.last_stats["unverified_faces"], "count")
                        self.metrics_service.write_metric(self.config.camera_id, "qdrant_latency", self.pipeline.last_stats["qdrant_latency_ms"], "ms")
                        self.metrics_service.update_camera_status(
                            self.config.camera_id,
                            "running",
                            self.reader.read_fps,
                            self.reader.camera_fps,
                            ai_latency_ms,
                        )
                        last_metrics_time = now

                if self.config.ai_interval > 0:
                    time.sleep(0.01)
                else:
                    time.sleep(0)
        except Exception as error:
            failed = True
            self.metrics_service.update_camera_status(
                self.config.camera_id,
                "error",
                self.reader.read_fps,
                self.reader.camera_fps,
                ai_latency_ms,
                str(error),
            )
            raise
        finally:
            self.running = False
            self.reader.stop()
            stream_thread.join(timeout=2)
            print(f"Worker stopped: {self.config.camera_id}")

    def publish_stream_loop(self) -> None:
        publish_interval = 1.0 / self.config.stream_publish_fps if self.config.stream_publish_fps > 0 else 0.0
        if publish_interval <= 0:
            return

        frame_id = 0
        last_stream_publish_time = 0.0
        while self.running:
            now = time.time()
            sleep_seconds = publish_interval - (now - last_stream_publish_time)
            if sleep_seconds > 0:
                time.sleep(min(sleep_seconds, 0.05))
                continue

            frame = self.reader.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            frame_id += 1
            self.publish_stream_frame(frame, frame_id, self.ai_latency_ms)
            last_stream_publish_time = time.time()

    def publish_stream_frame(self, frame, frame_id: int, ai_latency_ms: float) -> None:
        try:
            with self.state_lock:
                tracks = stream_track_payloads(self.tracker.tracks)
                zones = self.zone_manager.to_payload()
                ai_processed_fps = self.ai_processed_fps
                annotated = self.build_debug_annotated_frame(frame, ai_latency_ms) if self.config.debug_annotated_stream else frame
            source_height, source_width = frame.shape[:2]
            self.frame_publisher.publish(
                self.config.camera_id,
                frame,
                annotated,
                {
                    "camera_id": self.config.camera_id,
                    "frame_id": frame_id,
                    "source_width": source_width,
                    "source_height": source_height,
                    "read_fps": self.reader.read_fps,
                    "camera_fps": self.reader.camera_fps,
                    "ai_latency_ms": ai_latency_ms,
                    "ai_interval": self.config.ai_interval,
                    "ai_update_fps": ai_processed_fps,
                    "model_latency_fps": latency_capacity_fps(ai_latency_ms),
                    "stream_publish_fps": self.config.stream_publish_fps,
                    "tracks": tracks,
                    "zones": zones,
                },
            )
        except (redis.RedisError, ValueError) as error:
            print("stream_publish_error", self.config.camera_id, error)

    def stop(self) -> None:
        self.running = False

    def resolve_track_if_needed(self, track) -> None:
        pending = track.consume_pending_unknown_resolution()
        if pending is None:
            return
        event_id, label, score = pending
        if self.alert_manager.resolve_unknown_as_known(event_id, label, score):
            print("warning_resolved_known", self.config.camera_id, event_id, label, score)
            return
        track.restore_pending_unknown_resolution(event_id, label, score)

    def reload_zones(self) -> None:
        try:
            row = self.camera_repository.get_camera(self.config.camera_id)
        except Exception as error:
            print("zone_reload_error", self.config.camera_id, error)
            return
        config = row.get("config") if row else {}
        self.zone_manager = ZoneManager((config or {}).get("zones") or {}, self.config.camera_id)

    def build_debug_annotated_frame(self, frame, ai_latency_ms: float):
        annotated = frame.copy()
        self.zone_manager.draw_zones(annotated, self.config.camera_id)
        draw_tracks(annotated, self.tracker.tracks)
        cv2.putText(
            annotated,
            f"stream {self.config.stream_publish_fps:.1f} fps | AI {self.ai_processed_fps:.1f} fps | {ai_latency_ms:.0f} ms",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        return annotated


def latency_capacity_fps(ai_latency_ms: float) -> float:
    if ai_latency_ms > 0:
        return 1000.0 / ai_latency_ms
    return 0.0


def clamp_model_fps(value: float, read_fps: float, camera_fps: float) -> float:
    ceilings = [fps for fps in (read_fps, camera_fps) if fps > 0]
    if not ceilings:
        return max(0.0, value)
    return max(0.0, min(value, max(ceilings)))


class RollingFpsMeter:
    def __init__(self, window_seconds: float = 5.0) -> None:
        self.window_seconds = window_seconds
        self.timestamps: deque[float] = deque()

    def mark(self, now: float) -> float:
        self.timestamps.append(now)
        cutoff = now - self.window_seconds
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
        if len(self.timestamps) < 2:
            return 0.0
        elapsed = self.timestamps[-1] - self.timestamps[0]
        if elapsed <= 0:
            return 0.0
        return (len(self.timestamps) - 1) / elapsed


def stream_track_payloads(tracks: dict[int, Any]) -> list[dict[str, Any]]:
    payloads = []
    for track in tracks.values():
        payloads.append(
            {
                "track_id": track.track_id,
                "label": track.voted_label(),
                "status": track.voted_status(),
                "identity_status": track.identity_status,
                "score": track.best_score(),
                "bbox": list(track.bbox),
                "zone": track.zone,
                "unknown_alert_sent": track.unknown_alert_sent,
                "unknown_alert_event_id": track.unknown_alert_event_id,
            }
        )
    return payloads


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
