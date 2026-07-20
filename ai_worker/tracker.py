from collections import Counter, deque
from dataclasses import dataclass, field
import time

from config import KNOWN_MIN_VOTES, KNOWN_STABLE_FRAMES, RECOGNITION_VOTE_WINDOW, UNKNOWN_STABLE_FRAMES
from face_pipeline import FacePipelineResult
from insightface_recognizer import FaceEmbedding


@dataclass
class Track:
    track_id: int
    bbox: tuple[int, int, int, int]
    age: int = 0
    missed: int = 0
    zone: str = "none"
    history: deque[FacePipelineResult] = field(default_factory=lambda: deque(maxlen=30))
    identity_votes: deque[tuple[str, str, float | None]] = field(default_factory=lambda: deque(maxlen=RECOGNITION_VOTE_WINDOW))
    identity_status: str = "tracking"
    identity_label: str | None = None
    identity_score: float | None = None
    identity_confidence: float = 0.0
    unknown_first_seen_at: float | None = None
    unknown_alert_sent: bool = False
    unknown_alert_event_id: str | None = None
    pending_resolved_unknown_event_id: str | None = None
    pending_resolved_known_label: str | None = None
    pending_resolved_known_score: float | None = None
    best_face: FaceEmbedding | None = None
    best_embedding: list[float] | None = None
    best_quality: float = 0.0
    best_face_updated_at: float = 0.0
    last_seen_at: float = 0.0
    last_recognition_at: float = 0.0

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def apply_pipeline_result(self, result: FacePipelineResult, now: float | None = None) -> None:
        now = now or time.time()
        self.history.append(result)
        self.last_seen_at = now
        self.update_best_face(result, now)

        recognition = result.recognition
        if recognition.status == "known":
            self.last_recognition_at = now
            self.record_identity_vote(recognition.status, recognition.label, recognition.score)
            self.apply_identity_votes()
            return

        if self.identity_status == "known":
            return

        if not result.recognition_eligible or recognition.status == "unverified":
            self.identity_status = "unverified"
            self.identity_label = "Unverified"
            self.identity_score = None
            self.identity_confidence = 0.0
            self.unknown_first_seen_at = None
            return

        if recognition.status == "unknown":
            self.last_recognition_at = now
            self.record_identity_vote(recognition.status, recognition.label, recognition.score)
            if self.identity_status != "unknown":
                self.unknown_first_seen_at = now
                if self.unknown_alert_event_id is None:
                    self.unknown_alert_sent = False
            self.identity_status = "unknown"
            self.identity_label = "Unknown"
            self.identity_score = recognition.score
            self.identity_confidence = 0.0

    def is_known(self) -> bool:
        return self.identity_status == "known"

    def is_unknown_candidate(self) -> bool:
        return self.identity_status == "unknown"

    def is_unknown_stable(self, now: float | None = None, stable_seconds: float = 0.0) -> bool:
        if not self.is_unknown_candidate() or self.unknown_first_seen_at is None:
            return False
        now = now or time.time()
        return now - self.unknown_first_seen_at >= stable_seconds

    def mark_unknown_alert_sent(self, event_id: str) -> None:
        self.unknown_alert_sent = True
        self.unknown_alert_event_id = event_id

    def resolve_as_known(self, label: str, score: float | None) -> None:
        if self.unknown_alert_event_id:
            self.pending_resolved_unknown_event_id = self.unknown_alert_event_id
            self.pending_resolved_known_label = label
            self.pending_resolved_known_score = score
        self.identity_status = "known"
        self.identity_label = label
        self.identity_score = score
        self.identity_confidence = 1.0 if score is None else max(0.0, min(1.0, score))

    def consume_pending_unknown_resolution(self) -> tuple[str, str, float | None] | None:
        if not self.pending_resolved_unknown_event_id or not self.pending_resolved_known_label:
            return None
        payload = (
            self.pending_resolved_unknown_event_id,
            self.pending_resolved_known_label,
            self.pending_resolved_known_score,
        )
        self.pending_resolved_unknown_event_id = None
        self.pending_resolved_known_label = None
        self.pending_resolved_known_score = None
        return payload

    def restore_pending_unknown_resolution(self, event_id: str, label: str, score: float | None) -> None:
        self.pending_resolved_unknown_event_id = event_id
        self.pending_resolved_known_label = label
        self.pending_resolved_known_score = score

    def record_identity_vote(self, status: str, label: str, score: float | None) -> None:
        self.identity_votes.append((status, label, score))

    def apply_identity_votes(self) -> None:
        known_votes = [(label, score) for status, label, score in self.identity_votes if status == "known"]
        if not known_votes:
            return
        label_counts = Counter(label for label, _score in known_votes)
        label, votes = label_counts.most_common(1)[0]
        if votes < KNOWN_MIN_VOTES:
            return
        scores = [score for known_label, score in known_votes if known_label == label and score is not None]
        self.resolve_as_known(label, max(scores) if scores else None)

    def update_best_face(self, result: FacePipelineResult, now: float) -> None:
        if not result.recognition_eligible:
            return
        if result.quality_score <= self.best_quality:
            return
        self.best_face = result.face
        self.best_embedding = list(result.face.vector)
        self.best_quality = result.quality_score
        self.best_face_updated_at = now

    def voted_status(self) -> str:
        if self.identity_status == "known":
            return "known"
        if self.identity_status == "unverified":
            return "unverified"
        statuses = [result.recognition.status for result in self.history]
        if not statuses:
            return "unverified"

        counts = Counter(statuses)
        known_results = [result for result in self.history if result.recognition.status == "known"]
        if len(known_results) >= max(KNOWN_STABLE_FRAMES, KNOWN_MIN_VOTES):
            return "known"
        if counts["unknown"] >= UNKNOWN_STABLE_FRAMES and counts["known"] == 0:
            return "unknown"
        if counts["unverified"] >= max(counts["unknown"], counts["known"]):
            return "unverified"
        return counts.most_common(1)[0][0]

    def voted_label(self) -> str:
        if self.identity_status == "known" and self.identity_label:
            return self.identity_label
        known_labels = [result.recognition.label for result in self.history if result.recognition.status == "known"]
        if known_labels:
            return Counter(known_labels).most_common(1)[0][0]
        status = self.voted_status()
        if status == "unknown":
            return "Unknown"
        return "Unverified"

    def best_score(self) -> float | None:
        scores = [result.recognition.score for result in self.history if result.recognition.score is not None]
        return max(scores) if scores else None

    def latest_face_quality_text(self) -> str:
        if not self.history:
            return ""
        result = self.history[-1]
        face = result.face
        x1, y1, x2, y2 = face.bbox
        return f" det={face.det_score:.2f} size={x2 - x1}x{y2 - y1} pose={result.pose_score:.2f}"


class CentroidTracker:
    def __init__(self, max_distance: float = 80.0, max_missed: int = 10) -> None:
        self.max_distance = max_distance
        self.max_missed = max_missed
        self.next_track_id = 1
        self.tracks: dict[int, Track] = {}

    def update(self, results: list[FacePipelineResult], now: float | None = None) -> dict[int, Track]:
        now = now or time.time()
        unmatched_track_ids = set(self.tracks.keys())
        assignments: dict[int, Track] = {}

        for result in results:
            bbox = result.face.bbox
            center = bbox_center(bbox)
            track_id = self._nearest_track(center, unmatched_track_ids)
            if track_id is None:
                track = self._create_track(bbox)
            else:
                track = self.tracks[track_id]
                unmatched_track_ids.remove(track_id)
                track.bbox = bbox
                track.missed = 0

            track.age += 1
            track.apply_pipeline_result(result, now)
            assignments[id(result)] = track

        for track_id in list(unmatched_track_ids):
            track = self.tracks[track_id]
            track.missed += 1
            if track.missed > self.max_missed:
                del self.tracks[track_id]

        return assignments

    def _nearest_track(self, center: tuple[float, float], candidate_track_ids: set[int]) -> int | None:
        best_track_id = None
        best_distance = self.max_distance
        for track_id in candidate_track_ids:
            distance = euclidean_distance(center, self.tracks[track_id].center)
            if distance < best_distance:
                best_distance = distance
                best_track_id = track_id
        return best_track_id

    def _create_track(self, bbox: tuple[int, int, int, int]) -> Track:
        track = Track(track_id=self.next_track_id, bbox=bbox)
        self.tracks[track.track_id] = track
        self.next_track_id += 1
        return track


def bbox_center(bbox: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def euclidean_distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return ((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2) ** 0.5
