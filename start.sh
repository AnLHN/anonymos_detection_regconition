#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/infra/docker-compose.yml"
PYTHON_BIN="${PYTHON_BIN:-python}"
USE_WINDOWS_PYTHON=0
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  if command -v powershell.exe >/dev/null 2>&1; then
    USE_WINDOWS_PYTHON=1
  elif command -v py >/dev/null 2>&1; then
    PYTHON_BIN="py"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  fi
fi
LAN_MODE="${LAN_MODE:-1}"
if [[ "$LAN_MODE" == "1" || "$LAN_MODE" == "true" ]]; then
  BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
  FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
else
  BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
  FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
fi
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
FRONTEND_READY_TIMEOUT="${FRONTEND_READY_TIMEOUT:-180}"
FRONTEND_PREWARM_PATHS="${FRONTEND_PREWARM_PATHS:-/ /alerts /cameras /rules /employees /users /system /login}"
NEXT_DIST_DIR="${NEXT_DIST_DIR:-.next-rapi-local}"
export NEXT_DIST_DIR
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
ALERTMANAGER_PORT="${ALERTMANAGER_PORT:-9093}"
NODE_EXPORTER_PORT="${NODE_EXPORTER_PORT:-9100}"
CADVISOR_PORT="${CADVISOR_PORT:-8080}"
REDIS_EXPORTER_PORT="${REDIS_EXPORTER_PORT:-9121}"
POSTGRES_EXPORTER_PORT="${POSTGRES_EXPORTER_PORT:-9187}"
GRAFANA_PORT="${GRAFANA_PORT:-3001}"
ENABLE_LINUX_METRICS="${ENABLE_LINUX_METRICS:-0}"
ENABLE_GRAFANA="${ENABLE_GRAFANA:-0}"
profiles=()
if [[ "$ENABLE_LINUX_METRICS" == "1" || "$ENABLE_LINUX_METRICS" == "true" ]]; then
  profiles+=("linux-metrics")
fi
if [[ "$ENABLE_GRAFANA" == "1" || "$ENABLE_GRAFANA" == "true" ]]; then
  profiles+=("grafana")
fi
if [[ "${#profiles[@]}" -gt 0 && -z "${COMPOSE_PROFILES:-}" ]]; then
  export COMPOSE_PROFILES="$(IFS=,; echo "${profiles[*]}")"
fi
LAN_IP="${LAN_IP:-192.168.2.17}"
if [[ "$LAN_MODE" == "1" || "$LAN_MODE" == "true" ]]; then
  if [[ -n "$LAN_IP" && -z "${NEXT_PUBLIC_API_BASE:-}" ]]; then
    export NEXT_PUBLIC_API_BASE="http://$LAN_IP:$FRONTEND_PORT/api"
  fi
  if [[ -n "$LAN_IP" && -z "${NEXT_PUBLIC_GRAFANA_DASHBOARD_URL:-}" ]]; then
    export NEXT_PUBLIC_GRAFANA_DASHBOARD_URL="http://$LAN_IP:$GRAFANA_PORT/d/unknown-detection-monitoring/unknown-detection-monitoring?kiosk"
  fi
elif [[ -z "${NEXT_PUBLIC_GRAFANA_DASHBOARD_URL:-}" ]]; then
  export NEXT_PUBLIC_GRAFANA_DASHBOARD_URL="http://localhost:$GRAFANA_PORT/d/unknown-detection-monitoring/unknown-detection-monitoring?kiosk"
fi
RUNTIME_DIR="$ROOT_DIR/.runtime"

cd "$ROOT_DIR"
mkdir -p "$RUNTIME_DIR"

run_python() {
  if [[ "$USE_WINDOWS_PYTHON" == "1" ]]; then
    local script_path="$1"
    shift || true
    if command -v cygpath >/dev/null 2>&1; then
      script_path="$(cygpath -w "$script_path")"
    fi
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "py -3 \"$script_path\""
  else
    "$PYTHON_BIN" "$@"
  fi
}

echo "[start] Starting local infrastructure services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

echo "[start] Bootstrapping exported databases if needed..."
run_python "$ROOT_DIR/scripts/db/bootstrap_exports_if_missing.py"

echo "[start] Initializing event schema..."
run_python "$ROOT_DIR/scripts/db/init_event_schema.py"

echo "[start] Verifying databases..."
run_python "$ROOT_DIR/scripts/db/verify_databases.py"

start_process() {
  local name="$1"
  local pid_file="$2"
  shift 2
  if [[ -f "$pid_file" ]]; then
    local old_pid
    old_pid="$(cat "$pid_file")"
    if kill -0 "$old_pid" 2>/dev/null; then
      echo "[start] $name already running with PID $old_pid"
      return
    fi
  fi
  echo "[start] Starting $name..."
  "$@" > "$RUNTIME_DIR/$name.log" 2>&1 &
  echo $! > "$pid_file"
}

port_is_open() {
  local port="$1"
  (echo > "/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1
}

http_is_ready() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS --max-time 5 "$url" >/dev/null 2>&1
  elif command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "try { \$response = Invoke-WebRequest -UseBasicParsing -Uri '$url' -TimeoutSec 5; exit ([int](\$response.StatusCode -lt 200 -or \$response.StatusCode -ge 400)) } catch { exit 1 }" >/dev/null 2>&1
  else
    return 1
  fi
}

wait_http_ready() {
  local name="$1"
  local url="$2"
  local pid_file="$3"
  local timeout_seconds="${4:-90}"
  local started_at
  started_at="$(date +%s)"

  while true; do
    if http_is_ready "$url"; then
      echo "[start] $name is serving HTTP at $url"
      return 0
    fi

    if [[ -f "$pid_file" ]]; then
      local pid
      pid="$(cat "$pid_file")"
      if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
        echo "[start] $name process exited before HTTP became ready."
        echo "[start] Last $name log lines:"
        tail -n 80 "$RUNTIME_DIR/$name.log" 2>/dev/null || true
        return 1
      fi
    fi

    local now
    now="$(date +%s)"
    if (( now - started_at >= timeout_seconds )); then
      echo "[start] Timed out waiting for $name at $url after ${timeout_seconds}s."
      echo "[start] Last $name log lines:"
      tail -n 80 "$RUNTIME_DIR/$name.log" 2>/dev/null || true
      return 1
    fi
    sleep 2
  done
}

prewarm_frontend_routes() {
  local base_url="$1"
  local paths="$2"
  if ! command -v curl >/dev/null 2>&1; then
    return 0
  fi
  echo "[start] Prewarming frontend routes..."
  local path
  for path in $paths; do
    curl -fsS --max-time 60 "$base_url$path" >/dev/null 2>&1 || true
  done
}

stop_port_process() {
  local name="$1"
  local port="$2"
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "\$processIds = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach (\$processId in \$processIds) { if (\$processId -and \$processId -ne 0) { Write-Host '[start] Stopping stale $name port $port PID' \$processId; Stop-Process -Id \$processId -Force -ErrorAction SilentlyContinue } }" || true
  elif command -v lsof >/dev/null 2>&1; then
    local pids
    pids="$(lsof -ti tcp:"$port" || true)"
    if [[ -n "$pids" ]]; then
      echo "[start] Stopping stale $name port $port PID(s) $pids..."
      kill $pids 2>/dev/null || true
    fi
  fi
}

if [[ "$USE_WINDOWS_PYTHON" == "1" ]]; then
  if port_is_open "$BACKEND_PORT"; then
    echo "[start] backend already listening on port $BACKEND_PORT"
  else
    start_process "backend" "$RUNTIME_DIR/backend.pid" powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "py -3 -m uvicorn backend.main:app --host $BACKEND_HOST --port $BACKEND_PORT --reload"
  fi
  start_process "alert-consumer" "$RUNTIME_DIR/alert-consumer.pid" powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "py -3 \"$ROOT_DIR/scripts/alerts/run_alert_consumer.py\""
  start_process "worker" "$RUNTIME_DIR/worker.pid" powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "py -3 \"$ROOT_DIR/scripts/cameras/run_worker.py\""
else
  if port_is_open "$BACKEND_PORT"; then
    echo "[start] backend already listening on port $BACKEND_PORT"
  else
    start_process "backend" "$RUNTIME_DIR/backend.pid" "$PYTHON_BIN" -m uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
  fi
  start_process "alert-consumer" "$RUNTIME_DIR/alert-consumer.pid" "$PYTHON_BIN" "$ROOT_DIR/scripts/alerts/run_alert_consumer.py"
  start_process "worker" "$RUNTIME_DIR/worker.pid" "$PYTHON_BIN" "$ROOT_DIR/scripts/cameras/run_worker.py"
fi
if http_is_ready "http://127.0.0.1:$FRONTEND_PORT/"; then
  echo "[start] frontend already serving HTTP on port $FRONTEND_PORT"
else
  if port_is_open "$FRONTEND_PORT"; then
    echo "[start] frontend port $FRONTEND_PORT is occupied but HTTP is not ready; restarting it..."
    stop_port_process "frontend" "$FRONTEND_PORT"
    sleep 2
  fi
  rm -f "$RUNTIME_DIR/frontend.pid"
  start_process "frontend" "$RUNTIME_DIR/frontend.pid" npm run dev --prefix "$ROOT_DIR/frontend" -- --hostname "$FRONTEND_HOST" --port "$FRONTEND_PORT"
  wait_http_ready "frontend" "http://127.0.0.1:$FRONTEND_PORT/" "$RUNTIME_DIR/frontend.pid" "$FRONTEND_READY_TIMEOUT"
fi
prewarm_frontend_routes "http://127.0.0.1:$FRONTEND_PORT" "$FRONTEND_PREWARM_PATHS"

echo "[start] Services are ready:"
echo "[start] - Postgres: localhost:7001"
echo "[start] - Qdrant HTTP: localhost:7002"
echo "[start] - Qdrant gRPC: localhost:7003"
echo "[start] - Redis: localhost:6379"
echo "[start] - RabbitMQ management: http://localhost:15672"
echo "[start] - MediaMTX WebRTC/WHEP: http://localhost:8889"
echo "[start] - Prometheus: http://localhost:$PROMETHEUS_PORT"
echo "[start] - Alertmanager: http://localhost:$ALERTMANAGER_PORT"
if [[ "$ENABLE_LINUX_METRICS" == "1" || "$ENABLE_LINUX_METRICS" == "true" ]]; then
  echo "[start] - node-exporter: http://localhost:$NODE_EXPORTER_PORT/metrics"
  echo "[start] - cAdvisor: http://localhost:$CADVISOR_PORT/metrics"
else
  echo "[start] - Linux host/container exporters disabled. Use ENABLE_LINUX_METRICS=1 on Linux to enable them."
fi
echo "[start] - Redis exporter: http://localhost:$REDIS_EXPORTER_PORT/metrics"
echo "[start] - Postgres exporter: http://localhost:$POSTGRES_EXPORTER_PORT/metrics"
if [[ "$ENABLE_GRAFANA" == "1" || "$ENABLE_GRAFANA" == "true" ]]; then
  echo "[start] - Grafana: http://localhost:$GRAFANA_PORT"
else
  echo "[start] - Grafana disabled. Native System Analytics uses Prometheus directly."
fi
echo "[start] - Backend: http://$BACKEND_HOST:$BACKEND_PORT"
echo "[start] - Frontend: http://$FRONTEND_HOST:$FRONTEND_PORT"
echo "[start] - Monitoring page: http://$FRONTEND_HOST:$FRONTEND_PORT/system/monitoring"
echo "[start] - Alert consumer: background process"
echo "[start] - AI camera worker: background process"
if [[ "$LAN_MODE" == "1" || "$LAN_MODE" == "true" ]]; then
  if [[ -n "$LAN_IP" ]]; then
    echo "[start] LAN mode is enabled. Open the app from another device with: http://$LAN_IP:$FRONTEND_PORT"
    echo "[start] Browser API base: ${NEXT_PUBLIC_API_BASE:-/api}"
  else
    echo "[start] LAN mode is enabled. Open the app from another device with: http://<your-lan-ip>:$FRONTEND_PORT"
    echo "[start] Tip: start with LAN_IP=<your-lan-ip> so the frontend calls the backend over LAN automatically."
  fi
fi
echo "[start] Logs: $RUNTIME_DIR/backend.log, $RUNTIME_DIR/frontend.log, $RUNTIME_DIR/worker.log and $RUNTIME_DIR/alert-consumer.log"
