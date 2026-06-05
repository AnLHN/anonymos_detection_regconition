# Operations

Tài liệu vận hành hằng ngày cho môi trường local hoặc production-base.

## Start/Stop Local

```bash
./start.sh
./stop.sh
```

Kiểm tra DB:

```powershell
python scripts/db/verify_databases.py
```

Kiểm tra runtime AI:

```powershell
python scripts/dev/check_runtime.py
```

## Backend

Start thủ công:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoint quan trọng:

```text
POST  /auth/login
GET   /auth/me
GET   /system/health
GET   /system/analytics
GET   /alerts
PATCH /alerts/{event_id}/status
GET   /cameras
GET   /cameras/runtime
POST  /cameras/{camera_id}/reload
GET   /rules
PATCH /rules/{rule_code}
GET   /employees
GET   /users
PATCH /users/{username}
```

## Frontend

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

Build check:

```powershell
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

Nếu browser báo `file:///D:/Git/api/...`, restart bằng `./start.sh` mới. `start.sh` đã tránh Git Bash path conversion bằng API base đầy đủ.

## Camera Worker

Chạy tất cả camera active:

```powershell
python scripts/cameras/run_worker.py
```

Chạy một camera:

```powershell
python scripts/cameras/run_worker.py --camera-id door_67b
```

Chạy trực tiếp RTSP:

```powershell
python ai_worker/run_rtsp.py --camera-id door_67b --source "rtsp://user:password@ip:554/Streaming/Channels/101"
```

Worker publish frame/meta vào Redis:

```text
camera:{camera_id}:latest_raw_jpeg
camera:{camera_id}:latest_annotated_jpeg
camera:{camera_id}:latest_meta
```

Nếu Dashboard hiện `Waiting for camera worker frame`, kiểm tra theo thứ tự:

1. Camera active trong DB.
2. RTSP URL đúng và camera không block session.
3. Worker còn chạy.
4. Redis có latest frame/meta.
5. Backend `/cameras/runtime` có trạng thái mới.

Backend không tự mở RTSP fallback cho MJPEG; live frame đến từ worker.

## Camera Reload

Reload camera có cooldown để chống spam:

- Frontend disable nút reload trong cooldown.
- Backend dùng Redis lock.
- Backend không spawn subprocess worker nặng trong request reload.
- Worker tự đọc lại trạng thái camera/runtime.

Nếu camera vẫn lỗi sau reload:

- `timed out`: RTSP không phản hồi hoặc camera bận.
- `WinError 10054`: remote host/camera đóng connection.
- `inactive + error`: camera đang active trong DB nhưng worker không mở được stream.

## Users Và RBAC

Role:

```text
0 viewer
1 operator
5 admin
9 admin_super
```

Khi update quyền user, backend ghi audit log vào `audit_logs`. Dữ liệu `created_at/updated_at` đã được convert sang ISO string trước khi ghi JSONB để tránh lỗi 500.

Không được hạ quyền hoặc khóa admin_super cuối cùng.

## Monitoring

Prometheus:

```text
http://localhost:9090
```

Grafana:

```text
http://localhost:3001
```

Alertmanager:

```text
http://localhost:9093
```

Frontend monitoring page:

```text
/system/monitoring
```

Nếu iframe Grafana không load, kiểm tra:

- `NEXT_PUBLIC_GRAFANA_DASHBOARD_URL`.
- Grafana có chạy không.
- `GRAFANA_ALLOW_EMBEDDING`.
- Anonymous viewer hoặc reverse proxy auth.
- Prometheus targets có UP không.

## Runtime Outputs

```text
storage/snapshots/      full frame và face crop
storage/logs/           JSONL/debug logs
storage/debug_faces/    ảnh debug detection/recognition
.runtime/               pid và log local scripts
```

Không commit runtime output lên GitHub.

## Troubleshooting Nhanh

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Frontend đứng `Starting...` | Next cache kẹt quyền | Dùng `.next-rapi-local`, xóa cache cũ bằng admin nếu cần |
| API gọi `file:///D:/Git/api` | Git Bash convert `/api` | Dùng `start.sh` mới, hard refresh browser |
| `/api/users/*` 500 | Audit JSON chứa datetime ở bản cũ | Backend reload code mới, kiểm tra `backend/users/router.py` |
| Camera `timed out` | RTSP không phản hồi | Test RTSP, giảm spam reload, kiểm tra camera |
| `WinError 10054` | Camera đóng connection | Kiểm tra session limit/camera firmware/network |
| `Waiting for camera worker frame` | Worker chưa publish Redis | Kiểm tra worker, Redis keys, camera source |

## Production Commands

```bash
python scripts/dev/validate_production_env.py
./start-production.sh
./stop-production.sh
```
