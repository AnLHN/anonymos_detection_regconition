import json
import sys

import psycopg

from core.settings import get_str

DSN = get_str("POSTGRES_DSN", "host=localhost port=7001 dbname=face_db user=face_user password=face_password")


def camera_configs() -> list[dict]:
    return [
        {
            "camera_id": get_str("CAMERA_AI_PM_1_ID", "ai_pm_1"),
            "name": get_str("CAMERA_AI_PM_1_NAME", "Phòng AI-PM-1"),
            "model": "Hikvision DS-2SE4C425MWG(CH01)",
            "ip": get_str("CAMERA_AI_PM_1_IP", ""),
            "rtsp_url": get_str("CAMERA_AI_PM_1_RTSP", ""),
            "channel": "101",
        },
        {
            "camera_id": get_str("CAMERA_AI_PM_2_ID", "ai_pm_2"),
            "name": get_str("CAMERA_AI_PM_2_NAME", "Phòng AI-PM-2"),
            "model": "Hikvision DS-2SE4C425MWG(CH02)",
            "ip": get_str("CAMERA_AI_PM_2_IP", ""),
            "rtsp_url": get_str("CAMERA_AI_PM_2_RTSP", ""),
            "channel": "201",
        },
    ]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            for camera in camera_configs():
                if not camera["rtsp_url"]:
                    raise SystemExit(f"Missing RTSP URL for {camera['camera_id']} in .env")
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
                        camera["camera_id"],
                        camera["name"],
                        "rtsp",
                        camera["rtsp_url"],
                        "AI-PM",
                        json.dumps({
                            "ip": camera["ip"],
                            "model": camera["model"],
                            "protocol": "Hikvision RTSP",
                            "http_port": 80,
                            "https_port": 443,
                            "rtsp_port": 554,
                            "username": "admin",
                            "channel": camera["channel"],
                            "ai_interval": 0.7,
                        }),
                    ),
                )
        conn.commit()
    print("Upserted AI-PM cameras")


if __name__ == "__main__":
    main()
