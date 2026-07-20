import time
from dataclasses import dataclass

import redis

from config import UNKNOWN_ALERT_COOLDOWN_SECONDS, UNKNOWN_REID_THRESHOLD, UNKNOWN_REID_TTL_SECONDS
from face_pipeline import FacePipelineResult
from redis_state import RedisStateService, alert_cooldown_key
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
    rule_config: dict | None = None


class UnknownEventDetector:
    def __init__(self) -> None:
        self.rule_engine = RuleEngine()
        self.redis_state = RedisStateService()
        self.last_alert_by_track_and_type: dict[tuple[int, str], float] = {}
        self.last_low_alert_by_camera_and_type: dict[tuple[str, str], float] = {}

    def update_track(self, track: Track, camera_id: str = "") -> UnknownWarning | None:
        if not track.history:
            return None

        decision = self.rule_engine.evaluate_track(track)
        if not decision.should_alert:
            return None

        target_status = "unverified" if decision.warning_type.startswith("unverified") else "unknown"

        cooldown_key = (track.track_id, decision.warning_type)
        cooldown_seconds = decision.cooldown_seconds or UNKNOWN_ALERT_COOLDOWN_SECONDS
        now = time.time()
        redis_key = alert_cooldown_key(camera_id or "default", decision.warning_type, track.track_id)
        if self._is_in_redis_cooldown(redis_key):
            return None
        last_alert_time = self.last_alert_by_track_and_type.get(cooldown_key, 0.0)
        if now - last_alert_time < cooldown_seconds:
            return None

        camera_redis_key = None
        if decision.warning_level == "low":
            camera_cooldown_key = (camera_id or "default", decision.warning_type)
            camera_redis_key = alert_cooldown_key(camera_id or "default", decision.warning_type)
            if self._is_in_redis_cooldown(camera_redis_key):
                return None
            last_camera_alert_time = self.last_low_alert_by_camera_and_type.get(camera_cooldown_key, 0.0)
            if now - last_camera_alert_time < cooldown_seconds:
                return None
            self.last_low_alert_by_camera_and_type[camera_cooldown_key] = now

        self._set_redis_cooldown(redis_key, cooldown_seconds)
        if camera_redis_key:
            self._set_redis_cooldown(camera_redis_key, cooldown_seconds)
        self.last_alert_by_track_and_type[cooldown_key] = now
        face_result = self._select_face_result(track, target_status)
        if target_status == "unknown":
            similar_unknown = self._find_similar_unknown(camera_id or "default", face_result.face.vector)
            if similar_unknown:
                track.mark_unknown_alert_sent(str(similar_unknown.get("event_id", "reid_suppressed")))
                print(
                    "unknown_reid_suppressed",
                    camera_id,
                    track.track_id,
                    similar_unknown.get("event_id"),
                    f"{float(similar_unknown.get('score', 0.0)):.3f}",
                )
                return None
        return UnknownWarning(
            warning_type=decision.warning_type,
            warning_level=decision.warning_level,
            reason=decision.reason,
            face_result=face_result,
            track_id=track.track_id,
            zone=track.zone,
            rule_config=decision.rule_config,
        )

    def remember_unknown_warning(self, camera_id: str, warning: UnknownWarning, event_id: str) -> None:
        try:
            self.redis_state.set_unknown_reid(
                camera_id or "default",
                event_id,
                warning.face_result.face.vector,
                UNKNOWN_REID_TTL_SECONDS,
            )
        except redis.RedisError:
            pass

    def _is_in_redis_cooldown(self, key: str) -> bool:
        try:
            return self.redis_state.is_in_cooldown(key)
        except redis.RedisError:
            return False

    def _set_redis_cooldown(self, key: str, ttl_seconds: int) -> None:
        try:
            self.redis_state.set_cooldown(key, ttl_seconds)
        except redis.RedisError:
            pass

    def _find_similar_unknown(self, camera_id: str, vector: list[float]) -> dict | None:
        try:
            return self.redis_state.find_similar_unknown_reid(camera_id, vector, UNKNOWN_REID_THRESHOLD)
        except redis.RedisError:
            return None

    def _select_face_result(self, track: Track, target_status: str) -> FacePipelineResult:
        matching_results = [result for result in track.history if result.recognition.status == target_status]
        if matching_results:
            return max(matching_results, key=lambda result: result.quality_score)
        return track.history[-1]
