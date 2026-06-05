import time
from dataclasses import dataclass

import redis

from config import UNKNOWN_ALERT_COOLDOWN_SECONDS
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
            rule_config=decision.rule_config,
        )

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
