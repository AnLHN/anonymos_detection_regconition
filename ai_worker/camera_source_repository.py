from typing import Any

import psycopg
from psycopg.rows import dict_row

from config import POSTGRES_DSN


class CameraSourceRepository:
    def __init__(self) -> None:
        self.dsn = POSTGRES_DSN

    def get_active_cameras(self) -> list[dict[str, Any]]:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT camera_id, name, source_type, source_url, location, config
                    FROM camera_sources
                    WHERE is_active = true
                      AND source_type = 'rtsp'
                      AND (source_url LIKE 'rtsp://%%' OR source_url LIKE 'rtsps://%%')
                    ORDER BY camera_id
                    """
                )
                return list(cur.fetchall())

    def get_camera(self, camera_id: str) -> dict[str, Any] | None:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT camera_id, name, source_type, source_url, location, config
                    FROM camera_sources
                    WHERE camera_id = %s AND is_active = true
                      AND source_type = 'rtsp'
                      AND (source_url LIKE 'rtsp://%%' OR source_url LIKE 'rtsps://%%')
                    """,
                    (camera_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
