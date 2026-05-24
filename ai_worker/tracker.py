from collections import Counter, deque
from dataclasses import dataclass, field

from face_pipeline import FacePipelineResult


@dataclass
class Track:
    track_id: int
    bbox: tuple[int, int, int, int]
    age: int = 0
    missed: int = 0
    zone: str = "none"
    history: deque[FacePipelineResult] = field(default_factory=lambda: deque(maxlen=30))

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def voted_status(self) -> str:
        statuses = [result.recognition.status for result in self.history]
        if not statuses:
            return "unverified"

        counts = Counter(statuses)
        known_results = [result for result in self.history if result.recognition.status == "known"]
        if len(known_results) >= 3:
            return "known"
        if counts["unknown"] >= 5 and counts["known"] == 0:
            return "unknown"
        if counts["unverified"] >= max(counts["unknown"], counts["known"]):
            return "unverified"
        return counts.most_common(1)[0][0]

    def voted_label(self) -> str:
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


class CentroidTracker:
    def __init__(self, max_distance: float = 80.0, max_missed: int = 10) -> None:
        self.max_distance = max_distance
        self.max_missed = max_missed
        self.next_track_id = 1
        self.tracks: dict[int, Track] = {}

    def update(self, results: list[FacePipelineResult]) -> dict[int, Track]:
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
            track.history.append(result)
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
