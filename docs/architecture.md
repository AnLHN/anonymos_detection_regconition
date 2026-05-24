# Architecture

## Tổng quan

```text
Camera / RTSP / Webcam
        ↓
AI Worker
        ↓
InsightFace detection + recognition
        ↓
Qdrant vector search
        ↓
Known / Unknown / Unverified
        ↓
Tracking + Voting
        ↓
Zone / Rule Engine
        ↓
AlertManager
        ↓
Snapshot storage + JSONL + Postgres unknown_events
        ↓
Backend API
        ↓
Frontend Admin
```

## Thành phần

### AI Worker

Thư mục: `ai_worker/`

Nhiệm vụ:

- Đọc frame từ webcam/RTSP.
- Chạy InsightFace.
- Search Qdrant.
- Quyết định Known/Unknown/Unverified.
- Tracking/voting.
- Rule warning.
- Lưu snapshot/log/event.

### Backend

Thư mục: `backend/`

Nhiệm vụ:

- Login JWT.
- Health check Postgres/Qdrant.
- API alerts/employees/cameras/rules.

### Frontend

Thư mục: `frontend/`

Nhiệm vụ:

- Login.
- Dashboard cơ bản.
- Xem alerts/cameras/rules/employees.

### Databases

- Postgres: metadata, employees, accounts, unknown_events, camera_sources, alert_rules.
- Qdrant: face embeddings trong collection `employee_faces`.

## Model

- InsightFace model pack: `buffalo_l`.
- Detection: `det_10g.onnx`.
- Recognition: `w600k_r50.onnx`.
- Embedding: 512 chiều.
- Vector distance: Cosine.
