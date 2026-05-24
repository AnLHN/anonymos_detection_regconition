import json
from typing import Any

import psycopg

from config import POSTGRES_DSN


class PostgresEventService:
    def __init__(self) -> None:
        self.dsn = POSTGRES_DSN

    def insert_unknown_event(self, event: dict[str, Any]) -> None:
        sql = """
        INSERT INTO unknown_events (
            event_id,
            camera_id,
            track_id,
            zone,
            status,
            label,
            score,
            warning_type,
            warning_level,
            reason,
            bbox,
            best_match,
            snapshot_full,
            snapshot_face
        ) VALUES (
            %(event_id)s,
            %(camera_id)s,
            %(track_id)s,
            %(zone)s,
            %(status)s,
            %(label)s,
            %(score)s,
            %(warning_type)s,
            %(warning_level)s,
            %(reason)s,
            %(bbox)s,
            %(best_match)s,
            %(snapshot_full)s,
            %(snapshot_face)s
        ) ON CONFLICT (event_id) DO NOTHING
        """
        values = {
            **event,
            "bbox": json.dumps(event["bbox"], ensure_ascii=False),
            "best_match": json.dumps(event["best_match"], ensure_ascii=False) if event.get("best_match") else None,
        }
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, values)
            conn.commit()
