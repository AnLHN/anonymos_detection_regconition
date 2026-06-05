# Deployment Guide

## Requirements

- Python 3.12+
- Docker + Docker Compose
- Postgres and Qdrant via `infra/docker-compose.yml`
- Visual C++ Build Tools on Windows if `insightface` needs compilation
- `.env` copied from `.env.example`

## Setup

```bash
./setup.sh
```

## Start infrastructure

```bash
./start.sh
```

## Stop infrastructure

```bash
./stop.sh
```

## Run local stack

```bash
./start.sh
```

This starts Postgres, Qdrant, backend, and Next.js frontend.

## Run backend manually

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health check:

```text
GET http://localhost:8000/system/health
```

## Run worker

Run one camera:

```powershell
python scripts/cameras/run_worker.py --camera-id door_67b
```

Run all active cameras:

```powershell
python scripts/cameras/run_worker.py
```

## Run frontend

Run Next.js dev server:

```powershell
npm install --prefix frontend
npm run dev --prefix frontend
```

Open:

```text
http://localhost:3000
```

## Validate production env

Before starting production, validate `.env`:

```bash
python scripts/dev/validate_production_env.py
```

The check fails on missing required settings, default passwords and weak secrets.

## Docker production stack

Build and start full stack:

```bash
./start-production.sh
```

Stop full stack:

```bash
./stop-production.sh
```

Compose file:

```text
infra/docker-compose.production.yml
```

Services:

- `postgres`
- `qdrant`
- `backend`
- `worker`
- `frontend`

All production services use `restart: unless-stopped`.

Frontend port:

```text
http://localhost:8080
```

Container runs Next.js on port `3000`.

## Backup and restore

Backup Postgres:

```bash
scripts/db/backup_postgres.sh
```

Restore Postgres:

```bash
scripts/db/restore_postgres.sh backups/postgres_YYYYMMDDTHHMMSSZ.sql
```

## AI-annotated live camera MJPEG canvas

Backend reads RTSP sources, runs the local recognition pipeline, draws bbox/label overlays, and exposes an authenticated MJPEG endpoint. The frontend calls:

```text
GET /cameras/{camera_id}/mjpeg
```

The browser receives annotated JPEG frames over HTTP and draws them onto a canvas. Raw RTSP URLs and credentials stay server-side.

## Worker health

Worker ghi heartbeat vÃ o `camera_worker_status` theo tá»«ng camera. Backend tráº£ tráº¡ng thÃ¡i qua:

```text
GET /system/health
GET /cameras
```

Dashboard hiá»ƒn thá»‹ worker status, FPS vÃ  AI latency.

## Docker build hygiene

`.dockerignore` excludes local env files, git data, Python cache, exports, runtime storage, backups and benchmark output from container build context.

## Log rotation

`infra/docker-compose.production.yml` uses Docker `json-file` rotation for all services:

```text
max-size: 10m
max-file: 5
```

## Frontend runtime config

Frontend uses Next.js. Browser API base is configured with:

```text
NEXT_PUBLIC_API_BASE
```

Production compose maps this from `.env`:

```text
FRONTEND_API_BASE=http://localhost:8000
```

## Worker container healthcheck

Docker Compose worker service runs:

```text
python scripts/cameras/worker_healthcheck.py
```

The check passes when at least one camera worker heartbeat is `starting` or `running` within the last 2 minutes.

## Production stack preflight

```text
Date: 2026-05-25
Command: python scripts/dev/validate_production_env.py
Result: blocked
Reasons:
- POSTGRES_PASSWORD still uses unsafe default/dev value
- JWT_SECRET still uses unsafe default/dev value

Command: docker compose --env-file .env -f infra/docker-compose.production.yml config --quiet
Result: passed

Running containers observed:
- unknown-detection-postgres: healthy on 7001
- unknown-detection-qdrant: healthy on 7002/7003
- websearch-searxng: using port 8080

Production stack was not started because env validation failed and frontend port 8080 is already in use.
```

## Production gaps

- Replace `.env` production secrets before running `./start-production.sh`.
- Free port 8080 or change frontend published port before production stack test.
- External secret manager integration.
