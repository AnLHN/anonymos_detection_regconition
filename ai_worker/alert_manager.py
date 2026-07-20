import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2

from config import EVENT_LOG_PATH, FACE_THRESHOLD, RECOGNITION_DETECTION_SCORE, SNAPSHOT_DIR, TRACK_DETECTION_SCORE
from postgres_event_service import PostgresEventService
from rabbitmq_event_publisher import RabbitMQEventPublisher
from unknown_event_detector import UnknownWarning


class AlertManager:
    def __init__(self, snapshot_dir: Path = SNAPSHOT_DIR, event_log_path: Path = EVENT_LOG_PATH) -> None:
        self.snapshot_dir = snapshot_dir
        self.event_log_path = event_log_path
        self.event_service = PostgresEventService()
        self.event_publisher = RabbitMQEventPublisher()
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

    def save_unknown_warning(self, frame, warning: UnknownWarning, camera_id: str) -> dict:
        event_id = self._event_id()
        full_path = self.snapshot_dir / f"{event_id}_full.jpg"

        cv2.imwrite(str(full_path), annotated_warning_frame(frame, warning))

        recognition = warning.face_result.recognition
        best_candidate = recognition.candidates[0] if recognition.candidates else None
        event = {
            "event_id": event_id,
            "camera_id": camera_id,
            "track_id": warning.track_id,
            "zone": getattr(warning, "zone", "none"),
            "time": datetime.now().isoformat(timespec="seconds"),
            "status": recognition.status,
            "label": recognition.label,
            "score": recognition.score,
            "warning_type": warning.warning_type,
            "warning_level": warning.warning_level,
            "reason": warning.reason,
            "rule_config": warning.rule_config or {},
            "recognition_threshold": FACE_THRESHOLD,
            "detection_threshold": RECOGNITION_DETECTION_SCORE,
            "tracking_detection_threshold": TRACK_DETECTION_SCORE,
            "bbox": list(warning.face_result.face.bbox),
            "best_match": asdict(best_candidate) if best_candidate else None,
            "snapshot_full": str(full_path),
            "snapshot_face": None,
        }
        self._append_event(event)
        self._publish_or_insert_event(event)
        return event

    def resolve_unknown_as_known(self, event_id: str, label: str, score: float | None) -> bool:
        try:
            return self.event_service.resolve_unknown_as_known(event_id, label, score)
        except Exception as error:
            print("alert_resolve_error", event_id, error)
            return False

    def _append_event(self, event: dict) -> None:
        with self.event_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _publish_or_insert_event(self, event: dict) -> None:
        try:
            self.event_publisher.publish_alert_event(event)
        except Exception as error:
            print(f"RabbitMQ publish failed, writing event directly to Postgres: {error}")
            self.event_service.insert_unknown_event(event)

    def _event_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid4().hex[:8]
        return f"EVT_{timestamp}_{suffix}"


def annotated_warning_frame(frame, warning: UnknownWarning):
    annotated = frame.copy()
    height, width = annotated.shape[:2]
    x1, y1, x2, y2 = clamp_bbox(warning.face_result.face.bbox, width, height)
    status = warning.face_result.recognition.status
    color = warning_color(status)
    thickness = 3

    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
    label = warning_label(warning)
    (label_width, label_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    label_y = max(label_height + 12, y1 - 8)
    label_x2 = min(width - 1, x1 + label_width + 12)
    cv2.rectangle(
        annotated,
        (x1, label_y - label_height - baseline - 8),
        (label_x2, label_y + baseline + 4),
        color,
        -1,
    )
    cv2.putText(annotated, label, (x1 + 6, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return annotated


def clamp_bbox(bbox: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = [int(value) for value in bbox]
    x1 = max(0, min(width - 1, x1))
    x2 = max(0, min(width - 1, x2))
    y1 = max(0, min(height - 1, y1))
    y2 = max(0, min(height - 1, y2))
    if x2 <= x1:
        x2 = min(width - 1, x1 + 1)
    if y2 <= y1:
        y2 = min(height - 1, y1 + 1)
    return x1, y1, x2, y2


def warning_color(status: str) -> tuple[int, int, int]:
    if status == "known":
        return (0, 255, 0)
    if status == "unknown":
        return (0, 0, 255)
    return (0, 200, 255)


def warning_label(warning: UnknownWarning) -> str:
    recognition = warning.face_result.recognition
    face = warning.face_result.face
    track = f"ID {warning.track_id}" if warning.track_id is not None else "ID -"
    score = "" if recognition.score is None else f" match={recognition.score:.3f}"
    return f"{track}: {recognition.label} det={face.det_score:.2f}{score}"
