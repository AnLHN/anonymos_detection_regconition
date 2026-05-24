import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(SYSTEM_DIR))

from insightface_recognizer import InsightFaceRecognizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test InsightFace recognition embedding on one static image.")
    parser.add_argument("image", type=Path, help="Path to input image")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        raise SystemExit(f"Cannot read image: {args.image}")

    recognizer = InsightFaceRecognizer()
    embeddings = recognizer.extract_embeddings(image)

    print("Image:", args.image)
    print("Faces with embeddings:", len(embeddings))
    for index, embedding in enumerate(embeddings, start=1):
        print(f"Face {index}:")
        print("- bbox:", embedding.bbox)
        print("- det_score:", round(embedding.det_score, 6))
        print("- embedding_size:", len(embedding.vector))
        print("- embedding_norm:", round(embedding.norm, 6))
        print("- first_5_values:", [round(value, 6) for value in embedding.vector[:5]])


if __name__ == "__main__":
    main()
