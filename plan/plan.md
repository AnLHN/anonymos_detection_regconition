# Roadmap Và Kế Hoạch Triển Khai

Tài liệu này là plan kỹ thuật cho hệ thống phát hiện và nhận diện người lạ. Mục tiêu là giữ repo đủ rõ ràng để push GitHub, chạy CI, bàn giao và tiếp tục phát triển theo hướng production.

## 1. Mục Tiêu

Xây dựng hệ thống:

- Nhận input từ camera RTSP hoặc video source.
- Detect khuôn mặt bằng InsightFace local.
- Extract embedding 512 chiều.
- Search embedding trong Qdrant.
- Lookup metadata nhân viên trong Postgres.
- Phân loại `known`, `unknown`, `unverified`.
- Dùng tracking/voting/rule engine để tạo cảnh báo unknown ổn định.
- Quản trị qua FastAPI backend và Next.js admin frontend.
- Deploy được bằng Docker Compose.
- Kiểm tra được bằng GitHub Actions CI.

## 2. Data Contract

Qdrant:

```text
Collection: employee_faces
Vector size: 512
Distance: Cosine
Payload: employee_id, emp_code, name, department, is_active
```

Postgres:

```text
employees
accounts
camera_sources
alert_rules
unknown_events
system_metrics
audit_logs
```

Mapping chính:

```text
Qdrant payload.employee_id ↔ Postgres employees.id
Qdrant payload.emp_code    ↔ Postgres employees.emp_code
Qdrant payload.name        ↔ Postgres employees.name
```

Điều kiện bắt buộc:

- Embedding mới phải có 512 chiều.
- Recognition model/cách normalize phải tương thích với dữ liệu đã import vào Qdrant.
- Chỉ xem nhân viên active là match hợp lệ.
- `.env` không được commit.

## 3. Pipeline Tổng Thể

```text
Camera / RTSP / Video
        ↓
Frame reader
        ↓
InsightFace detection
        ↓
Face quality check
        ↓
InsightFace recognition embedding
        ↓
Qdrant top-k search
        ↓
Recognition decision
        ↓
Tracking + voting
        ↓
Zone / ROI
        ↓
Rule engine
        ↓
Alert manager
        ↓
Postgres + snapshots + JSONL fallback
        ↓
Backend API
        ↓
Frontend admin
```

## 4. Trạng Thái Hiện Tại

Đã có:

- AI pipeline cơ bản trong `ai_worker/`.
- Qdrant/Postgres services.
- Import/verify database scripts.
- Tracking, rule engine, alert manager.
- FastAPI backend với auth, alerts, employees, cameras, rules, health.
- Next.js frontend admin.
- Dockerfiles cho backend, frontend, worker.
- Production Compose.
- Setup/start/stop scripts.
- Benchmark script.
- GitHub Actions CI.
- Tài liệu setup/architecture/deployment/operations/model/CI-CD.

Cần kiểm thử thêm trước production thật:

- Camera RTSP thật trong thời gian dài.
- Dataset benchmark thật.
- Threshold/rule theo môi trường thực tế.
- Backup/restore định kỳ.
- Monitoring/log retention ngoài Docker mặc định.

## 5. Phase Checklist

### Phase 0: Khóa Schema Và Dữ Liệu Nền

- [x] Xác định Qdrant collection `employee_faces`.
- [x] Xác định vector size `512`.
- [x] Xác định distance `Cosine`.
- [x] Xác định mapping Qdrant ↔ Postgres.
- [x] Có script verify database.

### Phase 1: Project Skeleton

- [x] Có `ai_worker/`, `backend/`, `frontend/`, `core/`, `infra/`, `scripts/`.
- [x] Có settings loader dùng `.env`.
- [x] Có requirements Python.
- [x] Có package frontend.

### Phase 2: Database Local

- [x] Docker Compose local cho Postgres/Qdrant.
- [x] Script import Postgres export.
- [x] Script import Qdrant export.
- [x] Script init event schema.
- [x] Script verify DB.

### Phase 3: InsightFace Detection/Recognition

- [x] Detector local.
- [x] Recognizer local.
- [x] Face quality check.
- [x] Embedding 512-d.
- [ ] Benchmark đủ lớn trên ảnh thật.

### Phase 4: Known/Unknown Decision

- [x] Qdrant top-k search.
- [x] Threshold decision.
- [x] Status `known`, `unknown`, `unverified`.
- [x] Debug top-k candidates.
- [ ] Chốt threshold production bằng dataset thật.

### Phase 5: RTSP/Camera Worker

- [x] Runner RTSP trực tiếp.
- [x] Worker đọc camera từ Postgres.
- [x] Reconnect/backoff khi lỗi camera.
- [x] Worker health check.
- [ ] Soak test nhiều giờ với camera thật.

### Phase 6: Tracking, Zone Và Rule

- [x] Tracking/voting theo track.
- [x] Zone manager.
- [x] Rule engine đọc từ Postgres.
- [x] Cooldown chống spam.
- [x] Fallback rule từ `.env`.
- [ ] Review rule với nghiệp vụ thực tế.

### Phase 7: Event Store Và Alert

- [x] Bảng `unknown_events`.
- [x] Snapshot full frame/face crop.
- [x] JSONL fallback.
- [x] Alert review status/note.
- [ ] Chính sách retention cho snapshot/log.

### Phase 8: Backend API

- [x] Auth JWT.
- [x] Health/metrics.
- [x] Alerts API.
- [x] Cameras API.
- [x] Rules API.
- [x] Employees API.
- [x] CORS cho frontend.

### Phase 9: Frontend Admin

- [x] Next.js App Router + TypeScript.
- [x] Login.
- [x] Dashboard.
- [x] Alerts list/detail.
- [x] Cameras panel.
- [x] Rules panel.
- [x] Employees list.
- [x] Typecheck/build trong CI.

### Phase 10: Deployment

- [x] `.env.example`.
- [x] `.dockerignore`.
- [x] Backend Dockerfile.
- [x] Worker Dockerfile.
- [x] Frontend Dockerfile.
- [x] `infra/docker-compose.production.yml`.
- [x] `start-production.sh`.
- [x] `stop-production.sh`.
- [x] Production env validator.
- [x] Compose health checks.
- [x] Docker log rotation.
- [ ] External secret manager nếu triển khai nghiêm túc.

### Phase 11: CI/CD

- [x] GitHub Actions workflow.
- [x] Python dependency install.
- [x] Python compile check.
- [x] Backend import check.
- [x] Frontend npm install.
- [x] Frontend typecheck.
- [x] Frontend build.
- [x] Production Compose config validation.
- [ ] Thêm lint/test khi có test suite chính thức.
- [ ] Thêm Docker image build/push nếu triển khai qua registry.

### Phase 12: Documentation

- [x] README chuẩn GitHub.
- [x] Setup guide.
- [x] Architecture guide.
- [x] Model guide.
- [x] Operations guide.
- [x] Deployment guide.
- [x] CI/CD guide.
- [x] Roadmap/plan.
- [ ] Cập nhật report cuối cùng sau benchmark thật.

## 6. Chuẩn Push GitHub

Trước khi push:

```powershell
git status --short
npm run typecheck --prefix frontend
npm run build --prefix frontend
docker compose --env-file .env.example -f infra/docker-compose.production.yml config --quiet
```

Python compile:

```powershell
$files = Get-ChildItem -Recurse -Filter *.py | Where-Object { $_.FullName -notmatch '\\.venv|__pycache__' } | ForEach-Object { $_.FullName }
python -m py_compile $files
python -c "from backend.main import app; print(app.title)"
```

Không push:

- `.env`
- Secret thật
- Camera password thật
- Export JSON thật
- Runtime snapshots/logs
- Build/cache output

## 7. Hướng Nâng Cấp CI/CD

Ưu tiên tiếp theo:

1. Thêm Ruff lint.
2. Thêm Pytest cho backend service và rule engine.
3. Build Docker image trong CI.
4. Push image lên GitHub Container Registry.
5. Tạo staging deploy workflow.
6. Dùng GitHub Environments để quản lý secret.
7. Thêm dependency/security scan.

## 8. Definition Of Done Trước Production Thật

- [ ] CI pass trên GitHub.
- [ ] `.env` production không còn placeholder/default secret.
- [ ] Camera thật chạy ổn định ít nhất một ca vận hành.
- [ ] Benchmark có số liệu known/unknown/hard cases.
- [ ] Threshold/rule được chốt bằng dữ liệu thật.
- [ ] Backup/restore Postgres đã kiểm thử.
- [ ] Snapshot/log retention được cấu hình.
- [ ] Người vận hành có tài khoản và biết quy trình xử lý alert.
- [ ] Tài liệu deployment/operations khớp môi trường chạy thật.
