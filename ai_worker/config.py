from pathlib import Path

from core.settings import get_float, get_int, get_list, get_str

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

EXPORTS_DIR = PROJECT_ROOT / "data" / "exports"
MANIFEST_EXPORT_PATH = EXPORTS_DIR / "manifest_20260521T080719Z.json"
POSTGRES_EXPORT_PATH = EXPORTS_DIR / "postgres_20260521T080719Z.json"
QDRANT_EXPORT_PATH = EXPORTS_DIR / "qdrant_20260521T080719Z.json"

QDRANT_HOST = get_str("QDRANT_HOST", "localhost")
QDRANT_PORT = get_int("QDRANT_PORT", 7002)
QDRANT_COLLECTION = get_str("QDRANT_COLLECTION", "employee_faces")
QDRANT_VECTOR_SIZE = get_int("QDRANT_VECTOR_SIZE", 512)
QDRANT_DISTANCE = get_str("QDRANT_DISTANCE", "Cosine")

POSTGRES_HOST = get_str("POSTGRES_HOST", "localhost")
POSTGRES_PORT = get_int("POSTGRES_PORT", 7001)
POSTGRES_DATABASE = get_str("POSTGRES_DATABASE", "face_db")
POSTGRES_USER = get_str("POSTGRES_USER", "face_user")
POSTGRES_PASSWORD = get_str("POSTGRES_PASSWORD", "face_password")
POSTGRES_DSN = get_str(
    "POSTGRES_DSN",
    f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DATABASE} user={POSTGRES_USER} password={POSTGRES_PASSWORD}",
)
EMPLOYEES_TABLE = "employees"

INSIGHTFACE_DEVICE = get_str("INSIGHTFACE_DEVICE", "cpu")
INSIGHTFACE_DETECTION_MODEL = get_str("INSIGHTFACE_DETECTION_MODEL", "buffalo_l")
INSIGHTFACE_RECOGNITION_MODEL = get_str("INSIGHTFACE_RECOGNITION_MODEL", "buffalo_l")

FACE_THRESHOLD = get_float("FACE_THRESHOLD", 0.60)
MIN_DETECTION_SCORE = get_float("MIN_DETECTION_SCORE", 0.75)
MIN_FACE_WIDTH = get_int("MIN_FACE_WIDTH", 60)
MIN_FACE_HEIGHT = get_int("MIN_FACE_HEIGHT", 60)
TOP_K = get_int("TOP_K", 5)

UNKNOWN_STABLE_FRAMES = get_int("UNKNOWN_STABLE_FRAMES", 5)
UNKNOWN_ALERT_COOLDOWN_SECONDS = get_int("UNKNOWN_ALERT_COOLDOWN_SECONDS", 30)
STORAGE_DIR = PROJECT_ROOT / "storage"
SNAPSHOT_DIR = STORAGE_DIR / "snapshots"
EVENT_LOG_PATH = STORAGE_DIR / "logs" / "events.jsonl"

CAMERA_ZONES = {
    "webcam_0": {
        "gate": [(40, 80), (440, 80), (440, 420), (40, 420)],
    },
    "door_67b": {
        "gate": [(40, 80), (440, 80), (440, 420), (40, 420)],
    },
    "ai_pm_1": {},
    "ai_pm_2": {},
}

WORKING_HOUR_START = get_str("WORKING_HOUR_START", "08:00")
WORKING_HOUR_END = get_str("WORKING_HOUR_END", "17:30")
RESTRICTED_ZONES = get_list("RESTRICTED_ZONES", ["restricted_area", "server_room", "warehouse"])
GATE_ZONES = get_list("GATE_ZONES", ["gate"])
UNKNOWN_GATE_WARNING_FRAMES = get_int("UNKNOWN_GATE_WARNING_FRAMES", 8)
