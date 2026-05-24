# Setup Guide

## 1. Chuẩn bị `.env`

```powershell
Copy-Item .env.example .env
```

Điền các cấu hình:

- `POSTGRES_*`
- `QDRANT_*`
- `INSIGHTFACE_*`
- `CAMERA_*_RTSP`
- `JWT_SECRET`

## 2. Chuẩn bị dữ liệu export

Đặt file JSON vào:

```text
data/exports/
├── manifest_20260521T080719Z.json
├── postgres_20260521T080719Z.json
└── qdrant_20260521T080719Z.json
```

## 3. Cài dependency và import DB

```bash
./setup.sh
```

Nếu không chạy được `.sh` trên Windows, chạy từng bước:

```powershell
docker compose -f infra/docker-compose.yml up -d
python -m pip install -r requirements.txt
python scripts/db/import_postgres_export.py
python scripts/db/import_qdrant_export.py
python scripts/db/init_event_schema.py
python scripts/db/verify_databases.py
```

## 4. Kiểm tra runtime

```powershell
python scripts/dev/check_runtime.py
```

Kỳ vọng:

```text
cv2: OK
numpy: OK
onnxruntime: OK
insightface: OK
```

## 5. Chạy backend

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 6. Chạy camera

```powershell
python scripts/cameras/run_camera_from_env.py door_67b
```
