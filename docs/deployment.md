# Deployment Guide

## Current deployment level

This repository currently provides a production-base local deployment:

- Docker Compose for Postgres/Qdrant.
- Python AI worker.
- FastAPI backend.
- Static frontend skeleton.
- `.env`-based configuration.

## Local deployment

```bash
./setup.sh
./start.sh
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
python scripts/cameras/run_camera_from_env.py door_67b
```

## Required environment variables

Use `.env.example` as the deployment template.

Important groups:

- Database: `POSTGRES_*`
- Qdrant: `QDRANT_*`
- Model: `INSIGHTFACE_*`
- Rules: `WORKING_HOUR_*`, `RESTRICTED_ZONES`, `GATE_ZONES`
- Backend: `JWT_SECRET`
- Cameras: `CAMERA_*_RTSP`

## GitHub deployment notes

Never commit:

- `.env`
- real camera passwords
- exported production JSON
- runtime snapshots/logs

Commit only:

- `.env.example`
- source code
- docs
- CI config

## Future production work

Still needed for full production:

- Dockerfile for backend.
- Dockerfile for AI worker.
- Dockerfile/build for frontend.
- Compose file for backend/frontend/worker.
- Log rotation.
- Backup/restore scripts.
- Worker supervisor.
- Metrics and alerting.
