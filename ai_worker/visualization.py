import cv2

COLORS = {
    "known": (0, 255, 0),
    "unknown": (0, 0, 255),
    "unverified": (0, 255, 255),
}


def draw_tracks(frame, tracks, scale_x: float = 1.0, scale_y: float = 1.0) -> None:
    for track in tracks.values():
        if not track.history:
            continue
        status = track.voted_status()
        color = COLORS.get(status, (255, 255, 255))
        x1, x2 = int(track.bbox[0] * scale_x), int(track.bbox[2] * scale_x)
        y1, y2 = int(track.bbox[1] * scale_y), int(track.bbox[3] * scale_y)
        score = track.best_score()
        score_text = "" if score is None else f" {score:.3f}"
        zone_text = "" if track.zone == "none" else f" [{track.zone}]"
        label = f"ID {track.track_id}: {track.voted_label()}{score_text}{zone_text}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
