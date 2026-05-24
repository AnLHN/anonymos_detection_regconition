from config import FACE_THRESHOLD, MIN_DETECTION_SCORE, MIN_FACE_HEIGHT, MIN_FACE_WIDTH
from data_contract import RecognitionResult, SearchCandidate
from insightface_recognizer import FaceEmbedding


def decide_recognition(
    face: FaceEmbedding,
    candidates: list[SearchCandidate],
    threshold: float = FACE_THRESHOLD,
) -> RecognitionResult:
    if not is_good_quality_face(face):
        return RecognitionResult(
            status="unverified",
            label="Unverified",
            score=None,
            employee=None,
            candidates=candidates,
        )

    if not candidates:
        return RecognitionResult(
            status="unknown",
            label="Unknown",
            score=None,
            employee=None,
            candidates=candidates,
        )

    best = candidates[0]
    if best.score >= threshold and best.payload.is_active:
        return RecognitionResult(
            status="known",
            label=best.payload.name,
            score=best.score,
            employee=best.payload,
            candidates=candidates,
        )

    return RecognitionResult(
        status="unknown",
        label="Unknown",
        score=best.score,
        employee=None,
        candidates=candidates,
    )


def is_good_quality_face(face: FaceEmbedding) -> bool:
    x1, y1, x2, y2 = face.bbox
    width = x2 - x1
    height = y2 - y1
    return (
        face.det_score >= MIN_DETECTION_SCORE
        and width >= MIN_FACE_WIDTH
        and height >= MIN_FACE_HEIGHT
    )
