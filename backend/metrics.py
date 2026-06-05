import json
from datetime import datetime, timezone
from time import perf_counter

import psycopg
import redis
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from psycopg.rows import dict_row
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.config import POSTGRES_DSN, REDIS_URL

REQUEST_COUNT = Counter(
    "unknown_detection_http_requests_total",
    "Total backend HTTP requests",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "unknown_detection_http_request_duration_seconds",
    "Backend HTTP request duration in seconds",
    ["method", "path"],
)
CAMERA_WORKER_RUNNING = Gauge(
    "unknown_detection_camera_worker_running",
    "Camera worker running state, 1 when running else 0",
    ["camera_id"],
)
CAMERA_READ_FPS = Gauge(
    "unknown_detection_camera_read_fps",
    "Latest camera reader FPS reported by the worker",
    ["camera_id"],
)
CAMERA_SOURCE_FPS = Gauge(
    "unknown_detection_camera_fps",
    "Latest source camera FPS reported by the worker",
    ["camera_id"],
)
CAMERA_AI_LATENCY_MS = Gauge(
    "unknown_detection_camera_ai_latency_ms",
    "Latest AI pipeline latency in milliseconds reported by the worker",
    ["camera_id"],
)
CAMERA_LAST_SEEN_AGE_SECONDS = Gauge(
    "unknown_detection_camera_last_seen_age_seconds",
    "Seconds since the camera worker was last seen",
    ["camera_id"],
)
CAMERA_REDIS_FRAME_AVAILABLE = Gauge(
    "unknown_detection_camera_redis_frame_available",
    "Redis latest camera frame key availability",
    ["camera_id", "type"],
)
CAMERA_REDIS_FRAME_AGE_SECONDS = Gauge(
    "unknown_detection_camera_redis_frame_age_seconds",
    "Seconds since latest Redis camera metadata was published",
    ["camera_id"],
)
ALERTS_TOTAL = Gauge(
    "unknown_detection_alerts_total",
    "Unknown event count grouped by warning level, type and review status",
    ["warning_level", "warning_type", "review_status"],
)
AI_DETECTED_FACES = Gauge(
    "unknown_detection_camera_detected_faces",
    "Latest detected face count per camera from the AI pipeline",
    ["camera_id"],
)
AI_KNOWN_FACES = Gauge(
    "unknown_detection_camera_known_faces",
    "Latest known face count per camera from the AI pipeline",
    ["camera_id"],
)
AI_UNKNOWN_FACES = Gauge(
    "unknown_detection_camera_unknown_faces",
    "Latest unknown face count per camera from the AI pipeline",
    ["camera_id"],
)
AI_UNVERIFIED_FACES = Gauge(
    "unknown_detection_camera_unverified_faces",
    "Latest unverified face count per camera from the AI pipeline",
    ["camera_id"],
)
AI_QDRANT_LATENCY_MS = Gauge(
    "unknown_detection_camera_qdrant_latency_ms",
    "Latest Qdrant search latency in milliseconds per camera",
    ["camera_id"],
)

_REDIS_CLIENT: redis.Redis | None = None


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started_at = perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        elapsed = perf_counter() - started_at
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
        return response


def metrics_response() -> Response:
    refresh_runtime_metrics()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def refresh_runtime_metrics() -> None:
    try:
        refresh_camera_worker_metrics()
    except Exception:
        pass
    try:
        refresh_alert_metrics()
    except Exception:
        pass
    try:
        refresh_ai_inference_metrics()
    except Exception:
        pass


def refresh_camera_worker_metrics() -> None:
    rows = fetch_all_metrics(
        """
        SELECT camera_id, status, read_fps, camera_fps, ai_latency_ms, last_seen_at
        FROM camera_worker_status
        """
    )
    redis_client = get_redis_client()
    now = datetime.now(timezone.utc)
    for row in rows:
        camera_id = row["camera_id"]
        CAMERA_WORKER_RUNNING.labels(camera_id).set(1 if row.get("status") == "running" else 0)
        CAMERA_READ_FPS.labels(camera_id).set(float(row.get("read_fps") or 0))
        CAMERA_SOURCE_FPS.labels(camera_id).set(float(row.get("camera_fps") or 0))
        CAMERA_AI_LATENCY_MS.labels(camera_id).set(float(row.get("ai_latency_ms") or 0))
        last_seen_at = normalize_datetime(row.get("last_seen_at"))
        if last_seen_at:
            CAMERA_LAST_SEEN_AGE_SECONDS.labels(camera_id).set(max(0.0, (now - last_seen_at).total_seconds()))
        refresh_redis_frame_metrics(redis_client, camera_id, now)


def refresh_redis_frame_metrics(client: redis.Redis, camera_id: str, now: datetime) -> None:
    keys = {
        "raw": f"camera:{camera_id}:latest_raw_jpeg",
        "annotated": f"camera:{camera_id}:latest_annotated_jpeg",
        "meta": f"camera:{camera_id}:latest_meta",
    }
    for frame_type, key in keys.items():
        CAMERA_REDIS_FRAME_AVAILABLE.labels(camera_id, frame_type).set(1 if client.exists(key) else 0)
    meta = client.get(keys["meta"])
    if not meta:
        return
    payload = json.loads(meta.decode("utf-8") if isinstance(meta, bytes) else str(meta))
    created_at = normalize_datetime(payload.get("created_at"))
    if created_at:
        CAMERA_REDIS_FRAME_AGE_SECONDS.labels(camera_id).set(max(0.0, (now - created_at).total_seconds()))


def refresh_alert_metrics() -> None:
    rows = fetch_all_metrics(
        """
        SELECT warning_level, warning_type, review_status, count(*) AS total
        FROM unknown_events
        WHERE deleted_at IS NULL
        GROUP BY warning_level, warning_type, review_status
        """
    )
    for row in rows:
        ALERTS_TOTAL.labels(
            row.get("warning_level") or "unknown",
            row.get("warning_type") or "unknown",
            row.get("review_status") or "unknown",
        ).set(float(row.get("total") or 0))


def refresh_ai_inference_metrics() -> None:
    rows = fetch_all_metrics(
        """
        SELECT DISTINCT ON (camera_id, metric_name)
            camera_id,
            metric_name,
            metric_value
        FROM system_metrics
        WHERE metric_name IN ('detected_faces', 'known_faces', 'unknown_faces', 'unverified_faces', 'qdrant_latency')
        ORDER BY camera_id, metric_name, created_at DESC
        """
    )
    for row in rows:
        camera_id = row.get("camera_id")
        metric_name = row.get("metric_name")
        metric_value = float(row.get("metric_value") or 0)
        if metric_name == "detected_faces":
            AI_DETECTED_FACES.labels(camera_id).set(metric_value)
        elif metric_name == "known_faces":
            AI_KNOWN_FACES.labels(camera_id).set(metric_value)
        elif metric_name == "unknown_faces":
            AI_UNKNOWN_FACES.labels(camera_id).set(metric_value)
        elif metric_name == "unverified_faces":
            AI_UNVERIFIED_FACES.labels(camera_id).set(metric_value)
        elif metric_name == "qdrant_latency":
            AI_QDRANT_LATENCY_MS.labels(camera_id).set(metric_value)


def get_redis_client() -> redis.Redis:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = redis.Redis.from_url(REDIS_URL, decode_responses=False, socket_connect_timeout=1, socket_timeout=1)
    return _REDIS_CLIENT


def fetch_all_metrics(sql: str, params: tuple = ()) -> list[dict]:
    with psycopg.connect(POSTGRES_DSN, row_factory=dict_row, connect_timeout=2) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def normalize_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
