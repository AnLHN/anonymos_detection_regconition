# Setup Local

Tài liệu này hướng dẫn dựng môi trường local từ đầu. Khuyến nghị chạy `start.sh` bằng Git Bash trên Windows để khớp flow vận hành hiện tại.

## 1. Clone Repository

```bash
git clone https://github.com/AnLHN/anonymos_detection_regconition.git
cd anonymos_detection_regconition
```

Nếu đang làm trong thư mục hiện tại thì bỏ qua bước clone.

## 2. Tạo Cấu Hình

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Không commit `.env`. Các nhóm biến cần kiểm tra:

- `POSTGRES_*`
- `QDRANT_*`
- `JWT_SECRET`
- `CAMERA_*_RTSP`
- `FACE_THRESHOLD`
- `DEFAULT_AI_INTERVAL`
- `UNKNOWN_ALERT_COOLDOWN_SECONDS`

## 3. Chạy Setup

Mặc định `setup.sh` chỉ typecheck frontend để tránh build quá nặng:

```bash
./setup.sh
```

Tùy chọn:

```bash
SETUP_FRONTEND_CHECK=build ./setup.sh
SETUP_FRONTEND_CHECK=none ./setup.sh
```

Nếu chạy thủ công:

```powershell
docker compose -f infra/docker-compose.yml up -d
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/db/bootstrap_exports_if_missing.py
python scripts/db/init_event_schema.py
python scripts/db/verify_databases.py
npm ci --prefix frontend
npm run typecheck --prefix frontend
```

## 4. Start/Stop

Start:

```bash
./start.sh
```

Stop:

```bash
./stop.sh
```

URL mặc định:

```text
Frontend local: http://localhost:3000
Frontend LAN:   http://192.168.2.17:3000
Backend:        http://localhost:8000
Prometheus:     http://localhost:9090
RabbitMQ UI:    http://localhost:15672
MediaMTX WHEP:  http://localhost:8889
```

## 5. Chạy Từng Service Thủ Công

Backend:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

AI worker tất cả camera active:

```powershell
python scripts/cameras/run_worker.py
```

Một camera cụ thể:

```powershell
python scripts/cameras/run_worker.py --camera-id door_67b
```

RTSP trực tiếp:

```powershell
python ai_worker/run_rtsp.py --camera-id door_67b --source "rtsp://user:password@ip:554/Streaming/Channels/101"
```

## 6. Lưu Ý Windows/Git Bash

Git Bash/MSYS có thể đổi env `/api` thành Windows path `D:/Git/api`. Vì vậy `start.sh` dùng:

```text
NEXT_PUBLIC_API_BASE=http://192.168.2.17:3000/api
```

Frontend cũng normalize API base để fallback về `/api` nếu gặp Windows path hoặc `file:`.

Next.js local dùng:

```text
frontend/.next-rapi-local
```

để tránh cache `.next`/`.next-dev-local` từng bị kẹt quyền trên Windows.

Nếu cần xóa cache cũ, mở terminal Run as administrator:

```bat
cd /d D:\NTC_AI\Code\phat_hien_anonymos
takeown /f frontend\.next /r /d y
takeown /f frontend\.next-dev-local /r /d y
icacls frontend\.next /grant "%USERNAME%:(OI)(CI)F" /T /C
icacls frontend\.next-dev-local /grant "%USERNAME%:(OI)(CI)F" /T /C
rmdir /s /q frontend\.next
rmdir /s /q frontend\.next-dev-local
```

## 7. Kiểm Tra Trước Khi Push

```powershell
$files = Get-ChildItem -Recurse -Filter *.py | Where-Object { $_.FullName -notmatch '\\.venv|__pycache__|\\.next|node_modules' } | ForEach-Object { $_.FullName }
python -m py_compile $files
python -c "from backend.main import app; print(app.title)"
npm run typecheck --prefix frontend
npm run build --prefix frontend
docker compose --env-file .env.example -f infra/docker-compose.production.yml config --quiet
```
