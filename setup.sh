#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$ROOT_DIR"

echo "[setup] Checking required commands..."
command -v docker >/dev/null 2>&1 || { echo "[setup] Docker is required."; exit 1; }
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "[setup] Python is required. Set PYTHON_BIN if needed."; exit 1; }

echo "[setup] Python version:"
"$PYTHON_BIN" --version

echo "[setup] Starting Postgres and Qdrant..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[setup] Installing Python dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install "psycopg[binary]" opencv-python onnxruntime numpy fastapi uvicorn PyJWT httpx python-dotenv

if "$PYTHON_BIN" -m pip install insightface; then
  echo "[setup] insightface installed successfully."
else
  echo "[setup] insightface install failed."
  echo "[setup] On Windows/Python 3.12 this usually needs Microsoft C++ Build Tools."
  echo "[setup] Install Visual C++ Build Tools, then rerun: $PYTHON_BIN -m pip install insightface"
fi

echo "[setup] Importing Postgres export..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/db/import_postgres_export.py"

echo "[setup] Importing Qdrant export..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/db/import_qdrant_export.py"

echo "[setup] Initializing event schema..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/db/init_event_schema.py"

echo "[setup] Verifying databases..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/db/verify_databases.py"

echo "[setup] Checking runtime packages..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/dev/check_runtime.py"

echo "[setup] Done. Use ./start.sh to start services and ./stop.sh to stop them."
