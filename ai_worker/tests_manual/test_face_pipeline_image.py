import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(SYSTEM_DIR))

from face_pipeline import FaceRecognitionPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run static image through InsightFace recognition and Qdrant Known/Unknown decision.")
    parser.add_argument("image", type=Path, help="Path to input image")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit(f"Cannot read image: {args.image}")

    pipeline = FaceRecognitionPipeline()
    results = pipeline.process_image(image)

    print("Image:", args.image)
    print("Faces processed:", len(results))
    for index, result in enumerate(results, start=1):
        face = result.face
        recognition = result.recognition
        print(f"Face {index}:")
        print("- bbox:", face.bbox)
        print("- det_score:", round(face.det_score, 6))
        print("- embedding_size:", len(face.vector))
        print("- embedding_norm:", round(face.norm, 6))
        print("- status:", recognition.status)
        print("- label:", recognition.label)
        print("- score:", None if recognition.score is None else round(recognition.score, 6))
        print("- top_candidates:")
        for candidate_index, candidate in enumerate(recognition.candidates, start=1):
            payload = candidate.payload
            print(
                f"  {candidate_index}. score={candidate.score:.6f} "
                f"employee_id={payload.employee_id} emp_code={payload.emp_code} "
                f"name={payload.name} active={payload.is_active}"
            )


if __name__ == "__main__":
    main()
