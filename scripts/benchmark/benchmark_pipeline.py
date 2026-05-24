import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(SYSTEM_DIR))

from face_pipeline import FaceRecognitionPipeline

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark face recognition pipeline on a folder of images.")
    parser.add_argument("--input", type=Path, required=True, help="Image file or folder containing images")
    parser.add_argument("--output-json", type=Path, default=ROOT / "reports" / "benchmark_results.json")
    parser.add_argument("--output-md", type=Path, default=ROOT / "reports" / "benchmark.md")
    return parser.parse_args()


def collect_images(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    images = []
    for path in input_path.rglob("*"):
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(path)
    return sorted(images)


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = int(round((len(values) - 1) * percent))
    return values[index]


def summarize_latencies(latencies_ms: list[float]) -> dict:
    if not latencies_ms:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
        }
    return {
        "count": len(latencies_ms),
        "avg_ms": statistics.mean(latencies_ms),
        "min_ms": min(latencies_ms),
        "max_ms": max(latencies_ms),
        "p50_ms": percentile(latencies_ms, 0.50),
        "p95_ms": percentile(latencies_ms, 0.95),
    }


def write_markdown(path: Path, result: dict) -> None:
    summary = result["summary"]
    lines = [
        "# Benchmark pipeline",
        "",
        "## Input",
        "",
        f"- Images: {result['image_count']}",
        f"- Faces processed: {result['face_count']}",
        "",
        "## End-to-end latency",
        "",
        f"- Average: {summary['avg_ms']:.2f} ms/image",
        f"- Min: {summary['min_ms']:.2f} ms",
        f"- Max: {summary['max_ms']:.2f} ms",
        f"- P50: {summary['p50_ms']:.2f} ms",
        f"- P95: {summary['p95_ms']:.2f} ms",
        "",
        "## Per-image results",
        "",
        "| Image | Latency ms | Faces | Statuses |",
        "|---|---:|---:|---|",
    ]
    for item in result["items"]:
        statuses = ", ".join(item["statuses"])
        lines.append(f"| {item['image']} | {item['latency_ms']:.2f} | {item['faces']} | {statuses} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    images = collect_images(args.input)
    if not images:
        raise SystemExit(f"No images found: {args.input}")

    pipeline = FaceRecognitionPipeline()
    items = []
    latencies = []
    face_count = 0

    for image_path in images:
        image = cv2.imread(str(image_path))
        if image is None:
            items.append({
                "image": str(image_path),
                "latency_ms": 0.0,
                "faces": 0,
                "statuses": ["read_failed"],
            })
            continue

        start = time.perf_counter()
        results = pipeline.process_image(image)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)
        face_count += len(results)
        items.append({
            "image": str(image_path),
            "latency_ms": latency_ms,
            "faces": len(results),
            "statuses": [result.recognition.status for result in results],
        })

    output = {
        "image_count": len(images),
        "face_count": face_count,
        "summary": summarize_latencies(latencies),
        "items": items,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(args.output_md, output)

    print("Benchmark written:", args.output_json)
    print("Benchmark report:", args.output_md)
    print("Images:", output["image_count"])
    print("Faces:", output["face_count"])
    print("Average latency ms:", round(output["summary"]["avg_ms"], 2))


if __name__ == "__main__":
    main()
