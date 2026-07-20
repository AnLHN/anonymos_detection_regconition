from dataclasses import dataclass
import math
from typing import Any

import cv2

from config import FACE_QUALITY_MIN_POSE_SCORE, FACE_QUALITY_MIN_SCORE
from insightface_recognizer import FaceEmbedding


@dataclass(frozen=True)
class FaceQuality:
    score: float
    passed: bool
    blur_score: float = 0.0
    brightness_score: float = 0.0
    size_score: float = 0.0
    pose_score: float = 1.0


def compute_face_quality(frame: Any, face: FaceEmbedding) -> FaceQuality:
    x1, y1, x2, y2 = face.bbox
    width = max(0, x2 - x1)
    height = max(0, y2 - y1)
    size_score = min(1.0, min(width, height) / 100.0)
    det_score = max(0.0, min(1.0, float(face.det_score)))
    pose_score = compute_pose_score(face)

    blur_score = 0.5
    brightness_score = 0.5
    crop = crop_face(frame, face)
    if crop is not None:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        blur_score = max(0.0, min(1.0, cv2.Laplacian(gray, cv2.CV_64F).var() / 120.0))
        brightness = float(gray.mean())
        brightness_score = 1.0 - min(1.0, abs(brightness - 128.0) / 128.0)

    score = (det_score * 0.35) + (size_score * 0.2) + (blur_score * 0.15) + (brightness_score * 0.1) + (pose_score * 0.2)
    score = max(0.0, min(1.0, score))
    return FaceQuality(
        score=score,
        passed=score >= FACE_QUALITY_MIN_SCORE and pose_score >= FACE_QUALITY_MIN_POSE_SCORE,
        blur_score=blur_score,
        brightness_score=brightness_score,
        size_score=size_score,
        pose_score=pose_score,
    )


def crop_face(frame: Any, face: FaceEmbedding):
    if frame is None or not hasattr(frame, "shape"):
        return None
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = face.bbox
    x1 = max(0, min(width, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height, y1))
    y2 = max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


def compute_pose_score(face: FaceEmbedding) -> float:
    landmarks = face.landmarks
    if not landmarks or len(landmarks) < 5:
        return 1.0

    left_eye, right_eye, nose, left_mouth, right_mouth = landmarks[:5]
    eye_distance = point_distance(left_eye, right_eye)
    mouth_distance = point_distance(left_mouth, right_mouth)
    if eye_distance < 1e-6 or mouth_distance < 1e-6:
        return 0.0

    eye_mid = midpoint(left_eye, right_eye)
    mouth_mid = midpoint(left_mouth, right_mouth)

    roll_ratio = abs(left_eye[1] - right_eye[1]) / eye_distance
    yaw_ratio = abs(nose[0] - eye_mid[0]) / max(eye_distance * 0.5, 1e-6)
    mouth_center_ratio = abs(mouth_mid[0] - nose[0]) / max(mouth_distance * 0.5, 1e-6)

    upper_face = max(0.0, nose[1] - eye_mid[1])
    lower_face = max(0.0, mouth_mid[1] - nose[1])
    if upper_face < 1e-6 or lower_face < 1e-6:
        pitch_score = 0.0
    else:
        pitch_ratio = upper_face / (upper_face + lower_face)
        pitch_score = centered_score(pitch_ratio, target=0.42, max_delta=0.22)

    roll_score = descending_score(roll_ratio, limit=0.18)
    yaw_score = descending_score(yaw_ratio, limit=0.55)
    symmetry_score = descending_score(mouth_center_ratio, limit=0.65)

    score = (yaw_score * 0.45) + (pitch_score * 0.3) + (roll_score * 0.15) + (symmetry_score * 0.1)
    return max(0.0, min(1.0, score))


def midpoint(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    return ((first[0] + second[0]) / 2.0, (first[1] + second[1]) / 2.0)


def point_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


def descending_score(value: float, limit: float) -> float:
    if limit <= 0:
        return 0.0
    return max(0.0, 1.0 - min(1.0, value / limit))


def centered_score(value: float, target: float, max_delta: float) -> float:
    if max_delta <= 0:
        return 0.0
    return max(0.0, 1.0 - min(1.0, abs(value - target) / max_delta))
