#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
PYTHON_BIN="${PYTHON_BIN:-python}"
SETUP_FRONTEND_CHECK="${SETUP_FRONTEND_CHECK:-typecheck}"
NEXT_DIST_DIR="${NEXT_DIST_DIR:-.next-rapi-local}"
export NEXT_DIST_DIR

cd "$ROOT_DIR"

echo "[setup] Checking required commands..."
command -v docker >/dev/null 2>&1 || { echo "[setup] Docker is required."; exit 1; }
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "[setup] Python is required. Set PYTHON_BIN if needed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "[setup] npm is required for the Next.js frontend."; exit 1; }

echo "[setup] Python version:"
"$PYTHON_BIN" --version

echo "[setup] Validating local Docker Compose config..."
docker compose -f "$COMPOSE_FILE" config --quiet

echo "[setup] Starting local infrastructure services..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[setup] Installing Python dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install "psycopg[binary]" opencv-python onnxruntime numpy fastapi uvicorn PyJWT httpx python-dotenv redis prometheus-client

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

echo "[setup] Installing frontend dependencies..."
npm install --prefix "$ROOT_DIR/frontend"

case "$SETUP_FRONTEND_CHECK" in
  build)
    echo "[setup] Checking frontend production build..."
    echo "[setup] Cleaning previous Next.js production output..."
    if ! rm -rf "$ROOT_DIR/frontend/$NEXT_DIST_DIR"; then
      echo "[setup] Could not remove frontend/$NEXT_DIST_DIR."
      echo "[setup] Close any running Next.js dev/build process and rerun setup."
      exit 1
    fi
    NEXT_TELEMETRY_DISABLED=1 npm run build --prefix "$ROOT_DIR/frontend"
    ;;
  typecheck)
    echo "[setup] Checking frontend types..."
    npm run typecheck --prefix "$ROOT_DIR/frontend"
    ;;
  none|skip)
    echo "[setup] Skipping frontend check."
    ;;
  *)
    echo "[setup] Unknown SETUP_FRONTEND_CHECK=$SETUP_FRONTEND_CHECK. Use build, typecheck, or none."
    exit 1
    ;;
esac

echo "[setup] Checking runtime packages..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/dev/check_runtime.py"

echo "[setup] Done. Use ./start.sh to start infra, backend, worker, frontend, Prometheus and Grafana; use ./stop.sh to stop them."
