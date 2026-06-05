from dataclasses import dataclass
from typing import Any

from data_contract import RecognitionResult
from insightface_recognizer import FaceEmbedding, InsightFaceRecognizer
from qdrant_http_service import QdrantHttpService
from recognition_decision import decide_recognition


@dataclass(frozen=True)
class FacePipelineResult:
    face: FaceEmbedding
    recognition: RecognitionResult


class FaceRecognitionPipeline:
    def __init__(self) -> None:
        self.recognizer = InsightFaceRecognizer()
        self.qdrant = QdrantHttpService()
        self.last_stats = {
            "detected_faces": 0,
            "known_faces": 0,
            "unknown_faces": 0,
            "unverified_faces": 0,
            "qdrant_latency_ms": 0.0,
        }

    def process_image(self, image: Any) -> list[FacePipelineResult]:
        results = []
        total_qdrant_latency_ms = 0.0
        known_faces = 0
        unknown_faces = 0
        unverified_faces = 0
        faces = self.recognizer.extract_embeddings(image)
        for face in faces:
            candidates, qdrant_latency_ms = self.qdrant.search(face.vector)
            total_qdrant_latency_ms += qdrant_latency_ms
            recognition = decide_recognition(face, candidates)
            if recognition.status == "known":
                known_faces += 1
            elif recognition.status == "unknown":
                unknown_faces += 1
            else:
                unverified_faces += 1
            results.append(FacePipelineResult(face=face, recognition=recognition))
        self.last_stats = {
            "detected_faces": len(faces),
            "known_faces": known_faces,
            "unknown_faces": unknown_faces,
            "unverified_faces": unverified_faces,
            "qdrant_latency_ms": total_qdrant_latency_ms / len(faces) if faces else 0.0,
        }
        return results
