# Anonymous Detection & Recognition

Hệ thống phát hiện người lạ dựa trên camera/RTSP, InsightFace local, Qdrant vector search và Postgres event store.

## Tính năng hiện có

- Chạy InsightFace local với model pack `buffalo_l`.
- Face detection: `det_10g.onnx`.
- Face recognition: `w600k_r50.onnx`, embedding 512 chiều.
- Search nhân viên bằng Qdrant collection `employee_faces`.
- Metadata nhân viên và event lưu trong Postgres.
- Hỗ trợ webcam và RTSP.
- Tracking + voting đơn giản theo track.
- Rule engine cảnh báo Unknown.
- Lưu snapshot + JSONL + Postgres `unknown_events`.
- Backend FastAPI tối thiểu.
- Frontend admin static skeleton.

## Kiến trúc thư mục

```text
.
├── ai_worker/              # AI pipeline, RTSP runner, tracking/rules/alerts
├── backend/                # FastAPI backend API
├── core/                   # .env settings loader dùng chung
├── data/exports/           # nơi đặt file export JSON local, không commit data thật
├── docs/                   # tài liệu vận hành/triển khai
├── frontend/               # admin UI static skeleton
├── infra/                  # docker compose Postgres/Qdrant
├── plan/                   # roadmap triển khai
├── reports/                # benchmark/report output
├── scripts/                # db/camera/benchmark/dev scripts
├── storage/                # snapshots/logs/debug output, không commit runtime data
├── .env.example            # template cấu hình
├── setup.sh
├── start.sh
└── stop.sh
```

## Yêu cầu môi trường

- Windows/Linux có Python 3.12+.
- Docker + Docker Compose.
- Microsoft Visual C++ Build Tools trên Windows để build `insightface` nếu cần.
- Camera RTSP hoặc webcam.

## Cài đặt nhanh

1. Copy `.env.example` thành `.env` và điền thông tin thật:

```powershell
Copy-Item .env.example .env
```

2. Đặt export JSON vào:

```text
data/exports/postgres_20260521T080719Z.json
data/exports/qdrant_20260521T080719Z.json
data/exports/manifest_20260521T080719Z.json
```

3. Chạy setup:

```bash
./setup.sh
```

Nếu dùng PowerShell/Git Bash trên Windows, chạy script trong Git Bash hoặc WSL. Có thể chạy từng lệnh Python thủ công nếu shell không hỗ trợ `.sh`.

## Start/Stop services

Start Postgres/Qdrant:

```bash
./start.sh
```

Stop services và release ports:

```bash
./stop.sh
```

## Chạy backend API

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Health check:

```text
GET http://localhost:8000/system/health
```

## Chạy frontend admin

Mở file sau trong browser:

```text
frontend/index.html
```

Tài khoản dev phụ thuộc dữ liệu export trong bảng `accounts`.

## Chạy camera từ `.env`

```powershell
python scripts/cameras/run_camera_from_env.py door_67b
python scripts/cameras/run_camera_from_env.py ai_pm_1
python scripts/cameras/run_camera_from_env.py ai_pm_2
```

Hoặc chạy trực tiếp RTSP:

```powershell
python ai_worker/run_webcam.py --camera-id door_67b --source "rtsp://user:password@ip:554/Streaming/Channels/101"
```

## Benchmark

```powershell
python scripts/benchmark/benchmark_pipeline.py --input path\to\image_or_folder
```

Output:

```text
reports/benchmark_results.json
reports/benchmark.md
```

## Cấu hình quan trọng

Tất cả cấu hình chính nằm trong `.env`:

- Postgres/Qdrant.
- InsightFace model pack.
- Threshold nhận diện.
- Camera RTSP URL.
- Rule/cooldown.
- Backend JWT.

Không commit `.env` lên GitHub. Chỉ commit `.env.example`.

## Dữ liệu không nên commit

- `.env`.
- File JSON export thật trong `data/exports/`.
- Snapshot/log runtime trong `storage/`.
- Model/cache local.

## CI/CD

GitHub Actions hiện chạy kiểm tra cơ bản:

- Cài dependencies.
- Compile Python source bằng `py_compile`.
- Kiểm tra import backend app.

Xem workflow tại:

```text
.github/workflows/ci.yml
```

## Trạng thái production

Repo hiện là bản prototype/production-base. Các phần còn cần hoàn thiện trước khi production thật:

- Camera worker service quản lý nhiều camera từ DB.
- Frontend alert detail + snapshot viewer + review status.
- Rule Engine đọc cấu hình từ Postgres.
- Benchmark dataset thật và khóa threshold.
- Dockerfile backend/frontend/worker.
- Deployment guide đầy đủ.
