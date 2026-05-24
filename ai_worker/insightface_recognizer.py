import math
from dataclasses import dataclass
from typing import Any

from insightface.app import FaceAnalysis

from config import INSIGHTFACE_DEVICE, INSIGHTFACE_RECOGNITION_MODEL


@dataclass(frozen=True)
class FaceEmbedding:
    vector: list[float]
    norm: float
    bbox: tuple[int, int, int, int]
    det_score: float


class InsightFaceRecognizer:
    def __init__(self) -> None:
        providers = ["CPUExecutionProvider"]
        ctx_id = -1
        if INSIGHTFACE_DEVICE.lower() == "cuda":
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            ctx_id = 0

        self.app = FaceAnalysis(name=INSIGHTFACE_RECOGNITION_MODEL, providers=providers)
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))

    def extract_embeddings(self, image: Any) -> list[FaceEmbedding]:
        embeddings = []
        for face in self.app.get(image):
            vector = [float(value) for value in face.normed_embedding]
            x1, y1, x2, y2 = [int(value) for value in face.bbox]
            embeddings.append(
                FaceEmbedding(
                    vector=vector,
                    norm=vector_norm(vector),
                    bbox=(x1, y1, x2, y2),
                    det_score=float(face.det_score),
                )
            )
        return embeddings


def vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))
