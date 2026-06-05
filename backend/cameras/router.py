import json
import time
from datetime import datetime, timezone
from typing import Any

import cv2
import redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend.auth.security import get_current_user, require_permission
from backend.cameras.annotated_stream import annotated_mjpeg_frames, ensure_camera_worker, stop_camera_worker
from backend.config import MEDIAMTX_PUBLIC_WEBRTC_BASE_URL, REDIS_URL
from backend.database.postgres import execute, fetch_all, fetch_one

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_user)])
require_camera_read = require_permission("cameras:read")
require_camera_create = require_permission("cameras:create")
require_camera_update = require_permission("cameras:update")
_RUNTIME_REDIS: redis.Redis | None = None
CAMERA_RELOAD_LOCK_SECONDS = 30


class CameraCreate(BaseModel):
    camera_id: str
    name: str
    source_type: str = "rtsp"
    source_url: str
    location: str = ""
    is_active: bool = True
    config: dict[str, Any] = {}


class CameraUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    location: str | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None


def validate_rtsp_source(source_type: str | None, source_url: str | None) -> None:
    if source_type is not None and source_type != "rtsp":
        raise HTTPException(status_code=400, detail="Only RTSP camera sources are supported")
    if source_url is not None and not source_url.lower().startswith(("rtsp://", "rtsps://")):
        raise HTTPException(status_code=400, detail="Camera source_url must be an RTSP URL")


def probe_rtsp_source(source_url: str, timeout_seconds: float = 5.0) -> tuple[bool, float, str | None]:
    started_at = time.time()
    cap = cv2.VideoCapture(source_url, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            return False, 0.0, "RTSP stream could not be opened"
        ok, frame = cap.read()
        camera_fps = as_float(cap.get(cv2.CAP_PROP_FPS))
        if not ok or frame is None:
            return False, camera_fps, "RTSP stream opened but no frame was received"
        if time.time() - started_at > timeout_seconds:
            return False, camera_fps, "RTSP probe timed out"
        return True, camera_fps, None
    except Exception as error:
        return False, 0.0, str(error)
    finally:
        cap.release()


def write_camera_worker_status(camera_id: str, status: str, camera_fps: float = 0.0, last_error: str | None = None) -> None:
    execute(
        """
        INSERT INTO camera_worker_status (
            camera_id, status, read_fps, camera_fps, ai_latency_ms, last_error, last_seen_at, updated_at
        )
        VALUES (%s, %s, 0, %s, 0, %s, now(), now())
        ON CONFLICT (camera_id) DO UPDATE
        SET status = EXCLUDED.status,
            camera_fps = EXCLUDED.camera_fps,
            last_error = EXCLUDED.last_error,
            last_seen_at = now(),
            updated_at = now()
        """,
        (camera_id, status, camera_fps, last_error),
    )


def runtime_redis_client() -> redis.Redis:
    global _RUNTIME_REDIS
    if _RUNTIME_REDIS is None:
        _RUNTIME_REDIS = redis.Redis.from_url(REDIS_URL, decode_responses=False, socket_connect_timeout=1, socket_timeout=1)
    return _RUNTIME_REDIS


def camera_reload_lock_key(camera_id: str) -> str:
    return f"camera:{camera_id}:reload_lock"


def acquire_camera_reload_lock(camera_id: str) -> bool:
    try:
        return bool(runtime_redis_client().set(camera_reload_lock_key(camera_id), "1", nx=True, ex=CAMERA_RELOAD_LOCK_SECONDS))
    except redis.RedisError as error:
        raise HTTPException(status_code=503, detail=f"Reload lock unavailable: {error}") from error


def read_latest_meta(client: redis.Redis, camera_id: str) -> dict[str, Any] | None:
    try:
        payload = client.get(f"camera:{camera_id}:latest_meta")
    except redis.RedisError:
        return None
    if not payload:
        return None
    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_datetime(value: Any) -> str | None:
    parsed = parse_datetime(value)
    return parsed.isoformat() if parsed else None


def as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def latency_to_fps(ai_latency_ms: float) -> float:
    if ai_latency_ms <= 0:
        return 0.0
    return 1000.0 / max(ai_latency_ms, 1.0)


@router.get("")
def list_cameras(_current_user=Depends(require_camera_read)) -> list[dict]:
    cameras = fetch_all(
        """
        SELECT c.camera_id, c.name, c.source_type, c.source_url, c.location, c.is_active,
               c.config, c.created_at, c.updated_at,
               s.status AS worker_status, s.read_fps, s.camera_fps, s.ai_latency_ms,
               s.last_error, s.last_seen_at
        FROM camera_sources c
        LEFT JOIN camera_worker_status s ON s.camera_id = c.camera_id
        WHERE c.source_type = 'rtsp'
        ORDER BY c.camera_id
        """
    )
    prewarm_always_on_cameras(cameras)
    return cameras


@router.post("")
def create_camera(payload: CameraCreate, _current_user=Depends(require_camera_create)) -> dict[str, str]:
    validate_rtsp_source(payload.source_type, payload.source_url)
    config = normalize_camera_config(payload.config)
    execute(
        """
        INSERT INTO camera_sources (camera_id, name, source_type, source_url, location, is_active, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (camera_id) DO UPDATE
        SET name = EXCLUDED.name,
            source_type = EXCLUDED.source_type,
            source_url = EXCLUDED.source_url,
            location = EXCLUDED.location,
            is_active = EXCLUDED.is_active,
            config = EXCLUDED.config,
            updated_at = now()
        """,
        (
            payload.camera_id,
            payload.name,
            payload.source_type,
            payload.source_url,
            payload.location,
            payload.is_active,
            Jsonb(config),
        ),
    )
    apply_camera_worker_state(payload.camera_id, payload.source_url, payload.source_type, payload.is_active, config)
    return {"status": "ok"}


@router.get("/runtime")
def list_camera_runtime(_current_user=Depends(require_camera_read)) -> list[dict[str, Any]]:
    cameras = fetch_all(
        """
        SELECT c.camera_id, c.name, c.location,
               s.status AS worker_status, s.read_fps, s.camera_fps, s.ai_latency_ms,
               s.last_error, s.last_seen_at
        FROM camera_sources c
        LEFT JOIN camera_worker_status s ON s.camera_id = c.camera_id
        WHERE c.source_type = 'rtsp' AND c.is_active = true
        ORDER BY c.camera_id
        """
    )
    client = runtime_redis_client()
    now = datetime.now(timezone.utc)
    rows: list[dict[str, Any]] = []
    for camera in cameras:
        meta = read_latest_meta(client, camera["camera_id"])
        created_at = parse_datetime(meta.get("created_at")) if meta else None
        age_seconds = (now - created_at).total_seconds() if created_at else None
        read_fps = as_float(meta.get("read_fps") if meta else camera.get("read_fps"))
        camera_fps = as_float(meta.get("camera_fps") if meta else camera.get("camera_fps"))
        ai_latency_ms = as_float(meta.get("ai_latency_ms") if meta else camera.get("ai_latency_ms"))
        tracks = meta.get("tracks") if meta and isinstance(meta.get("tracks"), list) else []
        rows.append(
            {
                "camera_id": camera["camera_id"],
                "name": camera.get("name"),
                "location": camera.get("location"),
                "worker_status": camera.get("worker_status"),
                "read_fps": read_fps,
                "camera_fps": camera_fps,
                "ai_latency_ms": ai_latency_ms,
                "model_fps": latency_to_fps(ai_latency_ms),
                "frame_id": meta.get("frame_id") if meta else None,
                "tracks_count": len(tracks),
                "meta_age_seconds": age_seconds,
                "updated_at": meta.get("created_at") if meta else iso_datetime(camera.get("last_seen_at")),
                "is_realtime": age_seconds is not None and age_seconds <= 3,
                "last_error": camera.get("last_error"),
            }
        )
    return rows


@router.get("/{camera_id}/live")
def get_camera_live(camera_id: str, _current_user=Depends(require_camera_read)) -> dict[str, str]:
    camera = fetch_one(
        """
        SELECT camera_id, source_type, source_url, is_active
        FROM camera_sources
        WHERE camera_id = %s
        """,
        (camera_id,),
    )
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not camera["is_active"]:
        raise HTTPException(status_code=400, detail="Camera is inactive")
    if camera["source_type"] != "rtsp":
        raise HTTPException(status_code=400, detail="Live WebRTC is only available for RTSP cameras")
    validate_rtsp_source(camera["source_type"], camera["source_url"])

    stream_name = camera["camera_id"]
    base_url = MEDIAMTX_PUBLIC_WEBRTC_BASE_URL.rstrip("/")
    return {
        "camera_id": camera["camera_id"],
        "stream_name": stream_name,
        "webrtc_url": f"{base_url}/{stream_name}/whep",
    }


@router.get("/{camera_id}/mjpeg")
def stream_camera_mjpeg(camera_id: str, _current_user=Depends(require_camera_read)) -> StreamingResponse:
    camera = fetch_one(
        """
        SELECT camera_id, source_url, source_type, is_active, config
        FROM camera_sources
        WHERE camera_id = %s
        """,
        (camera_id,),
    )
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not camera["is_active"]:
        raise HTTPException(status_code=400, detail="Camera is inactive")
    if camera["source_type"] != "rtsp":
        raise HTTPException(status_code=400, detail="Only RTSP camera sources are supported")
    if not camera["source_url"]:
        raise HTTPException(status_code=400, detail="Camera source is empty")
    validate_rtsp_source(camera["source_type"], camera["source_url"])

    return StreamingResponse(
        annotated_mjpeg_frames(camera["camera_id"], camera["source_url"], camera.get("config") or {}),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.patch("/{camera_id}")
def update_camera(camera_id: str, payload: CameraUpdate, _current_user=Depends(require_camera_update)) -> dict[str, str]:
    validate_rtsp_source(payload.source_type, payload.source_url)
    fields = []
    params = []
    for field_name in ["name", "source_type", "source_url", "location", "is_active"]:
        value = getattr(payload, field_name)
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)
    normalized_config = normalize_camera_config(payload.config) if payload.config is not None else None
    if normalized_config is not None:
        fields.append("config = %s")
        params.append(Jsonb(normalized_config))
    if not fields:
        return {"status": "ok"}

    fields.append("updated_at = now()")
    params.append(camera_id)
    execute(
        f"""
        UPDATE camera_sources
        SET {", ".join(fields)}
        WHERE camera_id = %s
        """,
        tuple(params),
    )
    camera = fetch_one(
        """
        SELECT camera_id, source_url, source_type, is_active, config
        FROM camera_sources
        WHERE camera_id = %s
        """,
        (camera_id,),
    )
    if camera:
        apply_camera_worker_state(camera["camera_id"], camera["source_url"], camera["source_type"], camera["is_active"], camera.get("config") or {})
    return {"status": "ok"}


@router.post("/{camera_id}/reload")
def reload_camera(camera_id: str, _current_user=Depends(require_camera_update)) -> dict[str, Any]:
    if not acquire_camera_reload_lock(camera_id):
        raise HTTPException(status_code=409, detail="Camera reload is already running or cooling down")

    camera = fetch_one(
        """
        SELECT camera_id, source_url, source_type, is_active, config
        FROM camera_sources
        WHERE camera_id = %s
        """,
        (camera_id,),
    )
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not camera["is_active"]:
        raise HTTPException(status_code=400, detail="Camera is inactive")
    validate_rtsp_source(camera["source_type"], camera["source_url"])
    config = normalize_camera_config(camera.get("config") or {})
    probe_ok, camera_fps, probe_error = probe_rtsp_source(camera["source_url"])
    if not probe_ok:
        write_camera_worker_status(camera["camera_id"], "error", camera_fps, probe_error)
        raise HTTPException(status_code=502, detail=probe_error or "Camera probe failed")
    write_camera_worker_status(camera["camera_id"], "standby", camera_fps, None)
    if config.get("always_on"):
        ensure_camera_worker(camera["camera_id"], camera["source_url"], config)
    return {"status": "ok", "camera_fps": camera_fps, "cooldown_seconds": CAMERA_RELOAD_LOCK_SECONDS}


def normalize_camera_config(config: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(config or {})
    if normalized.get("always_on"):
        normalized.setdefault("mjpeg_idle_timeout", 0)
    return normalized


def prewarm_always_on_cameras(cameras: list[dict]) -> None:
    for camera in cameras:
        config = normalize_camera_config(camera.get("config") or {})
        if camera["source_type"] == "rtsp" and camera["is_active"] and config.get("always_on"):
            ensure_camera_worker(camera["camera_id"], camera["source_url"], config)


def apply_camera_worker_state(camera_id: str, source_url: str, source_type: str, is_active: bool, config: dict[str, Any]) -> None:
    normalized = normalize_camera_config(config)
    if source_type == "rtsp" and is_active and normalized.get("always_on"):
        write_camera_worker_status(camera_id, "standby", 0.0, None)
        ensure_camera_worker(camera_id, source_url, normalized)
        return
    if not is_active:
        stop_camera_worker(camera_id)
        write_camera_worker_status(camera_id, "stopped", 0.0, None)
        return
    if not normalized.get("always_on"):
        write_camera_worker_status(camera_id, "standby", 0.0, None)
