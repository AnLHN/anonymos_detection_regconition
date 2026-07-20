import math
from dataclasses import dataclass
from typing import Any

from insightface.app import FaceAnalysis

from config import INSIGHTFACE_DET_SIZE, INSIGHTFACE_DEVICE, INSIGHTFACE_RECOGNITION_MODEL, INSIGHTFACE_ROOT, TRACK_DETECTION_SCORE, TRT_ENGINE_DIR
from onnx_providers import insightface_providers


@dataclass(frozen=True)
class FaceEmbedding:
    vector: list[float]
    norm: float
    bbox: tuple[int, int, int, int]
    det_score: float
    landmarks: tuple[tuple[float, float], ...] | None = None


class InsightFaceRecognizer:
    def __init__(self) -> None:
        providers, provider_options, ctx_id = insightface_providers(INSIGHTFACE_DEVICE)
        self.app = FaceAnalysis(
            name=INSIGHTFACE_RECOGNITION_MODEL,
            root=INSIGHTFACE_ROOT,
            allowed_modules=["detection", "recognition"],
            providers=providers,
            provider_options=provider_options,
        )
        self._attach_tensorrt_engines()
        self.app.prepare(
            ctx_id=ctx_id,
            det_size=(INSIGHTFACE_DET_SIZE, INSIGHTFACE_DET_SIZE),
            det_thresh=TRACK_DETECTION_SCORE,
        )

    def extract_embeddings(self, image: Any) -> list[FaceEmbedding]:
        embeddings = []
        for face in self.app.get(image):
            vector = [float(value) for value in face.normed_embedding]
            x1, y1, x2, y2 = [int(value) for value in face.bbox]
            landmarks = normalize_landmarks(getattr(face, "kps", None))
            embeddings.append(
                FaceEmbedding(
                    vector=vector,
                    norm=vector_norm(vector),
                    bbox=(x1, y1, x2, y2),
                    det_score=float(face.det_score),
                    landmarks=landmarks,
                )
            )
        return embeddings

    def _attach_tensorrt_engines(self) -> None:
        if INSIGHTFACE_DEVICE.lower() != "cuda":
            return
        if INSIGHTFACE_DET_SIZE == 640:
            self._replace_session("detection", TRT_ENGINE_DIR / "det_10g_640_trt11.engine")
        self._replace_session("recognition", TRT_ENGINE_DIR / "w600k_r50_b1_trt11.engine")

    def _replace_session(self, task_name: str, engine_path) -> None:
        if not engine_path.exists():
            return
        model = self.app.models.get(task_name)
        if model is None:
            return
        try:
            from tensorrt_session import TensorRTInferenceSession
        except ImportError as error:
            print(f"TensorRT engine skipped for {task_name}: {error}")
            return
        model.session = TensorRTInferenceSession(engine_path)
        print(f"TensorRT engine enabled for {task_name}: {engine_path}")


def vector_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def normalize_landmarks(raw_landmarks: Any) -> tuple[tuple[float, float], ...] | None:
    if raw_landmarks is None:
        return None

    normalized = []
    for point in raw_landmarks:
        if len(point) < 2:
            continue
        normalized.append((float(point[0]), float(point[1])))
    return tuple(normalized) if normalized else None
