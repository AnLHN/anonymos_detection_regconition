from dataclasses import dataclass
from typing import Any

import cv2
from insightface.app import FaceAnalysis

from config import INSIGHTFACE_DETECTION_MODEL, INSIGHTFACE_DEVICE, MIN_DETECTION_SCORE, MIN_FACE_HEIGHT, MIN_FACE_WIDTH


@dataclass(frozen=True)
class DetectedFace:
    bbox: tuple[int, int, int, int]
    landmarks: Any
    det_score: float
    quality_pass: bool

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]


class InsightFaceDetector:
    def __init__(self) -> None:
        providers = ["CPUExecutionProvider"]
        ctx_id = -1
        if INSIGHTFACE_DEVICE.lower() == "cuda":
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            ctx_id = 0

        self.app = FaceAnalysis(name=INSIGHTFACE_DETECTION_MODEL, providers=providers)
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))

    def detect(self, image) -> list[DetectedFace]:
        faces = []
        for face in self.app.get(image):
            x1, y1, x2, y2 = [int(value) for value in face.bbox]
            det_score = float(face.det_score)
            width = x2 - x1
            height = y2 - y1
            quality_pass = (
                det_score >= MIN_DETECTION_SCORE
                and width >= MIN_FACE_WIDTH
                and height >= MIN_FACE_HEIGHT
            )
            faces.append(
                DetectedFace(
                    bbox=(x1, y1, x2, y2),
                    landmarks=face.kps,
                    det_score=det_score,
                    quality_pass=quality_pass,
                )
            )
        return faces


def draw_faces(image, faces: list[DetectedFace]):
    output = image.copy()
    for face in faces:
        color = (0, 255, 0) if face.quality_pass else (0, 255, 255)
        x1, y1, x2, y2 = face.bbox
        label = f"score={face.det_score:.3f} size={face.width}x{face.height}"
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        cv2.putText(output, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    return output
