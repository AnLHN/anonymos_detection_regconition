import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ai_worker"))

from camera_reader import open_capture
from camera_source_repository import CameraSourceRepository

points: list[tuple[int, int]] = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Click camera/image points to build a zone polygon.")
    parser.add_argument("--camera-id", default="door_67b")
    parser.add_argument("--image", help="Optional image path. If omitted, captures one frame from camera_sources.")
    return parser.parse_args()


def on_mouse(event, x, y, *_):
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append((x, y))
        print(points)


def load_frame(args: argparse.Namespace):
    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            raise SystemExit(f"Cannot read image: {args.image}")
        return frame

    camera = CameraSourceRepository().get_camera(args.camera_id)
    if not camera:
        raise SystemExit(f"Camera not found: {args.camera_id}")

    cap = open_capture(camera["source_url"])
    try:
        ok, frame = cap.read()
        if not ok:
            raise SystemExit(f"Cannot read frame from camera: {args.camera_id}")
        return frame
    finally:
        cap.release()


def main() -> None:
    args = parse_args()
    frame = load_frame(args)
    cv2.namedWindow("draw-zone-points", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("draw-zone-points", on_mouse)

    while True:
        display = frame.copy()
        for index, point in enumerate(points):
            cv2.circle(display, point, 5, (0, 255, 255), -1)
            cv2.putText(display, str(index + 1), (point[0] + 8, point[1] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if len(points) >= 2:
            for left, right in zip(points, points[1:]):
                cv2.line(display, left, right, (0, 255, 255), 2)
        if len(points) >= 3:
            cv2.line(display, points[-1], points[0], (0, 255, 255), 2)
        cv2.imshow("draw-zone-points", display)
        key = cv2.waitKey(20) & 0xFF
        if key in (ord("q"), 27):
            break
        if key == ord("r"):
            points.clear()
        if key == ord("p"):
            print("polygon =", points)

    print("polygon =", points)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
