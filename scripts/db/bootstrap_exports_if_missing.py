import json
from urllib import error, request

import psycopg

import import_postgres_export
import import_qdrant_export

POSTGRES_DSN = "host=localhost port=7001 dbname=face_db user=face_user password=face_password"
QDRANT_URL = "http://localhost:7002"


def postgres_employee_count() -> int | None:
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.employees')")
            if cur.fetchone()[0] is None:
                return None

            cur.execute("SELECT COUNT(*) FROM employees")
            return cur.fetchone()[0]


def qdrant_employee_faces_count() -> int | None:
    try:
        with request.urlopen(f"{QDRANT_URL}/collections/employee_faces", timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    return data["result"].get("points_count", 0)


def main() -> None:
    employees_count = postgres_employee_count()
    if employees_count:
        print(f"Postgres employees already present: {employees_count}")
    else:
        print("Postgres employees missing; importing bundled export...")
        import_postgres_export.main()

    points_count = qdrant_employee_faces_count()
    if points_count:
        print(f"Qdrant employee_faces already present: {points_count}")
    else:
        print("Qdrant employee_faces missing; importing bundled export...")
        import_qdrant_export.main()


if __name__ == "__main__":
    main()
