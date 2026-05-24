#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "$ROOT_DIR"

echo "[start] Starting Postgres and Qdrant..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[start] Verifying databases..."
"$PYTHON_BIN" "$ROOT_DIR/scripts/db/verify_databases.py"

echo "[start] Services are ready:"
echo "[start] - Postgres: localhost:7001"
echo "[start] - Qdrant HTTP: localhost:7002"
echo "[start] - Qdrant gRPC: localhost:7003"
