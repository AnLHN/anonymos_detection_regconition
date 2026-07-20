import json
import shutil
import time
from urllib import request
from urllib.parse import urlencode

import psycopg
import redis
from fastapi import APIRouter, Depends

from backend.auth.security import CurrentUser, require_permission
from backend.config import POSTGRES_DSN, PROMETHEUS_URL, QDRANT_URL, REDIS_URL

router = APIRouter(prefix="/system", tags=["system"])
require_system_read = require_permission("system:read")
_CPU_SAMPLE: tuple[float, float] | None = None


@router.get("/health")
def health(_current_user: CurrentUser = Depends(require_system_read)) -> dict:
    postgres_ok = check_postgres()
    qdrant_ok = check_qdrant()
    redis_ok = check_redis()
    worker_summary = get_worker_summary() if postgres_ok else {"running": 0, "total": 0}
    return {
        "status": "ok" if postgres_ok and qdrant_ok and redis_ok else "degraded",
        "postgres": postgres_ok,
        "qdrant": qdrant_ok,
        "redis": redis_ok,
        "workers": worker_summary,
    }


@router.get("/analytics")
def analytics(_current_user: CurrentUser = Depends(require_system_read)) -> dict:
    health_data = health(_current_user)
    prometheus_ok = prometheus_query("up") is not None
    counts = get_system_counts()
    recent_audit = get_recent_audit_actions()
    request_rate = prometheus_scalar('sum(rate(unknown_detection_http_requests_total[5m]))')
    backend_5xx_rate = prometheus_scalar('sum(rate(unknown_detection_http_requests_total{status=~"5.."}[5m]))')
    auth_failed_rate = prometheus_scalar('sum(rate(unknown_detection_http_requests_total{path="/auth/login",status=~"401|403"}[5m]))')
    forbidden_rate = prometheus_scalar('sum(rate(unknown_detection_http_requests_total{status="403"}[5m]))')
    not_found_rate = prometheus_scalar('sum(rate(unknown_detection_http_requests_total{status="404"}[5m]))')
    cpu_usage = prometheus_scalar('100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])))')
    ram_usage = prometheus_scalar('100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))')
    disk_usage = prometheus_scalar('100 * max(1 - (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}))')
    prometheus_host_metrics = cpu_usage is not None or ram_usage is not None or disk_usage is not None
    if not prometheus_host_metrics:
        native_resources = get_native_resource_usage()
        cpu_usage = native_resources["cpu_percent"]
        ram_usage = native_resources["ram_percent"]
        disk_usage = native_resources["disk_percent"]
    host_metrics_enabled = cpu_usage is not None or ram_usage is not None or disk_usage is not None
    resource_source = "prometheus" if prometheus_host_metrics else "native" if host_metrics_enabled else "none"
    redis_memory = prometheus_scalar("redis_memory_used_bytes")
    postgres_conns = prometheus_scalar("sum(pg_stat_database_numbackends)")
    qdrant_vectors = prometheus_scalar("qdrant_collections_vector_total")
    if qdrant_vectors is None:
        qdrant_vectors = float(counts["qdrant_points"])

    security_signals = build_security_signals(
        auth_failed_rate=auth_failed_rate,
        forbidden_rate=forbidden_rate,
        not_found_rate=not_found_rate,
        backend_5xx_rate=backend_5xx_rate,
        request_rate=request_rate,
        recent_audit=recent_audit,
    )

    backend_up = prometheus_scalar('max(up{job="unknown-detection-backend"})')

    return {
        "updated_at": utc_now_iso(),
        "prometheus": {"connected": prometheus_ok, "url": PROMETHEUS_URL},
        "summary": {
            "alerts": counts["alerts"],
            "api_requests_per_second": round_float(request_rate),
            "cameras": counts["cameras"],
            "users": counts["users"],
        },
        "services": [
            {"name": "postgres", "status": "ok" if health_data["postgres"] else "error"},
            {"name": "redis", "status": "ok" if health_data.get("redis") else "error"},
            {"name": "backend", "status": "ok" if backend_up is None or backend_up > 0 else "warning"},
            {"name": "qdrant", "status": "ok" if health_data["qdrant"] else "error"},
            {"name": "prometheus", "status": "ok" if prometheus_ok else "error"},
            {"name": "alertmanager", "status": "ok" if prometheus_scalar('up{job="prometheus"}') is not None else "warning"},
            {"name": "worker", "status": "ok" if health_data.get("workers", {}).get("running", 0) > 0 else "warning"},
        ],
        "resources": {
            "cpu_percent": round_float(cpu_usage),
            "ram_percent": round_float(ram_usage),
            "disk_percent": round_float(disk_usage),
            "linux_metrics_enabled": host_metrics_enabled,
            "source": resource_source,
        },
        "throughput": {
            "backend_rps": round_float(request_rate),
            "error_5xx_rps": round_float(backend_5xx_rate),
            "auth_failed_rps": round_float(auth_failed_rate),
        },
        "storage": {
            "qdrant_vectors": round_float(qdrant_vectors),
            "postgres_connections": round_float(postgres_conns),
            "redis_memory_bytes": round_float(redis_memory),
            "employee_vectors": counts["qdrant_points"],
        },
        "security": security_signals,
    }


def check_postgres() -> bool:
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return True
    except Exception:
        return False


def get_system_counts() -> dict:
    counts = {"alerts": 0, "cameras": 0, "users": 0, "qdrant_points": 0}
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM unknown_events WHERE deleted_at IS NULL")
                counts["alerts"] = int(cur.fetchone()[0] or 0)
                cur.execute("SELECT count(*) FROM camera_sources WHERE is_active = true")
                counts["cameras"] = int(cur.fetchone()[0] or 0)
                cur.execute("SELECT count(*) FROM accounts WHERE is_active = true")
                counts["users"] = int(cur.fetchone()[0] or 0)
    except Exception:
        pass
    try:
        with request.urlopen(f"{QDRANT_URL}/collections/employee_faces", timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
            result = data.get("result", {})
            counts["qdrant_points"] = int(result.get("points_count") or result.get("vectors_count") or 0)
    except Exception:
        pass
    return counts


def get_recent_audit_actions() -> list[dict]:
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT actor, action, entity_type, entity_id, created_at
                    FROM audit_logs
                    ORDER BY created_at DESC
                    LIMIT 8
                    """
                )
                return [
                    {
                        "actor": row[0],
                        "action": row[1],
                        "entity_type": row[2],
                        "entity_id": row[3],
                        "created_at": row[4].isoformat() if row[4] else None,
                    }
                    for row in cur.fetchall()
                ]
    except Exception:
        return []


def prometheus_scalar(expr: str) -> float | None:
    data = prometheus_query(expr)
    if not data:
        return None
    result = data.get("data", {}).get("result", [])
    if not result:
        return None
    try:
        return float(result[0]["value"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def prometheus_query(expr: str) -> dict | None:
    try:
        query = urlencode({"query": expr})
        with request.urlopen(f"{PROMETHEUS_URL.rstrip('/')}/api/v1/query?{query}", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if payload.get("status") == "success" else None
    except Exception:
        return None


def get_native_resource_usage() -> dict[str, float | None]:
    return {
        "cpu_percent": get_proc_cpu_percent(),
        "ram_percent": get_proc_ram_percent(),
        "disk_percent": get_disk_percent(),
    }


def get_proc_cpu_percent() -> float | None:
    global _CPU_SAMPLE
    sample = read_proc_cpu_sample()
    if sample is None:
        return None
    previous = _CPU_SAMPLE
    if previous is None:
        time.sleep(0.05)
        second_sample = read_proc_cpu_sample()
        if second_sample is None:
            _CPU_SAMPLE = sample
            return None
        previous = sample
        sample = second_sample
    _CPU_SAMPLE = sample
    previous_idle, previous_total = previous
    idle, total = sample
    total_delta = total - previous_total
    idle_delta = idle - previous_idle
    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))


def read_proc_cpu_sample() -> tuple[float, float] | None:
    try:
        with open("/proc/stat", encoding="utf-8") as file:
            fields = file.readline().split()
        if not fields or fields[0] != "cpu":
            return None
        values = [float(value) for value in fields[1:]]
        if len(values) < 5:
            return None
        idle = values[3] + values[4]
        total = sum(values)
        return idle, total
    except (OSError, ValueError):
        return None


def get_proc_ram_percent() -> float | None:
    try:
        memory: dict[str, float] = {}
        with open("/proc/meminfo", encoding="utf-8") as file:
            for line in file:
                key, raw_value = line.split(":", 1)
                memory[key] = float(raw_value.strip().split()[0])
        total = memory.get("MemTotal")
        available = memory.get("MemAvailable")
        if not total or available is None:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - available / total)))
    except (OSError, ValueError):
        return None


def get_disk_percent() -> float | None:
    try:
        usage = shutil.disk_usage("/")
        if usage.total <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * usage.used / usage.total))
    except OSError:
        return None


def build_security_signals(
    auth_failed_rate: float | None,
    forbidden_rate: float | None,
    not_found_rate: float | None,
    backend_5xx_rate: float | None,
    request_rate: float | None,
    recent_audit: list[dict],
) -> dict:
    auth_failed = auth_failed_rate or 0.0
    forbidden = forbidden_rate or 0.0
    not_found = not_found_rate or 0.0
    errors = backend_5xx_rate or 0.0
    requests = request_rate or 0.0
    ddos_score = min(
        100.0,
        score_component(requests, warning_at=8.0, critical_at=40.0, max_score=40.0)
        + score_component(not_found, warning_at=0.2, critical_at=2.0, max_score=24.0)
        + score_component(forbidden, warning_at=0.1, critical_at=1.0, max_score=20.0)
        + score_component(errors, warning_at=0.05, critical_at=0.5, max_score=16.0)
    )
    signals = [
        signal("failed_login", auth_failed, "warning" if auth_failed > 0.05 else "ok", "Đăng nhập sai tăng bất thường" if auth_failed > 0.05 else "Đăng nhập thất bại trong ngưỡng bình thường"),
        signal("forbidden_access", forbidden, "warning" if forbidden > 0.1 else "ok", "Nhiều request bị chặn quyền" if forbidden > 0.1 else "Không thấy truy cập trái quyền nổi bật"),
        signal("scan_404", not_found, "warning" if not_found > 0.2 else "ok", "Có dấu hiệu quét endpoint/URL lạ" if not_found > 0.2 else "Không thấy quét URL nổi bật"),
        signal("backend_errors", errors, "warning" if errors > 0.05 else "ok", "Backend 5xx tăng" if errors > 0.05 else "Backend lỗi thấp"),
        signal("ddos_pressure", ddos_score, "critical" if ddos_score > 75 else "warning" if ddos_score > 40 else "ok", "Điểm áp lực request/DDoS tổng hợp"),
        signal("vpn_visibility", None, "unknown", "Nginx production gateway đã có, nhưng analytics chưa đọc access log Nginx/VPN nên chưa xác định được VPN thật"),
    ]
    return {
        "risk_level": "critical" if ddos_score > 75 else "warning" if ddos_score > 40 or auth_failed > 0.05 or forbidden > 0.1 else "ok",
        "ddos_score": round_float(ddos_score),
        "signals": signals,
        "recent_audit": recent_audit,
    }


def score_component(value: float, warning_at: float, critical_at: float, max_score: float) -> float:
    if value <= warning_at:
        return 0.0
    if critical_at <= warning_at:
        return max_score
    normalized = min(1.0, (value - warning_at) / (critical_at - warning_at))
    return normalized * max_score


def signal(code: str, value: float | None, status: str, message: str) -> dict:
    return {"code": code, "value": round_float(value), "status": status, "message": message}


def round_float(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def get_worker_summary() -> dict:
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        count(*) FILTER (WHERE status = 'running') AS running,
                        count(*) AS total
                    FROM camera_worker_status
                    WHERE last_seen_at > now() - interval '2 minutes'
                    """
                )
                running, total = cur.fetchone()
                return {"running": running, "total": total}
    except Exception:
        return {"running": 0, "total": 0}


def check_qdrant() -> bool:
    try:
        with request.urlopen(f"{QDRANT_URL}/collections/employee_faces", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False


def check_redis() -> bool:
    try:
        client = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        return bool(client.ping())
    except redis.RedisError:
        return False
