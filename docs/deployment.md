# Deployment

Tài liệu này mô tả cách chuẩn bị repo để push GitHub và chạy production-base bằng Docker Compose.

## Mức Độ Hiện Tại

Dự án đang ở mức production-base:

- Có Dockerfile cho backend, frontend và AI worker.
- Có Docker Compose production cho Postgres, Qdrant, Redis, RabbitMQ, MediaMTX, backend, worker, alert-consumer, frontend, Nginx, Prometheus, Alertmanager và Grafana.
- Có script validate production env.
- Có health check và restart policy trong Compose.
- Backend expose `/metrics` cho Prometheus.
- Redis dùng cho worker heartbeat, reload cooldown và latest camera frame/meta.
- RabbitMQ dùng queue `alert_events`; `alert-consumer` ghi alert vào Postgres.
- CI validate Python, frontend và Compose config.

Chưa nên xem là production hoàn chỉnh nếu chưa kiểm thử với camera thật, dataset thật, backup/restore thật, secret thật và quy trình giám sát vận hành thật.

## Chuẩn Bị Trước Khi Push

```bash
git status --short
git diff --stat
```

Không commit:

- `.env`
- Password/token/RTSP thật
- `admin_super_login.md` nếu có credential thật
- `.runtime/`
- `.next*`
- `storage/snapshots/*`
- `storage/logs/*`
- `test-results/`
- Data export thật trong `data/exports/`

Kiểm tra `.env.example` chỉ chứa placeholder an toàn.

## Local Deployment

```bash
./setup.sh
./start.sh
```

Nếu chỉ muốn bật infra:

```bash
docker compose -f infra/docker-compose.yml up -d
```

## Production Compose

Validate `.env` production:

```bash
python scripts/dev/validate_production_env.py
```

Validate Compose:

```bash
docker compose --env-file .env.example -f infra/docker-compose.production.yml config --quiet
```

Start:

```bash
./start-production.sh
```

Stop:

```bash
./stop-production.sh
```

URL mặc định qua production stack:

```text
Admin UI qua Nginx: http://localhost
Backend API:        http://localhost/api
Backend direct:     http://localhost:8000
Prometheus:         http://localhost:9090
Grafana:            http://localhost:3001
RabbitMQ UI:        http://localhost:15672
Qdrant:             http://localhost:7002
Postgres:           localhost:7001
Redis:              localhost:6379
```

Trong LAN, thay `localhost` bằng IP máy chạy server, ví dụ `http://192.168.2.182`.

## Thành Phần Production

| Service | Vai trò |
|---|---|
| Nginx | Reverse proxy frontend/API |
| Backend | FastAPI app |
| Frontend | Next.js standalone build |
| Worker | AI camera worker |
| Alert Consumer | Ghi alert events từ RabbitMQ vào Postgres |
| Postgres | CSDL nghiệp vụ |
| Qdrant | Vector database |
| Redis | State/cooldown/cache |
| RabbitMQ | Event queue |
| MediaMTX | RTSP/WebRTC gateway |
| Prometheus | Metrics scrape |
| Alertmanager | Alert routing |
| Grafana | Monitoring dashboard |

## Biến Môi Trường Quan Trọng

Database:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DATABASE`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DSN`

Auth/backend:

- `JWT_SECRET`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ADMIN_SUPER_PASSWORD`
- `BACKEND_PORT`
- `FRONTEND_API_BASE`
- `NGINX_HTTP_PORT`

Camera/AI:

- `CAMERA_*_RTSP`
- `DEFAULT_AI_INTERVAL`
- `DEFAULT_RECONNECT_DELAY`
- `FACE_THRESHOLD`
- `MIN_DETECTION_SCORE`
- `MIN_FACE_WIDTH`
- `MIN_FACE_HEIGHT`
- `TOP_K`

Runtime:

- `REDIS_PORT`
- `RABBITMQ_DEFAULT_USER`
- `RABBITMQ_DEFAULT_PASS`
- `UNKNOWN_ALERT_COOLDOWN_SECONDS`
- `CAMERA_RELOAD_LOCK_SECONDS`

Observability:

- `PROMETHEUS_PORT`
- `PROMETHEUS_RETENTION`
- `GRAFANA_PORT`
- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`
- `NEXT_PUBLIC_GRAFANA_DASHBOARD_URL`

## Health Check

Backend:

```text
GET /system/health
GET /metrics
```

Production Compose health checks:

- Postgres bằng `pg_isready`.
- Qdrant TCP check.
- Redis bằng `redis-cli ping`.
- RabbitMQ bằng `rabbitmq-diagnostics ping`.
- Backend bằng `/system/health`.
- Worker bằng `scripts/cameras/worker_healthcheck.py`.
- Nginx bằng HTTP check.

## Backup Và Restore

Backup Postgres:

```bash
./scripts/db/backup_postgres.sh
```

Restore Postgres:

```bash
./scripts/db/restore_postgres.sh path/to/backup.sql
```

Nên lưu backup ngoài máy production và kiểm thử restore định kỳ.

## Checklist Trước Production

- `.env` production đã đổi toàn bộ secret placeholder.
- `JWT_SECRET` đủ dài và không dùng lại secret dev.
- Camera RTSP đã test kết nối.
- `docker compose config --quiet` pass.
- Frontend build pass.
- Backend import app pass.
- Có backup Postgres/Qdrant/storage.
- Monitoring target Prometheus đều UP.
- Grafana dashboard load được.
- Alertmanager receiver đã cấu hình nếu cần gửi cảnh báo thật.
