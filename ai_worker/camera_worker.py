import time
from dataclasses import dataclass
from typing import Any

import cv2
import redis

from alert_manager import AlertManager
from camera_reader import CameraFrameReader
from config import STREAM_PUBLISH_FPS
from face_pipeline import FaceRecognitionPipeline
from metrics_service import MetricsService
from redis_frame_publisher import RedisFramePublisher
from tracker import CentroidTracker
from unknown_event_detector import UnknownEventDetector
from visualization import draw_tracks
from zone_manager import ZoneManager


@dataclass(frozen=True)
class CameraWorkerConfig:
    camera_id: str
    source_url: str
    ai_interval: float = 0.7
    reconnect_delay: float = 5.0
    metrics_interval: float = 30.0
    stream_publish_fps: float = STREAM_PUBLISH_FPS

    @classmethod
    def from_camera_row(cls, row: dict[str, Any]) -> "CameraWorkerConfig":
        config = row.get("config") or {}
        return cls(
            camera_id=row["camera_id"],
            source_url=row["source_url"],
            ai_interval=float(config.get("ai_interval", 0.7)),
            reconnect_delay=float(config.get("reconnect_delay", 5.0)),
            metrics_interval=float(config.get("metrics_interval", 30.0)),
            stream_publish_fps=float(config.get("stream_publish_fps", STREAM_PUBLISH_FPS)),
        )


class CameraWorker:
    def __init__(self, config: CameraWorkerConfig) -> None:
        self.config = config
        self.reader = CameraFrameReader(config.source_url, config.reconnect_delay)
        self.pipeline = FaceRecognitionPipeline()
        self.tracker = CentroidTracker()
        self.zone_manager = ZoneManager()
        self.unknown_detector = UnknownEventDetector()
        self.alert_manager = AlertManager()
        self.metrics_service = MetricsService()
        self.frame_publisher = RedisFramePublisher()
        self.running = False

    def run(self) -> None:
        self.running = True
        self.reader.start()
        last_ai_time = 0.0
        last_metrics_time = 0.0
        last_stream_publish_time = 0.0
        frame_id = 0
        ai_latency_ms = 0.0
        self.metrics_service.update_camera_status(self.config.camera_id, "starting")
        print(f"Worker started: {self.config.camera_id}")

        failed = False
        try:
            while self.running:
                frame = self.reader.get_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                now = time.time()
                if now - last_ai_time >= self.config.ai_interval:
                    ai_start = time.time()
                    try:
                        results = self.pipeline.process_image(frame.copy())
                        self.tracker.update(results)
                        for track in list(self.tracker.tracks.values()):
                            track.zone = self.zone_manager.get_zone(self.config.camera_id, track.bbox)
                            warning = self.unknown_detector.update_track(track, self.config.camera_id)
                            if warning:
                                event = self.alert_manager.save_unknown_warning(frame, warning, self.config.camera_id)
                                print("warning", self.config.camera_id, event["warning_type"], event["event_id"])
                        ai_latency_ms = (time.time() - ai_start) * 1000
                    except Exception as error:
                        ai_latency_ms = (time.time() - ai_start) * 1000
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

                    if now - last_metrics_time >= self.config.metrics_interval:
                        self.metrics_service.write_metric(self.config.camera_id, "read_fps", self.reader.read_fps, "fps")
                        self.metrics_service.write_metric(self.config.camera_id, "camera_fps", self.reader.camera_fps, "fps")
                        self.metrics_service.write_metric(self.config.camera_id, "ai_latency", ai_latency_ms, "ms")
                        self.metrics_service.write_metric(self.config.camera_id, "detected_faces", self.pipeline.last_stats["detected_faces"], "count")
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

                publish_interval = 1.0 / self.config.stream_publish_fps if self.config.stream_publish_fps > 0 else 0.0
                if publish_interval and now - last_stream_publish_time >= publish_interval:
                    frame_id += 1
                    self.publish_stream_frame(frame, frame_id, ai_latency_ms)
                    last_stream_publish_time = now

                time.sleep(0.01)
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
            self.reader.stop()
            if not failed:
                self.metrics_service.update_camera_status(
                    self.config.camera_id,
                    "stopped",
                    self.reader.read_fps,
                    self.reader.camera_fps,
                    ai_latency_ms,
                )
            print(f"Worker stopped: {self.config.camera_id}")

    def publish_stream_frame(self, frame, frame_id: int, ai_latency_ms: float) -> None:
        try:
            annotated = frame.copy()
            self.zone_manager.draw_zones(annotated, self.config.camera_id)
            draw_tracks(annotated, self.tracker.tracks)
            cv2.putText(
                annotated,
                f"read {self.reader.read_fps:.1f} fps | AI {ai_latency_ms:.0f} ms",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            self.frame_publisher.publish(
                self.config.camera_id,
                frame,
                annotated,
                {
                    "frame_id": frame_id,
                    "read_fps": self.reader.read_fps,
                    "camera_fps": self.reader.camera_fps,
                    "ai_latency_ms": ai_latency_ms,
                    "tracks": stream_track_payloads(self.tracker.tracks),
                },
            )
        except (redis.RedisError, ValueError) as error:
            print("stream_publish_error", self.config.camera_id, error)

    def stop(self) -> None:
        self.running = False


def stream_track_payloads(tracks: dict[int, Any]) -> list[dict[str, Any]]:
    payloads = []
    for track in tracks.values():
        payloads.append(
            {
                "track_id": track.track_id,
                "label": track.voted_label(),
                "status": track.voted_status(),
                "score": track.best_score(),
                "bbox": list(track.bbox),
                "zone": track.zone,
            }
        )
    return payloads
