# Architecture

Tài liệu này mô tả kiến trúc hiện tại của hệ thống phát hiện và nhận diện người lạ.

## Tổng Quan

```text
Camera RTSP / video source
  -> MediaMTX
  -> AI camera worker
  -> InsightFace detection + recognition
  -> Qdrant vector search
  -> Recognition decision: known / unknown / unverified
  -> Tracking + voting
  -> Zone manager + rule engine
  -> Alert manager
  -> RabbitMQ alert_events / Postgres unknown_events / snapshots
  -> FastAPI backend
  -> Next.js admin frontend
```

## Thành Phần

### Backend API

Thư mục: `backend/`

Nhiệm vụ:

- JWT login/logout và `/auth/me`.
- RBAC theo role/permission.
- Quản lý alerts, cameras, rules, employees, users.
- Stream/snapshot/static file serving.
- System health, analytics, metrics.
- Camera reload guard và runtime status.

Module chính:

```text
backend/auth/
backend/users/
backend/alerts/
backend/cameras/
backend/employees/
backend/rules/
backend/system/
backend/database/
backend/main.py
```

### Frontend Admin

Thư mục: `frontend/`

Stack:

- Next.js App Router.
- React 18.
- TypeScript.
- API client qua `frontend/src/lib/api.ts`.
- API base normalize qua `frontend/src/lib/config.ts`.

Nhiệm vụ:

- Login/logout.
- Dashboard metrics.
- Live camera monitor.
- Alert review, delete/restore/repair.
- Camera CRUD/reload.
- Rule CRUD/update.
- Employee search/enroll.
- User CRUD và role update.
- System monitoring/Grafana embed.

### AI Worker

Thư mục: `ai_worker/`

Nhiệm vụ:

- Đọc frame từ RTSP/camera source.
- Chạy InsightFace detect và extract embedding.
- Search Qdrant collection `employee_faces`.
- Phân loại `known`, `unknown`, `unverified`.
- Tracking/voting nhiều frame để giảm nhiễu.
- Kiểm tra zone/ROI và alert rules.
- Lưu snapshot.
- Publish alert event qua RabbitMQ.
- Publish latest frame/meta qua Redis.
- Ghi heartbeat/metrics.

### Data Stores

Postgres:

```text
accounts
employees
camera_sources
alert_rules
unknown_events
system_metrics
audit_logs
```

Qdrant:

```text
collection: employee_faces
vector size: 512
distance: Cosine
payload: employee_id, emp_code, name, department, is_active
```

Redis:

```text
camera:{camera_id}:latest_raw_jpeg
camera:{camera_id}:latest_annotated_jpeg
camera:{camera_id}:latest_meta
camera reload lock/cooldown keys
worker heartbeat keys
```

RabbitMQ:

```text
queue: alert_events
```

Storage:

```text
storage/snapshots/
storage/logs/
storage/debug_faces/
```

## Luồng Camera Thống Nhất

Live camera và cảnh báo dùng chung nguồn xử lý chính là `ai_worker`:

```text
Camera RTSP
  -> ai_worker đọc frame
  -> InsightFace + tracking + rule engine
  -> Alert manager ghi event/snapshot khi cần
  -> ai_worker vẽ annotated frame và encode JPEG
  -> Redis latest frame keys
  -> Backend đọc Redis
  -> Frontend hiển thị live monitor/enrollment frame
```

Backend không tự mở RTSP hoặc chạy model AI cho live stream. Nếu worker chưa publish frame, backend trả trạng thái chờ frame.

## Luồng Nhận Diện

```text
Frame
  -> detect face
  -> filter by detection score and face size
  -> extract normed embedding
  -> search top-k in Qdrant
  -> compare best score with FACE_THRESHOLD
  -> build recognition result
```

Quy tắc:

```text
Quality fail              -> unverified
Best score >= threshold   -> known
Best score < threshold    -> unknown
```

## Luồng Cảnh Báo

Unknown không tạo cảnh báo ngay trên một frame đơn. Kết quả đi qua:

- Tracking theo `track_id`.
- Voting nhiều frame.
- Cooldown chống spam.
- Zone/ROI.
- Rule engine từ `alert_rules`.

Khi rule thỏa điều kiện, `AlertManager`:

1. Lưu full frame snapshot.
2. Lưu face crop nếu có.
3. Publish RabbitMQ event.
4. Alert consumer ghi Postgres.
5. Ghi JSONL fallback nếu queue/DB lỗi.

## Auth Và RBAC

Role:

```text
0 viewer
1 operator
5 admin
9 admin_super
```

Permission được khai báo trong `backend/auth/security.py`. Backend dùng dependency `require_permission(...)` để bảo vệ route. Frontend dùng permission từ `/auth/me` để ẩn/hiện chức năng.

## Deployment View

Production Compose gồm:

- `postgres`
- `qdrant`
- `redis`
- `rabbitmq`
- `mediamtx`
- `backend`
- `worker`
- `alert-consumer`
- `frontend`
- `nginx`
- `prometheus`
- `alertmanager`
- `grafana`

File chính:

```text
infra/docker-compose.production.yml
infra/nginx.conf
infra/prometheus.yml
backend/Dockerfile
ai_worker/Dockerfile
frontend/Dockerfile
start-production.sh
stop-production.sh
```

## Ranh Giới Cấu Hình

- `.env.example` là template an toàn để commit.
- `.env` là cấu hình thật, không commit.
- `core/settings.py` đọc cấu hình dùng chung.
- `backend/config.py` map cấu hình cho FastAPI.
- `ai_worker/config.py` map cấu hình cho pipeline AI.
- `frontend/src/lib/config.ts` map cấu hình public cho browser.
