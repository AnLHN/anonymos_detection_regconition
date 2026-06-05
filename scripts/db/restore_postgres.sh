#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: scripts/db/restore_postgres.sh backups/postgres_YYYYMMDDTHHMMSSZ.sql"
  exit 1
fi

cat "$1" | docker exec -i unknown-detection-postgres psql -U "${POSTGRES_USER:-face_user}" "${POSTGRES_DATABASE:-face_db}"
