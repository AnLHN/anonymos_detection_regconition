from core.settings import get_int, get_str

JWT_SECRET = get_str("JWT_SECRET", "change-me-in-production-change-me-now")
JWT_ALGORITHM = get_str("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)

POSTGRES_DSN = get_str("POSTGRES_DSN", "host=localhost port=7001 dbname=face_db user=face_user password=face_password")
QDRANT_URL = get_str("QDRANT_URL", "http://localhost:7002")
