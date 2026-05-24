import json
import sys
from urllib import request

import psycopg

POSTGRES_DSN = "host=localhost port=7001 dbname=face_db user=face_user password=face_password"
QDRANT_URL = "http://localhost:7002"


def qdrant_get(path: str) -> dict:
    with request.urlopen(f"{QDRANT_URL}{path}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM employees")
            employees_count = cur.fetchone()[0]
            cur.execute("SELECT id, emp_code, name FROM employees ORDER BY id LIMIT 3")
            employees = cur.fetchall()

    collection = qdrant_get("/collections/employee_faces")
    scroll_req = request.Request(
        f"{QDRANT_URL}/collections/employee_faces/points/scroll",
        data=json.dumps({"limit": 3, "with_payload": True, "with_vector": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(scroll_req, timeout=30) as response:
        points = json.loads(response.read().decode("utf-8"))["result"]["points"]

    print("Postgres employees count:", employees_count)
    print("Postgres sample employees:", employees)
    print("Qdrant employee_faces status:", collection["result"]["status"])
    print("Qdrant employee_faces points_count:", collection["result"]["points_count"])
    print("Qdrant sample payloads:", [point["payload"] for point in points])


if __name__ == "__main__":
    main()
