#!/usr/bin/env bash
set -euo pipefail

python scripts/dev/validate_production_env.py
docker compose --env-file .env -f infra/docker-compose.production.yml up -d --build

echo "[production] Services are starting:"
echo "[production] - Admin UI via nginx: http://localhost:${NGINX_HTTP_PORT:-80}"
echo "[production] - Backend direct: http://localhost:${BACKEND_PORT:-8000}"
echo "[production] - Prometheus: http://localhost:${PROMETHEUS_PORT:-9090}"
echo "[production] - Grafana: http://localhost:${GRAFANA_PORT:-3001}"
echo "[production] - RabbitMQ management: http://localhost:${RABBITMQ_MANAGEMENT_PORT:-15672}"
