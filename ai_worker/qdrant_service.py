import json
import math
from pathlib import Path

from config import QDRANT_COLLECTION, QDRANT_DISTANCE, QDRANT_EXPORT_PATH, QDRANT_VECTOR_SIZE
from data_contract import EmployeePayload, SearchCandidate


class QdrantExportService:
    def __init__(self, export_path: Path = QDRANT_EXPORT_PATH) -> None:
        self.export_path = export_path
        self.collection = self._load_collection()
        self.points = self.collection["points"]

    def _load_collection(self) -> dict:
        data = json.loads(self.export_path.read_text(encoding="utf-8"))
        for collection in data["collections"]:
            if collection["name"] == QDRANT_COLLECTION:
                vectors = collection["info"]["config"]["params"]["vectors"]
                if vectors["size"] != QDRANT_VECTOR_SIZE:
                    raise ValueError(f"Unexpected vector size: {vectors['size']}")
                if vectors["distance"] != QDRANT_DISTANCE:
                    raise ValueError(f"Unexpected distance: {vectors['distance']}")
                return collection
        raise ValueError(f"Collection not found: {QDRANT_COLLECTION}")

    def get_point(self, point_id: int | str) -> dict:
        for point in self.points:
            if str(point["id"]) == str(point_id):
                return point
        raise ValueError(f"Point not found: {point_id}")

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchCandidate]:
        if len(vector) != QDRANT_VECTOR_SIZE:
            raise ValueError(f"Expected vector size {QDRANT_VECTOR_SIZE}, got {len(vector)}")

        scored_points = []
        for point in self.points:
            score = cosine_similarity(vector, point["vector"])
            scored_points.append((score, point))

        scored_points.sort(key=lambda item: item[0], reverse=True)
        candidates = []
        for score, point in scored_points[:top_k]:
            candidates.append(
                SearchCandidate(
                    point_id=point["id"],
                    score=score,
                    payload=EmployeePayload.from_qdrant_payload(point["payload"]),
                )
            )
        return candidates


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
