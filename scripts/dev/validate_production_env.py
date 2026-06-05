import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
DEFAULT_VALUES = {
    "POSTGRES_PASSWORD": {"change-me", "face_password", "password"},
    "JWT_SECRET": {"replace-with-at-least-32-random-characters", "local-dev-secret-change-before-production-123456"},
    "RABBITMQ_DEFAULT_PASS": {"change-me", "face_password", "password"},
    "GRAFANA_ADMIN_PASSWORD": {"change-me", "admin", "password"},
}
REQUIRED_KEYS = [
    "POSTGRES_PASSWORD",
    "JWT_SECRET",
    "POSTGRES_DATABASE",
    "POSTGRES_USER",
    "QDRANT_COLLECTION",
    "RABBITMQ_DEFAULT_USER",
    "RABBITMQ_DEFAULT_PASS",
    "GRAFANA_ADMIN_USER",
    "GRAFANA_ADMIN_PASSWORD",
]


def load_env_file(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_value(values: dict[str, str], key: str) -> str:
    return os.environ.get(key) or values.get(key, "")


def main() -> None:
    values = load_env_file(ENV_PATH)
    errors = []

    for key in REQUIRED_KEYS:
        if not get_value(values, key):
            errors.append(f"Missing required env: {key}")

    for key, blocked_values in DEFAULT_VALUES.items():
        value = get_value(values, key)
        if value in blocked_values:
            errors.append(f"Unsafe default value for {key}")

    jwt_secret = get_value(values, "JWT_SECRET")
    if jwt_secret and len(jwt_secret) < 32:
        errors.append("JWT_SECRET must be at least 32 characters")

    postgres_password = get_value(values, "POSTGRES_PASSWORD")
    if postgres_password and len(postgres_password) < 12:
        errors.append("POSTGRES_PASSWORD should be at least 12 characters")

    rabbitmq_password = get_value(values, "RABBITMQ_DEFAULT_PASS")
    if rabbitmq_password and len(rabbitmq_password) < 12:
        errors.append("RABBITMQ_DEFAULT_PASS should be at least 12 characters")

    grafana_password = get_value(values, "GRAFANA_ADMIN_PASSWORD")
    if grafana_password and len(grafana_password) < 12:
        errors.append("GRAFANA_ADMIN_PASSWORD should be at least 12 characters")

    if errors:
        print("Production environment validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("Production environment validation passed.")


if __name__ == "__main__":
    main()
