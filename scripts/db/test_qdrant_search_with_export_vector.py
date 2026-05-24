import json
import sys
from pathlib import Path
from urllib import request

import psycopg

ROOT = Path(__file__).resolve().parents[2]
QDRANT_EXPORT_PATH = ROOT / "data" / "exports" / "qdrant_20260521T080719Z.json"
QDRANT_URL = "http://localhost:7002"
POSTGRES_DSN = "host=localhost port=7001 dbname=face_db user=face_user password=face_password"
COLLECTION_NAME = "employee_faces"
TOP_K = 5


def load_first_employee_face_point() -> dict:
    export = json.loads(QDRANT_EXPORT_PATH.read_text(encoding="utf-8"))
    for collection in export["collections"]:
        if collection["name"] == COLLECTION_NAME:
            return collection["points"][0]
    raise ValueError(f"Collection not found: {COLLECTION_NAME}")


def qdrant_search(vector: list[float]) -> list[dict]:
    payload = {
        "vector": vector,
        "limit": TOP_K,
        "with_payload": True,
        "with_vector": False,
    }
    req = request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))["result"]


def get_employee(employee_id: int) -> tuple | None:
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, emp_code, name, department, is_active FROM employees WHERE id = %s",
                (employee_id,),
            )
            return cur.fetchone()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    source_point = load_first_employee_face_point()
    source_payload = source_point["payload"]
    results = qdrant_search(source_point["vector"])

    print("Source point:")
    print("- point_id:", source_point["id"])
    print("- employee_id:", source_payload["employee_id"])
    print("- emp_code:", source_payload["emp_code"])
    print("- name:", source_payload["name"])
    print()

    print(f"Top {TOP_K} Qdrant results:")
    for index, result in enumerate(results, start=1):
        payload = result["payload"]
        print(
            f"{index}. point_id={result['id']} score={result['score']:.6f} "
            f"employee_id={payload.get('employee_id')} emp_code={payload.get('emp_code')} name={payload.get('name')}"
        )

    top_payload = results[0]["payload"]
    employee = get_employee(int(top_payload["employee_id"]))
    print()
    print("Postgres lookup for top-1:")
    print(employee)

    expected_employee_id = int(source_payload["employee_id"])
    actual_employee_id = int(top_payload["employee_id"])
    if actual_employee_id != expected_employee_id:
        raise SystemExit(f"Top-1 mismatch: expected {expected_employee_id}, got {actual_employee_id}")

    print()
    print("OK: Qdrant top-1 matches source vector and Postgres lookup works.")


if __name__ == "__main__":
    main()
