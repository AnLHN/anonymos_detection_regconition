import json
from datetime import datetime
from typing import Any

import cv2
import redis

from config import REDIS_URL, STREAM_FRAME_TTL_SECONDS, STREAM_JPEG_QUALITY


class RedisFramePublisher:
    def __init__(self, redis_url: str = REDIS_URL, ttl_seconds: int = STREAM_FRAME_TTL_SECONDS, jpeg_quality: int = STREAM_JPEG_QUALITY) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self.jpeg_quality = jpeg_quality
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(self.redis_url, decode_responses=False)
        return self._client

    def publish(self, camera_id: str, raw_frame, annotated_frame, meta: dict[str, Any]) -> None:
        raw_jpeg = encode_jpeg(raw_frame, self.jpeg_quality)
        annotated_jpeg = encode_jpeg(annotated_frame, self.jpeg_quality)
        payload = dict(meta)
        payload.setdefault("camera_id", camera_id)
        payload.setdefault("created_at", datetime.now().isoformat(timespec="milliseconds"))
        pipe = self.client.pipeline()
        pipe.setex(raw_frame_key(camera_id), self.ttl_seconds, raw_jpeg)
        pipe.setex(annotated_frame_key(camera_id), self.ttl_seconds, annotated_jpeg)
        pipe.setex(meta_key(camera_id), self.ttl_seconds, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        pipe.execute()


def encode_jpeg(frame, quality: int) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Could not encode camera frame as JPEG")
    return encoded.tobytes()


def raw_frame_key(camera_id: str) -> str:
    return f"camera:{camera_id}:latest_raw_jpeg"


def annotated_frame_key(camera_id: str) -> str:
    return f"camera:{camera_id}:latest_annotated_jpeg"


def meta_key(camera_id: str) -> str:
    return f"camera:{camera_id}:latest_meta"
