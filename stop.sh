#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
PORTS=(7001 7002 7003)

cd "$ROOT_DIR"

echo "[stop] Stopping Docker services..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

kill_port_windows() {
  local port="$1"
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "\
    \$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue; \
    if (\$connections) { \
      \$connections | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { \
        if (\$_ -and \$_ -ne 0) { \
          Write-Host '[stop] Killing process on port $port:' \$_; \
          Stop-Process -Id \$_ -Force -ErrorAction SilentlyContinue; \
        } \
      } \
    }"
}

kill_port_unix() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" || true)"
    if [[ -n "$pids" ]]; then
      echo "[stop] Killing processes on port $port: $pids"
      kill -TERM $pids 2>/dev/null || true
      sleep 1
      kill -KILL $pids 2>/dev/null || true
    fi
  fi
}

for port in "${PORTS[@]}"; do
  echo "[stop] Releasing port $port if needed..."
  if command -v powershell.exe >/dev/null 2>&1; then
    kill_port_windows "$port"
  else
    kill_port_unix "$port"
  fi
done

echo "[stop] Done."
