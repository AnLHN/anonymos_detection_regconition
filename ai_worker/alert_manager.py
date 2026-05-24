import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2

from config import EVENT_LOG_PATH, SNAPSHOT_DIR
from postgres_event_service import PostgresEventService
from unknown_event_detector import UnknownWarning


class AlertManager:
    def __init__(self, snapshot_dir: Path = SNAPSHOT_DIR, event_log_path: Path = EVENT_LOG_PATH) -> None:
        self.snapshot_dir = snapshot_dir
        self.event_log_path = event_log_path
        self.event_service = PostgresEventService()
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

    def save_unknown_warning(self, frame, warning: UnknownWarning, camera_id: str) -> dict:
        event_id = self._event_id()
        full_path = self.snapshot_dir / f"{event_id}_full.jpg"
        face_path = self.snapshot_dir / f"{event_id}_face.jpg"

        cv2.imwrite(str(full_path), frame)
        face_crop = self._crop_face(frame, warning)
        if face_crop is not None:
            cv2.imwrite(str(face_path), face_crop)
        else:
            face_path = None

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
            "bbox": list(warning.face_result.face.bbox),
            "best_match": asdict(best_candidate) if best_candidate else None,
            "snapshot_full": str(full_path),
            "snapshot_face": str(face_path) if face_path else None,
        }
        self._append_event(event)
        self.event_service.insert_unknown_event(event)
        return event

    def _crop_face(self, frame, warning: UnknownWarning):
        x1, y1, x2, y2 = warning.face_result.face.bbox
        height, width = frame.shape[:2]
        x1 = max(0, min(width, x1))
        x2 = max(0, min(width, x2))
        y1 = max(0, min(height, y1))
        y2 = max(0, min(height, y2))
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]

    def _append_event(self, event: dict) -> None:
        with self.event_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _event_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid4().hex[:8]
        return f"EVT_{timestamp}_{suffix}"
