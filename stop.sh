#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
RUNTIME_DIR="$ROOT_DIR/.runtime"

cd "$ROOT_DIR"

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]]; then
      if command -v powershell.exe >/dev/null 2>&1; then
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "\$processId = [int]'$pid'; \$process = Get-Process -Id \$processId -ErrorAction SilentlyContinue; if (\$process) { Write-Host '[stop] Stopping $name PID' \$processId; Stop-Process -Id \$processId -Force -ErrorAction SilentlyContinue }"
      elif kill -0 "$pid" 2>/dev/null; then
        echo "[stop] Stopping $name PID $pid..."
        kill "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$pid_file"
  fi
}

stop_port() {
  local name="$1"
  local port="$2"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "\$processIds = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach (\$processId in \$processIds) { if (\$processId -and \$processId -ne 0) { Write-Host '[stop] Stopping $name port $port PID' \$processId; Stop-Process -Id \$processId -Force -ErrorAction SilentlyContinue } }"
  elif command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" || true)"
    if [[ -n "$pids" ]]; then
      echo "[stop] Stopping $name port $port PID(s) $pids..."
      kill $pids 2>/dev/null || true
    fi
  fi
}

echo "[stop] Stopping Docker services..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

stop_pid_file "worker" "$RUNTIME_DIR/worker.pid"
stop_pid_file "alert-consumer" "$RUNTIME_DIR/alert-consumer.pid"
stop_pid_file "backend" "$RUNTIME_DIR/backend.pid"
stop_pid_file "frontend" "$RUNTIME_DIR/frontend.pid"
stop_port "backend" "${BACKEND_PORT:-8000}"
stop_port "frontend" "${FRONTEND_PORT:-3000}"

echo "[stop] Done."
