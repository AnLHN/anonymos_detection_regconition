import json
from datetime import datetime
from typing import Any

import redis

from config import REDIS_URL

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


def camera_status_key(camera_id: str) -> str:
    return f"camera:{camera_id}:status"


def alert_cooldown_key(camera_id: str, warning_type: str, track_id: int | None = None) -> str:
    track_part = "camera" if track_id is None else f"track:{track_id}"
    return f"alert_cooldown:{camera_id}:{warning_type}:{track_part}"
