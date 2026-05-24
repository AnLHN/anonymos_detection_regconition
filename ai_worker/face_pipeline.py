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

    def process_image(self, image: Any) -> list[FacePipelineResult]:
        results = []
        for face in self.recognizer.extract_embeddings(image):
            candidates = self.qdrant.search(face.vector)
            recognition = decide_recognition(face, candidates)
            results.append(FacePipelineResult(face=face, recognition=recognition))
        return results
