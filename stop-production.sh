#!/usr/bin/env bash
set -euo pipefail

docker compose --env-file .env -f infra/docker-compose.production.yml down
