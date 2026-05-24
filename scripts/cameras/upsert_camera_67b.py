import json
import sys

import psycopg

from core.settings import get_str

DSN = get_str("POSTGRES_DSN", "host=localhost port=7001 dbname=face_db user=face_user password=face_password")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    camera_id = get_str("CAMERA_DOOR_67B_ID", "door_67b")
    name = get_str("CAMERA_DOOR_67B_NAME", "Cửa ra vào 67B")
    ip = get_str("CAMERA_DOOR_67B_IP", "")
    rtsp_url = get_str("CAMERA_DOOR_67B_RTSP", "")
    if not rtsp_url:
        raise SystemExit("Missing CAMERA_DOOR_67B_RTSP in .env")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO camera_sources (camera_id, name, source_type, source_url, location, config)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (camera_id) DO UPDATE
                SET name = EXCLUDED.name,
                    source_type = EXCLUDED.source_type,
                    source_url = EXCLUDED.source_url,
                    location = EXCLUDED.location,
                    config = EXCLUDED.config,
                    updated_at = now()
                """,
                (
                    camera_id,
                    name,
                    "rtsp",
                    rtsp_url,
                    "67B",
                    json.dumps({
                        "ip": ip,
                        "model": "Generic Model",
                        "protocol": "Generic RTSP",
                        "http_port": 80,
                        "https_port": 443,
                        "rtsp_port": 554,
                        "username": "admin",
                        "frame_skip": 10,
                        "process_width": 480,
                    }),
                ),
            )
        conn.commit()

    print(f"Upserted camera {camera_id} / {name} / {ip}")


if __name__ == "__main__":
    main()
