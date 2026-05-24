import time
from dataclasses import dataclass

from config import UNKNOWN_ALERT_COOLDOWN_SECONDS
from face_pipeline import FacePipelineResult
from rule_engine import RuleEngine
from tracker import Track


@dataclass(frozen=True)
class UnknownWarning:
    warning_type: str
    warning_level: str
    reason: str
    face_result: FacePipelineResult
    track_id: int | None = None
    zone: str = "none"


class UnknownEventDetector:
    def __init__(self) -> None:
        self.rule_engine = RuleEngine()
        self.last_alert_by_track_and_type: dict[tuple[int, str], float] = {}

    def update_track(self, track: Track) -> UnknownWarning | None:
        if not track.history:
            return None

        decision = self.rule_engine.evaluate_track(track)
        if not decision.should_alert:
            return None

        cooldown_key = (track.track_id, decision.warning_type)
        now = time.time()
        last_alert_time = self.last_alert_by_track_and_type.get(cooldown_key, 0.0)
        if now - last_alert_time < UNKNOWN_ALERT_COOLDOWN_SECONDS:
            return None

        self.last_alert_by_track_and_type[cooldown_key] = now
        face_result = max(
            track.history,
            key=lambda result: result.face.det_score,
        )
        return UnknownWarning(
            warning_type=decision.warning_type,
            warning_level=decision.warning_level,
            reason=decision.reason,
            face_result=face_result,
            track_id=track.track_id,
            zone=track.zone,
        )
