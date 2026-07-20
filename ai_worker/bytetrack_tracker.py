import time
from typing import Any

import numpy as np
import supervision as sv

from config import (
    BYTETRACK_ACTIVATION_THRESHOLD,
    BYTETRACK_LOST_TRACK_BUFFER,
    BYTETRACK_MATCHING_THRESHOLD,
    BYTETRACK_MIN_CONSECUTIVE_FRAMES,
    TRACK_STATE_TTL_SECONDS,
)
from face_pipeline import FacePipelineResult
from tracker import Track


class ByteTrackTracker:
    def __init__(
        self,
        frame_rate: int = 30,
        track_activation_threshold: float = BYTETRACK_ACTIVATION_THRESHOLD,
        lost_track_buffer: int = BYTETRACK_LOST_TRACK_BUFFER,
        minimum_matching_threshold: float = BYTETRACK_MATCHING_THRESHOLD,
        minimum_consecutive_frames: int = BYTETRACK_MIN_CONSECUTIVE_FRAMES,
        track_state_ttl_seconds: float = TRACK_STATE_TTL_SECONDS,
    ) -> None:
        self.tracker = sv.ByteTrack(
            track_activation_threshold=track_activation_threshold,
            lost_track_buffer=lost_track_buffer,
            minimum_matching_threshold=minimum_matching_threshold,
            frame_rate=frame_rate,
            minimum_consecutive_frames=minimum_consecutive_frames,
        )
        self.track_state_ttl_seconds = track_state_ttl_seconds
        self.track_states: dict[int, Track] = {}
        self.tracks: dict[int, Track] = {}

    def update(self, results: list[FacePipelineResult], now: float | None = None) -> dict[int, Track]:
        now = now or time.time()
        if not results:
            self.tracker.update_with_detections(empty_detections())
            self.tracks = {}
            self._cleanup_stale_states(now)
            return {}

        detections = sv.Detections(
            xyxy=np.array([result.face.bbox for result in results], dtype=float),
            confidence=np.array([result.face.det_score for result in results], dtype=float),
            class_id=np.zeros(len(results), dtype=int),
            data={"result_index": np.arange(len(results), dtype=int)},
        )
        tracked_detections = self.tracker.update_with_detections(detections)

        active_tracks: dict[int, Track] = {}
        assignments: dict[int, Track] = {}
        tracker_ids = tracked_detections.tracker_id
        if tracker_ids is None:
            self.tracks = {}
            self._cleanup_stale_states(now)
            return assignments

        result_indices = tracked_detections.data.get("result_index")
        for detection_index, raw_track_id in enumerate(tracker_ids):
            if raw_track_id is None:
                continue
            track_id = int(raw_track_id)
            result_index = int(result_indices[detection_index]) if result_indices is not None else detection_index
            if result_index < 0 or result_index >= len(results):
                continue
            result = results[result_index]
            bbox = tuple(int(value) for value in tracked_detections.xyxy[detection_index])
            track = self.track_states.get(track_id)
            if track is None:
                track = Track(track_id=track_id, bbox=bbox)
                self.track_states[track_id] = track
            track.bbox = bbox
            track.missed = 0
            track.age += 1
            track.apply_pipeline_result(result, now)
            active_tracks[track_id] = track
            assignments[id(result)] = track

        inactive_track_ids = set(self.track_states) - set(active_tracks)
        for track_id in inactive_track_ids:
            self.track_states[track_id].missed += 1

        self.tracks = active_tracks
        self._cleanup_stale_states(now)
        return assignments

    def _cleanup_stale_states(self, now: float) -> None:
        if self.track_state_ttl_seconds <= 0:
            return
        for track_id, track in list(self.track_states.items()):
            if track_id in self.tracks:
                continue
            if track.last_seen_at and now - track.last_seen_at > self.track_state_ttl_seconds:
                del self.track_states[track_id]


def empty_detections() -> sv.Detections:
    return sv.Detections(
        xyxy=np.empty((0, 4), dtype=float),
        confidence=np.empty((0,), dtype=float),
        class_id=np.empty((0,), dtype=int),
        data={"result_index": np.empty((0,), dtype=int)},
    )
