# Ke hoach hop nhat luong camera stream va luong AI worker

## Muc tieu

Chuyen kien truc hien tai tu 2 pipeline doc RTSP/chay AI rieng biet sang 1 pipeline trung tam:

```text
Camera RTSP
  -> ai_worker doc 1 lan
  -> AI infer/tracking/rule/event
  -> tao latest raw/annotated frame/result
  -> backend chi lay frame/result de stream cho frontend
  -> frontend hien thi live monitor
```

Ket qua mong doi:

- RTSP chi bi doc 1 lan cho moi camera.
- AI chi chay 1 lan cho moi camera.
- Live view va alert/event dung cung mot nguon ket qua nhan dien.
- Backend khong can load model AI de phuc vu MJPEG stream.
- Giam tinh trang live annotation va alert bi lech nhau do 2 pipeline doc 2 frame khac nhau.

## Hien trang hien tai

Hien tai he thong co 2 pipeline runtime doc cung mot camera RTSP:

### 1. Backend stream pipeline

```text
Frontend LiveMonitor
  -> GET /cameras/{camera_id}/mjpeg
  -> backend/cameras/router.py
  -> backend/cameras/annotated_stream.py
  -> CameraStreamWorker
  -> CameraFrameReader doc RTSP
  -> FaceRecognitionPipeline
  -> CentroidTracker
  -> ZoneManager
  -> draw annotation
  -> encode JPEG
  -> tra MJPEG ve browser
```

Muc dich:

- Hien thi live camera tren Dashboard.
- Ve box/label/zone de nguoi van hanh xem.
- Giu stream nong khi reload/chuyen trang.

### 2. AI worker pipeline

```text
ai_worker camera worker / RTSP runner
  -> CameraFrameReader doc RTSP
  -> FaceRecognitionPipeline
  -> tracking/zone
  -> RuleEngine
  -> UnknownEventDetector
  -> luu Postgres event/snapshot
  -> publish RabbitMQ/alert
```

Muc dich:

- Nhan dien known/unknown.
- Ap rule canh bao.
- Sinh event/alert.
- Luu snapshot.
- Cap nhat worker status.

### Van de

- Mot camera co the bi doc RTSP 2 lan.
- AI co the chay 2 lan.
- Live annotation va alert/event co the lech nhau vi 2 pipeline doc 2 frame/timing khac nhau.
- Ton tai nguyen CPU/GPU/network hon khi so camera tang.

## Huong kien truc de xuat

Dung `ai_worker` lam nguon truth duy nhat cho camera:

```text
ai_worker/camera_worker.py
  -> doc RTSP
  -> infer
  -> tracking
  -> rule engine
  -> event/alert
  -> draw annotated frame
  -> encode latest raw/annotated JPEG
  -> ghi Redis latest frame/result

backend/cameras/annotated_stream.py
  -> khong doc RTSP
  -> khong chay FaceRecognitionPipeline
  -> doc latest annotated JPEG tu Redis
  -> stream MJPEG ve browser

backend/employees/router.py
  -> enroll nhan vien tu latest raw frame trong Redis

frontend/src/components/LiveMonitor.tsx
  -> giu API MJPEG hien tai, gan nhu khong doi
```

## Chon co che chia se frame/result

### Lua chon uu tien: Redis latest frame

Project da co Redis nen dung Redis la cach don gian nhat cho phase dau.

Key goi y:

```text
camera:{camera_id}:latest_raw_jpeg
camera:{camera_id}:latest_annotated_jpeg
camera:{camera_id}:latest_meta
```

`latest_raw_jpeg`:

- Frame goc encode JPEG.
- Dung cho enrollment/extract face.

`latest_annotated_jpeg`:

- Frame da ve box/label/zone/status.
- Dung cho Dashboard live MJPEG.

`latest_meta`:

```json
{
  "camera_id": "door_67b",
  "frame_id": 12345,
  "created_at": "2026-06-02T10:25:30.123Z",
  "read_fps": 24.8,
  "ai_latency_ms": 83,
  "tracks": [
    {
      "track_id": 7,
      "label": "unknown",
      "score": 0.72,
      "bbox": [100, 80, 220, 260],
      "zone": "door"
    }
  ]
}
```

Redis TTL goi y:

```text
latest_raw_jpeg: 5-15 giay
latest_annotated_jpeg: 5-15 giay
latest_meta: 5-15 giay
```

## Phase A - AI worker publish latest frame/result

### Files du kien

- `ai_worker/camera_worker.py`
- `ai_worker/redis_frame_publisher.py` moi
- `ai_worker/visualization.py`
- `ai_worker/config.py`
- `ai_worker/redis_state.py` neu muon reuse Redis client hien co

### Cong viec

1. Tao service moi `RedisFramePublisher`:

```python
class RedisFramePublisher:
    def publish_raw_frame(camera_id: str, frame, frame_id: int) -> None: ...
    def publish_annotated_frame(camera_id: str, frame, meta: dict) -> None: ...
    def get_latest_raw_frame(camera_id: str): ...
    def get_latest_annotated_jpeg(camera_id: str): ...
```

2. Trong `ai_worker/camera_worker.py`, sau khi doc/infer/tracking:

- tao raw JPEG theo FPS gioi han.
- tao annotated frame bang `draw_tracks`/zone/status.
- ghi Redis.

3. Them config:

```text
STREAM_PUBLISH_FPS=5
STREAM_JPEG_QUALITY=75
STREAM_FRAME_TTL_SECONDS=10
```

4. Gioi han publish FPS de tranh Redis qua tai:

```text
camera 25 FPS -> chi publish stream 5-10 FPS
```

### Tieu chi hoan thanh

- Khi ai_worker chay, Redis co key latest frame cho camera.
- Frame het TTL neu worker dung.
- Khong anh huong sinh event/alert hien co.

## Phase B - Backend MJPEG stream doc tu Redis

### Files du kien

- `backend/cameras/annotated_stream.py`
- `backend/cameras/router.py`
- `backend/config.py`

### Cong viec

1. Them backend helper doc Redis latest annotated JPEG.

2. Doi `annotated_mjpeg_frames()`:

Tu:

```text
backend tu tao CameraStreamWorker -> doc RTSP -> infer -> encode JPEG
```

Thanh:

```text
poll Redis camera:{camera_id}:latest_annotated_jpeg
neu co frame moi -> yield MJPEG multipart
neu khong co -> yield waiting frame hoac giu ket noi cho toi khi co frame
```

3. Khong load `FaceRecognitionPipeline` trong backend stream nua.

4. Giu API hien co:

```http
GET /cameras/{camera_id}/mjpeg
```

De frontend khong can doi lon.

5. Neu Redis khong co frame:

- Tra frame placeholder `Waiting for camera worker...`, hoac
- Giu connection va frontend se thay `connecting`/`error` tuy implementation.

Khuyen nghi phase dau: tao placeholder JPEG de UI ro rang.

### Tieu chi hoan thanh

- Mo Dashboard live thi backend stream frame tu Redis.
- Tat ai_worker thi Dashboard khong tu doc RTSP rieng nua.
- Backend khong khoi tao `FaceRecognitionPipeline` cho stream.

## Phase C - Enrollment lay latest raw frame tu Redis

### Files du kien

- `backend/employees/router.py`
- `backend/cameras/annotated_stream.py` hoac helper Redis frame rieng
- `ai_worker/redis_frame_publisher.py`/shared module neu can

### Cong viec

1. Doi endpoint:

```http
POST /employees/enroll-from-camera
```

Tu:

```text
get_latest_camera_frame() -> co the start backend stream worker rieng
```

Thanh:

```text
lay camera:{camera_id}:latest_raw_jpeg tu Redis
cv2.imdecode -> frame
InsightFaceRecognizer.extract_embeddings(frame)
```

2. Neu Redis khong co raw frame:

```text
503: Chua co frame moi tu camera worker
```

3. Giu validate hien co:

- 0 face -> 400
- >1 face -> 400
- face nho/score thap -> 400
- duplicate emp_code -> 409
- Qdrant fail -> deactivate employee + 500

### Tieu chi hoan thanh

- Them nhan vien dung frame tu worker chinh.
- Backend khong can start camera stream worker de enroll.

## Phase D - Go/giam backend stream AI worker cu

### Files du kien

- `backend/cameras/annotated_stream.py`
- `backend/cameras/router.py`
- `backend/employees/router.py`

### Cong viec

1. Xoa hoac vo hieu hoa cac import AI trong backend stream:

- `CameraFrameReader`
- `FaceRecognitionPipeline`
- `CentroidTracker`
- `ZoneManager`
- `draw_tracks`

2. Xoa registry `_STREAM_WORKERS` neu khong con can fallback.

3. Giu lai helper stream tu Redis.

4. Neu muon an toan, co the giu fallback bang config:

```text
BACKEND_STREAM_FALLBACK_LOCAL=false
```

Khuyen nghi production: default `false` de dam bao chi co 1 pipeline.

### Tieu chi hoan thanh

- Backend stream khong doc RTSP.
- Backend stream khong chay model AI.
- Mot camera chi co ai_worker doc RTSP.

## Phase E - Verification runtime

### Kiem tra can lam

1. Start Redis, Postgres, Qdrant, backend, ai_worker, frontend.

2. Mo Dashboard.

Expected:

- LiveMonitor hien frame tu Redis/worker.
- Network van goi `/cameras/{camera_id}/mjpeg` nhu cu.
- Backend log khong co khoi tao `FaceRecognitionPipeline` cho MJPEG.

3. Tat ai_worker.

Expected:

- Redis frame het TTL.
- Dashboard dung/placeholder/error ro rang.
- Backend khong tu mo RTSP fallback neu fallback disabled.

4. Bat ai_worker lai.

Expected:

- Dashboard co frame lai.
- Alert/event van sinh binh thuong.

5. Them nhan vien tu camera.

Expected:

- Endpoint enroll lay latest raw frame tu Redis.
- Employee moi luu Postgres.
- Qdrant co point moi.

6. So sanh tai nguyen.

Expected:

- So connection RTSP/camera giam tu 2 xuong 1 khi Dashboard dang mo.
- CPU/GPU backend giam vi khong infer stream.

## Lenh kiem tra ky thuat

```powershell
python -m compileall backend ai_worker
npm run typecheck --prefix frontend
npm run build --prefix frontend
```

Neu verify runtime dung skill `/verify`, tap trung vao viec chay app that va quan sat Dashboard/enrollment, khong chi dua vao build/typecheck.

## Rủi ro va tradeoff

### Neu ai_worker chet thi live stream cung mat

Day la tradeoff chap nhan duoc vi ai_worker la nguon truth nghiep vu. Neu worker chet thi he thong canh bao cung dang loi, Dashboard nen hien ro trang thai do thay vi backend tu chay pipeline phu.

### Redis bandwidth co the tang

Can gioi han:

```text
STREAM_PUBLISH_FPS=5 hoac 10
STREAM_JPEG_QUALITY=70-80
TTL ngan
```

### Delay nho

Co them do tre worker -> Redis -> backend -> browser. Chap nhan duoc cho Dashboard giam sat neu FPS publish hop ly.

### Multi-process backend

Redis lam shared source nen backend chay nhieu process van doc duoc frame, tot hon registry in-process hien tai.

## Ket luan

Huong nay dua he thong ve kien truc ro rang hon:

```text
ai_worker = doc camera + AI + event + tao frame/result
backend = API gateway + MJPEG proxy tu Redis
frontend = hien thi
```

Day la phase nen lam tiep neu muc tieu la production va giam tai khi so camera tang.
