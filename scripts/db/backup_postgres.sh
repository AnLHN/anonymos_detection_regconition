#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker exec unknown-detection-postgres pg_dump -U "${POSTGRES_USER:-face_user}" "${POSTGRES_DATABASE:-face_db}" > "backups/postgres_${stamp}.sql"
