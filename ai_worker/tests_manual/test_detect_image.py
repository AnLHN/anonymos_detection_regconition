import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(SYSTEM_DIR))

from insightface_detector import InsightFaceDetector, draw_faces


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test InsightFace detection on one static image.")
    parser.add_argument("image", type=Path, help="Path to input image")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "storage" / "debug_faces" / "detect_debug.jpg",
        help="Path to output debug image",
    )
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit(f"Cannot read image: {args.image}")

    detector = InsightFaceDetector()
    faces = detector.detect(image)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    debug_image = draw_faces(image, faces)
    cv2.imwrite(str(args.output), debug_image)

    print("Image:", args.image)
    print("Debug output:", args.output)
    print("Faces detected:", len(faces))
    for index, face in enumerate(faces, start=1):
        print(f"Face {index}:")
        print("- bbox:", face.bbox)
        print("- det_score:", round(face.det_score, 6))
        print("- size:", f"{face.width}x{face.height}")
        print("- quality_pass:", face.quality_pass)


if __name__ == "__main__":
    main()
