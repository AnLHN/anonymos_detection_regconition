import redis
import psycopg

from config import POSTGRES_DSN
from redis_state import RedisStateService


class MetricsService:
    def __init__(self) -> None:
        self.dsn = POSTGRES_DSN
        self.redis_state = RedisStateService()

    def write_metric(self, camera_id: str, metric_name: str, metric_value: float, unit: str = "") -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO system_metrics (camera_id, metric_name, metric_value, unit)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (camera_id, metric_name, metric_value, unit),
                )
            conn.commit()

    def update_camera_status(
        self,
        camera_id: str,
        status: str,
        read_fps: float = 0.0,
        camera_fps: float = 0.0,
        ai_latency_ms: float = 0.0,
        last_error: str | None = None,
    ) -> None:
        try:
            self.redis_state.set_camera_status(camera_id, status, read_fps, camera_fps, ai_latency_ms, last_error)
        except redis.RedisError:
            pass

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO camera_worker_status (
                        camera_id, status, read_fps, camera_fps, ai_latency_ms, last_error, last_seen_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, now(), now())
                    ON CONFLICT (camera_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        read_fps = EXCLUDED.read_fps,
                        camera_fps = EXCLUDED.camera_fps,
                        ai_latency_ms = EXCLUDED.ai_latency_ms,
                        last_error = EXCLUDED.last_error,
                        last_seen_at = now(),
                        updated_at = now()
                    """,
                    (camera_id, status, read_fps, camera_fps, ai_latency_ms, last_error),
                )
            conn.commit()
