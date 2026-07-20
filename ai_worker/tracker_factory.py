from typing import Any

from config import TRACKER_TYPE
from tracker import CentroidTracker


def create_tracker(frame_rate: int = 30) -> Any:
    if TRACKER_TYPE == "bytetrack":
        try:
            from bytetrack_tracker import ByteTrackTracker
        except ImportError as error:
            print(f"ByteTrack unavailable, falling back to CentroidTracker: {error}")
            return CentroidTracker()
        return ByteTrackTracker(frame_rate=frame_rate)
    return CentroidTracker()
