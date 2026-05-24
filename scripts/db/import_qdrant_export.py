import json
from pathlib import Path
from typing import Any
from urllib import request

ROOT = Path(__file__).resolve().parents[2]
EXPORT_PATH = ROOT / "data" / "exports" / "qdrant_20260521T080719Z.json"
QDRANT_URL = "http://localhost:7002"


def http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(f"{QDRANT_URL}{path}", data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except Exception as exc:
        raise RuntimeError(f"Qdrant request failed: {method} {path}: {exc}") from exc


def recreate_collection(collection: dict[str, Any]) -> None:
    name = collection["name"]
    vectors = collection["info"]["config"]["params"]["vectors"]
    http_json("DELETE", f"/collections/{name}")
    http_json(
        "PUT",
        f"/collections/{name}",
        {
            "vectors": {
                "size": vectors["size"],
                "distance": vectors["distance"],
            }
        },
    )


def upsert_points(collection: dict[str, Any]) -> None:
    name = collection["name"]
    points = [
        {
            "id": point["id"],
            "vector": point["vector"],
            "payload": point.get("payload", {}),
        }
        for point in collection.get("points", [])
    ]
    if not points:
        return

    batch_size = 64
    for index in range(0, len(points), batch_size):
        http_json(
            "PUT",
            f"/collections/{name}/points?wait=true",
            {"points": points[index:index + batch_size]},
        )


def main() -> None:
    export = json.loads(EXPORT_PATH.read_text(encoding="utf-8"))
    for collection in export["collections"]:
        recreate_collection(collection)
        upsert_points(collection)
        print(f"Imported Qdrant collection: {collection['name']} ({len(collection.get('points', []))} points)")


if __name__ == "__main__":
    main()
