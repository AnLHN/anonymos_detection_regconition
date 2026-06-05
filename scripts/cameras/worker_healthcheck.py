import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI_WORKER_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AI_WORKER_DIR))

import psycopg

from config import POSTGRES_DSN


def main() -> None:
    with psycopg.connect(POSTGRES_DSN, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM camera_worker_status
                WHERE status IN ('starting', 'running')
                  AND last_seen_at > now() - interval '2 minutes'
                """
            )
            active_count = cur.fetchone()[0]
    if active_count < 1:
        raise SystemExit("No recent active worker heartbeat")


if __name__ == "__main__":
    main()
