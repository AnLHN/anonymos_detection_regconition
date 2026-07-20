from dataclasses import dataclass
from typing import Any

from data_contract import RecognitionResult
from face_quality import compute_face_quality
from insightface_recognizer import FaceEmbedding, InsightFaceRecognizer
from qdrant_http_service import QdrantHttpService
from recognition_decision import decide_recognition, is_recognition_quality_face, is_trackable_face


@dataclass(frozen=True)
class FacePipelineResult:
    face: FaceEmbedding
    recognition: RecognitionResult
    trackable: bool = True
    recognition_eligible: bool = True
    quality_score: float = 0.0
    pose_score: float = 1.0


class FaceRecognitionPipeline:
    def __init__(self) -> None:
        self.recognizer = InsightFaceRecognizer()
        self.qdrant = QdrantHttpService()
        self.last_stats = {
            "detected_faces": 0,
            "trackable_faces": 0,
            "recognition_eligible_faces": 0,
            "known_faces": 0,
            "unknown_faces": 0,
            "unverified_faces": 0,
            "qdrant_latency_ms": 0.0,
        }

    def process_image(self, image: Any) -> list[FacePipelineResult]:
        results = []
        total_qdrant_latency_ms = 0.0
        qdrant_searches = 0
        trackable_faces = 0
        recognition_eligible_faces = 0
        known_faces = 0
        unknown_faces = 0
        unverified_faces = 0
        faces = self.recognizer.extract_embeddings(image)
        for face in faces:
            trackable = is_trackable_face(face)
            if not trackable:
                continue

            trackable_faces += 1
            quality = compute_face_quality(image, face)
            recognition_eligible = is_recognition_quality_face(face) and quality.passed
            if recognition_eligible:
                recognition_eligible_faces += 1
                candidates, qdrant_latency_ms = self.qdrant.search(face.vector)
                qdrant_searches += 1
                total_qdrant_latency_ms += qdrant_latency_ms
                recognition = decide_recognition(face, candidates)
            else:
                recognition = RecognitionResult(
                    status="unverified",
                    label="Unverified",
                    score=None,
                    employee=None,
                    candidates=[],
                )

            if recognition.status == "known":
                known_faces += 1
            elif recognition.status == "unknown":
                unknown_faces += 1
            else:
                unverified_faces += 1
            results.append(
                FacePipelineResult(
                    face=face,
                    recognition=recognition,
                    trackable=trackable,
                    recognition_eligible=recognition_eligible,
                    quality_score=quality.score,
                    pose_score=quality.pose_score,
                )
            )
        self.last_stats = {
            "detected_faces": len(faces),
            "trackable_faces": trackable_faces,
            "recognition_eligible_faces": recognition_eligible_faces,
            "known_faces": known_faces,
            "unknown_faces": unknown_faces,
            "unverified_faces": unverified_faces,
            "qdrant_latency_ms": total_qdrant_latency_ms / qdrant_searches if qdrant_searches else 0.0,
        }
        return results
