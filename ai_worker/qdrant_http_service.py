import json
from urllib import request

from config import QDRANT_COLLECTION, QDRANT_HOST, QDRANT_PORT, TOP_K
from data_contract import EmployeePayload, SearchCandidate


class QdrantHttpService:
    def __init__(self, host: str = QDRANT_HOST, port: int = QDRANT_PORT) -> None:
        self.base_url = f"http://{host}:{port}"

    def search(self, vector: list[float], top_k: int = TOP_K) -> list[SearchCandidate]:
        payload = {
            "vector": vector,
            "limit": top_k,
            "with_payload": True,
            "with_vector": False,
        }
        req = request.Request(
            f"{self.base_url}/collections/{QDRANT_COLLECTION}/points/search",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))["result"]

        return [
            SearchCandidate(
                point_id=item["id"],
                score=float(item["score"]),
                payload=EmployeePayload.from_qdrant_payload(item["payload"]),
            )
            for item in result
        ]
