from core.settings import get_float, get_int, get_str

JWT_SECRET = get_str("JWT_SECRET", "change-me-in-production-change-me-now")
JWT_ALGORITHM = get_str("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)

POSTGRES_DSN = get_str("POSTGRES_DSN", "host=localhost port=7001 dbname=face_db user=face_user password=face_password")
QDRANT_URL = get_str("QDRANT_URL", "http://localhost:7002")
REDIS_URL = get_str("REDIS_URL", "redis://localhost:6379/0")
PROMETHEUS_URL = get_str("PROMETHEUS_URL", "http://localhost:9090")
MJPEG_REDIS_POLL_INTERVAL = get_float("MJPEG_REDIS_POLL_INTERVAL", 0.03)
MJPEG_WAITING_FRAME_INTERVAL = get_float("MJPEG_WAITING_FRAME_INTERVAL", 1.0)
MEDIAMTX_PUBLIC_WEBRTC_BASE_URL = get_str("MEDIAMTX_PUBLIC_WEBRTC_BASE_URL", "http://localhost:8889")
