import argparse
import signal
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AI_WORKER_DIR = ROOT / "ai_worker"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AI_WORKER_DIR))

from camera_source_repository import CameraSourceRepository
from camera_worker import CameraWorker, CameraWorkerConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run headless AI camera worker.")
    parser.add_argument("--camera-id", help="Run one camera_id. If omitted, run all active cameras.")
    return parser.parse_args()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    repo = CameraSourceRepository()
    camera_rows = [repo.get_camera(args.camera_id)] if args.camera_id else repo.get_active_cameras()
    camera_rows = [row for row in camera_rows if row]
    if not camera_rows:
        raise SystemExit("No active camera found")

    workers = [CameraWorker(CameraWorkerConfig.from_camera_row(row)) for row in camera_rows]
    stop_event = threading.Event()

    def stop_workers(*_):
        stop_event.set()
        for worker in workers:
            worker.stop()

    signal.signal(signal.SIGINT, stop_workers)
    signal.signal(signal.SIGTERM, stop_workers)

    threads = [threading.Thread(target=worker.run, daemon=True) for worker in workers]
    for thread in threads:
        thread.start()

    print("Workers running:", ", ".join(worker.config.camera_id for worker in workers))
    while not stop_event.is_set():
        stop_event.wait(1)

    for thread in threads:
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
