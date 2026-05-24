import json
from urllib import request

import psycopg
from fastapi import APIRouter

from backend.config import POSTGRES_DSN, QDRANT_URL

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
def health() -> dict:
    postgres_ok = check_postgres()
    qdrant_ok = check_qdrant()
    return {
        "status": "ok" if postgres_ok and qdrant_ok else "degraded",
        "postgres": postgres_ok,
        "qdrant": qdrant_ok,
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


def check_qdrant() -> bool:
    try:
        with request.urlopen(f"{QDRANT_URL}/collections/employee_faces", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False
