import json
import math
from datetime import datetime
from typing import Any

import redis

from config import REDIS_URL, UNKNOWN_REID_THRESHOLD, UNKNOWN_REID_TTL_SECONDS

CAMERA_STATUS_TTL_SECONDS = 120


class RedisStateService:
    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self.redis_url = redis_url
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def is_available(self) -> bool:
        try:
            return bool(self.client.ping())
        except redis.RedisError:
            return False

    def set_camera_status(
        self,
        camera_id: str,
        status: str,
        read_fps: float = 0.0,
        camera_fps: float = 0.0,
        ai_latency_ms: float = 0.0,
        last_error: str | None = None,
    ) -> None:
        payload = {
            "camera_id": camera_id,
            "status": status,
            "read_fps": read_fps,
            "camera_fps": camera_fps,
            "ai_latency_ms": ai_latency_ms,
            "last_error": last_error,
            "last_seen_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.client.setex(camera_status_key(camera_id), CAMERA_STATUS_TTL_SECONDS, json.dumps(payload, ensure_ascii=False))

    def get_camera_status(self, camera_id: str) -> dict[str, Any] | None:
        value = self.client.get(camera_status_key(camera_id))
        if not value:
            return None
        return json.loads(value)

    def set_cooldown(self, key: str, ttl_seconds: int) -> None:
        self.client.setex(key, ttl_seconds, "1")

    def is_in_cooldown(self, key: str) -> bool:
        return bool(self.client.exists(key))

    def set_unknown_reid(
        self,
        camera_id: str,
        event_id: str,
        vector: list[float],
        ttl_seconds: int = UNKNOWN_REID_TTL_SECONDS,
    ) -> None:
        payload = {
            "camera_id": camera_id,
            "event_id": event_id,
            "vector": vector,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.client.setex(unknown_reid_key(camera_id, event_id), ttl_seconds, json.dumps(payload, ensure_ascii=False))

    def find_similar_unknown_reid(
        self,
        camera_id: str,
        vector: list[float],
        threshold: float = UNKNOWN_REID_THRESHOLD,
        scan_count: int = 100,
    ) -> dict[str, Any] | None:
        best_payload = None
        best_score = threshold
        for key in self.client.scan_iter(match=unknown_reid_key(camera_id, "*"), count=scan_count):
            value = self.client.get(key)
            if not value:
                continue
            payload = json.loads(value)
            cached_vector = payload.get("vector") or []
            score = cosine_similarity(vector, cached_vector)
            if score >= best_score:
                best_score = score
                best_payload = {**payload, "score": score}
        return best_payload


def camera_status_key(camera_id: str) -> str:
    return f"camera:{camera_id}:status"


def alert_cooldown_key(camera_id: str, warning_type: str, track_id: int | None = None) -> str:
    track_part = "camera" if track_id is None else f"track:{track_id}"
    return f"alert_cooldown:{camera_id}:{warning_type}:{track_part}"


def unknown_reid_key(camera_id: str, event_id: str) -> str:
    return f"unknown_reid:{camera_id}:{event_id}"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm <= 0 or right_norm <= 0:
        return 0.0
    return dot / (left_norm * right_norm)
