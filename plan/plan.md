# Plan dựng hệ thống phát hiện người lạ với InsightFace local, Qdrant và Postgres

## 1. Mục tiêu

Dựng hệ thống phát hiện người lạ theo hướng chạy **InsightFace trực tiếp trên máy local**, chỉ dùng hai phần:

- **Detection**: phát hiện khuôn mặt trong ảnh/frame.
- **Recognition**: trích xuất embedding khuôn mặt 512 chiều.

Sau đó dùng embedding để search trong **Qdrant**, lấy thông tin nhân viên từ payload hoặc **Postgres**, rồi phân loại:

- `Known`: người có trong database.
- `Unknown`: người không khớp ai trong database.
- `Unverified`: mặt không đủ điều kiện để kết luận.

Không cảnh báo ngay khi vừa thấy Unknown. Unknown chỉ đi vào cảnh báo khi thỏa rule như ngoài giờ, vào vùng cấm, đứng lâu ở cổng hoặc xuất hiện nhiều lần.

---

## 2. Dữ liệu hiện có

```text
manifest_20260521T080719Z.json
        ↓
Xác nhận bộ export gồm Postgres + Qdrant

postgres_20260521T080719Z.json
        ↓
Database nghiệp vụ face_db
        ↓
Bảng employees chứa thông tin nhân viên:
- id
- emp_code
- name
- department
- photo_path
- is_active

qdrant_20260521T080719Z.json
        ↓
Vector database
        ↓
Collection employee_faces:
- vector size: 512
- distance: Cosine
- points_count: 44
- payload có employee_id, emp_code, name, department, is_active
```

Mapping quan trọng:

```text
Qdrant payload.employee_id  ↔  Postgres employees.id
Qdrant payload.emp_code     ↔  Postgres employees.emp_code
Qdrant payload.name         ↔  Postgres employees.name
```

Điều kiện bắt buộc:

- Embedding mới từ InsightFace local phải là 512 chiều.
- Embedding mới phải dùng cùng recognition model/cách normalize với embedding đã lưu trong Qdrant.
- Qdrant đang dùng metric `Cosine`.
- Chỉ nhận diện nhân viên đang active nếu `is_active = true`.

---

## 3. Pipeline tổng thể

```text
Camera / Video / Image
        ↓
Frame Reader
        ↓
InsightFace Detection local
        ↓
Face bbox + landmarks + detection score
        ↓
Face quality check
        ↓
Crop / align face
        ↓
InsightFace Recognition local
        ↓
512-d embedding
        ↓
Normalize embedding đúng cách
        ↓
Qdrant search trong collection employee_faces
        ↓
Top-k candidates
        ↓
Recognition Decision
        ↓
Known / Unknown / Unverified
        ↓
Tracking + Voting theo track_id
        ↓
Zone / ROI check
        ↓
Rule Engine
        ↓
Alert / Snapshot / Log
```

---

## 4. Bước dựng database local từ JSON export

Trước khi chạy pipeline nhận diện, cần dựng lại **Postgres** và **Qdrant** local rồi import dữ liệu từ 2 file JSON export vào đó.

### File đã tạo

```text
infra/docker-compose.yml
scripts/import_postgres_export.py
scripts/import_qdrant_export.py
scripts/verify_databases.py
```

### Pipeline dựng DB

```text
postgres_20260521T080719Z.json
        ↓
import_postgres_export.py
        ↓
Postgres local: localhost:7001 / face_db
        ↓
Bảng employees và các bảng export khác

qdrant_20260521T080719Z.json
        ↓
import_qdrant_export.py
        ↓
Qdrant local: localhost:7002
        ↓
Collection employee_faces / 512 / Cosine / 44 points
```

### Thứ tự chạy

```powershell
cd D:\NTC_AI\Code\phat_hien_anonymos

docker compose -f infra/docker-compose.yml up -d

python -m pip install psycopg[binary]

python scripts/import_postgres_export.py
python scripts/import_qdrant_export.py
python scripts/verify_databases.py
```

### Output kiểm chứng mong muốn

```text
Postgres employees count: <số nhân viên>
Qdrant employee_faces status: green
Qdrant employee_faces points_count: 44
```

Chỉ qua bước tiếp theo khi `verify_databases.py` xác nhận cả Postgres và Qdrant đều có dữ liệu.

---

## 5. Phase 0: Khóa schema và dữ liệu nền

### Mục tiêu

Hiểu chắc dữ liệu Postgres, Qdrant và manifest trước khi viết pipeline xử lý ảnh.

### Việc cần làm

- Đọc `manifest_20260521T080719Z.json` để xác nhận bộ export.
- Đọc schema Postgres, tập trung trước vào bảng `employees`.
- Đọc schema Qdrant, tập trung trước vào collection `employee_faces`.
- Xác nhận mapping giữa Qdrant payload và Postgres.
- Xác nhận vector size là `512` và distance là `Cosine`.
- Xác nhận dữ liệu nhân viên active/inactive.

### Output cần có

```text
Data contract:
- employee_id lấy từ Qdrant payload
- name lấy từ Qdrant payload hoặc join Postgres employees
- vector size bắt buộc 512
- metric bắt buộc Cosine
- inactive employee không nên hiển thị là Known hợp lệ
```

### Điều kiện qua phase

- [ ] Biết collection Qdrant chính xác: `employee_faces`.
- [ ] Biết bảng Postgres chính xác: `employees`.
- [ ] Biết key mapping giữa Qdrant và Postgres.
- [ ] Không còn mơ hồ embedding mới phải có shape bao nhiêu.

---

## 5. Phase 1: Dựng project skeleton tối thiểu

### Mục tiêu

Tạo bộ khung code nhỏ, chưa xử lý realtime, chỉ đủ để test từng module độc lập.

### Cấu trúc đề xuất

```text
unknown_detection_system/
├── main.py
├── config.py
├── data_contract.py
├── insightface_detector.py
├── insightface_recognizer.py
├── face_pipeline.py
├── qdrant_service.py
├── postgres_service.py
├── recognition_decision.py
├── tests_manual/
│   ├── test_qdrant_search.py
│   ├── test_postgres_lookup.py
│   ├── test_detect_image.py
│   └── test_recognize_image.py
└── outputs/
    ├── debug_faces/
    └── logs/
```

### Pipeline trong phase này

```text
Config
  ↓
Load Qdrant/Postgres connection info
  ↓
Load InsightFace model config
  ↓
Chạy từng script test độc lập
```

### Điều kiện qua phase

- [ ] Có `config.py` chứa tên collection, threshold, device, model path/name.
- [ ] Có module Qdrant service nhưng chỉ search thử, chưa nối camera.
- [ ] Có module Postgres service nhưng chỉ lookup nhân viên, chưa ghi log.
- [ ] Có module detector/recognizer nhưng chưa realtime.

---

## 6. Phase 2: Kết nối và kiểm thử Qdrant/Postgres trước

### Mục tiêu

Đảm bảo phần DB hoạt động đúng trước khi đụng model ảnh.

### Pipeline kiểm thử

```text
Lấy 1 vector có sẵn từ qdrant export
        ↓
Search lại vào Qdrant collection employee_faces
        ↓
Nhận top-k candidates
        ↓
Lấy employee_id / emp_code / name từ payload
        ↓
Lookup Postgres employees nếu cần bổ sung thông tin
        ↓
In kết quả kiểm chứng
```

### Output mong muốn

```text
Query vector id: 7
Top 1:
- employee_id: 7
- emp_code: NV011
- name: Hoàng Mạnh Tiến
- score: gần 1.0 nếu search bằng chính vector gốc
```

### Điều kiện qua phase

- [x] Query Qdrant thành công.
- [x] Top-1 trả về đúng nhân viên khi dùng vector gốc.
- [x] Payload có đủ `employee_id`, `emp_code`, `name`.
- [x] Lookup Postgres theo `employee_id` thành công nếu cần.

### Kết quả đã kiểm chứng

```text
Script: scripts/test_qdrant_search_with_export_vector.py
Source point_id: 7
Source employee_id: 7
Source name: Hoàng Mạnh Tiến
Top-1 score: 1.000000
Postgres lookup: (7, 'NV011', 'Hoàng Mạnh Tiến', 'GD_Khuvuc', True)
```

---

## 7. Phase 3: Chạy InsightFace detection local trên ảnh tĩnh

### Trạng thái môi trường

```text
Python: 3.12.10
cv2: OK
numpy: OK
onnxruntime: OK
insightface: OK
Visual C++ Build Tools: OK
```

### Mục tiêu

Máy local detect được khuôn mặt ổn định trước khi recognition.

### Pipeline

```text
Input image
        ↓
OpenCV read image
        ↓
InsightFace detection local
        ↓
List face bbox + landmarks + det_score
        ↓
Filter theo MIN_DETECTION_SCORE, MIN_FACE_WIDTH, MIN_FACE_HEIGHT
        ↓
Save ảnh debug có bbox
```

### Output mong muốn

```text
Image: test_employee.jpg
Faces detected: 1
Face 1:
- bbox: [x1, y1, x2, y2]
- det_score: 0.92
- quality: pass
```

### Điều kiện qua phase

- [ ] Detect được mặt trên ảnh nhân viên rõ.
- [ ] Không nhận mặt quá nhỏ/mờ nếu dưới ngưỡng.
- [ ] Lưu được ảnh debug bbox để nhìn bằng mắt.
- [ ] Biết FPS detection tạm thời trên máy local.

### Trạng thái triển khai

```text
Module: unknown_detection_system/insightface_detector.py
Script: unknown_detection_system/tests_manual/test_detect_image.py
Model local: buffalo_l
Detection model: det_10g.onnx
Runtime: CPUExecutionProvider
Status: detector khởi tạo thành công
```

Lệnh test khi có ảnh mẫu:

```powershell
python unknown_detection_system/tests_manual/test_detect_image.py path\to\image.jpg
```

Output debug mặc định:

```text
unknown_detection_system/outputs/debug_faces/detect_debug.jpg
```

---

## 8. Phase 4: Chạy InsightFace recognition local và kiểm tra embedding

### Mục tiêu

Từ bbox đã detect, extract được embedding 512 chiều đúng chuẩn.

### Pipeline

```text
Input image
        ↓
Detection
        ↓
Landmarks
        ↓
Align face
        ↓
Recognition model local
        ↓
Embedding 512-d
        ↓
Normalize embedding
        ↓
Kiểm tra shape + norm
```

### Output mong muốn

```text
Embedding shape: (512,)
Embedding norm: ~1.0 nếu đã normalize
```

### Điều kiện qua phase

- [ ] Extract được embedding từ ảnh rõ mặt.
- [ ] Embedding có đúng 512 chiều.
- [ ] Cách normalize thống nhất với dữ liệu trong Qdrant.
- [ ] Nếu embedding search sai hoàn toàn, dừng lại kiểm tra model recognition có trùng model tạo DB không.

### Trạng thái triển khai

```text
Module: unknown_detection_system/insightface_recognizer.py
Script: unknown_detection_system/tests_manual/test_recognize_image.py
Model local: buffalo_l
Recognition model: w600k_r50.onnx
Runtime: CPUExecutionProvider
Status: recognizer khởi tạo thành công
```

Lệnh test khi có ảnh mẫu:

```powershell
python unknown_detection_system/tests_manual/test_recognize_image.py path\to\image.jpg
```

---

## 9. Phase 5: Nối recognition local với Qdrant để phân loại Known/Unknown

### Mục tiêu

Ảnh tĩnh đi hết pipeline từ ảnh gốc đến Known/Unknown.

### Pipeline

```text
Input image
        ↓
Detect face
        ↓
Quality check
        ↓
Align face
        ↓
Extract embedding
        ↓
Qdrant search top_k=5
        ↓
Best score
        ↓
Compare FACE_THRESHOLD
        ↓
Known / Unknown / Unverified
```

### Logic quyết định

```python
if face_quality_is_low:
    status = "unverified"
elif best_score >= FACE_THRESHOLD:
    status = "known"
else:
    status = "unknown"
```

### Output mong muốn

```text
Image: sample.jpg
Status: known
Name: Nguyen Van A
Employee ID: 10
Score: 0.68
Best candidates:
1. Nguyen Van A - 0.68
2. Tran Van B - 0.42
3. Le Van C - 0.39
```

### Điều kiện qua phase

- [ ] Ảnh nhân viên trong DB có thể ra Known.
- [ ] Ảnh người ngoài DB có thể ra Unknown.
- [ ] Ảnh mờ/nhỏ ra Unverified.
- [x] Có log top-k để debug threshold.

### Trạng thái triển khai

```text
Module: unknown_detection_system/qdrant_http_service.py
Module: unknown_detection_system/recognition_decision.py
Module: unknown_detection_system/face_pipeline.py
Script: unknown_detection_system/tests_manual/test_face_pipeline_image.py
Status: pipeline khởi tạo thành công, chờ ảnh mẫu để test Known/Unknown thực tế
```

Lệnh test khi có ảnh mẫu:

```powershell
python unknown_detection_system/tests_manual/test_face_pipeline_image.py path\to\image.jpg
```

---

## 10. Phase 6: Chạy video/camera nhưng chưa cảnh báo

### Mục tiêu

Đưa pipeline ảnh tĩnh vào video realtime, chỉ vẽ bbox và label, chưa Rule Engine.

### Pipeline

```text
Camera / video file
        ↓
Read frame
        ↓
Skip frame nếu cần để giảm lag
        ↓
Detect faces
        ↓
Recognition theo từng face đủ chất lượng
        ↓
Qdrant search
        ↓
Draw bbox:
- Known: xanh + tên
- Unknown: đỏ + Unknown
- Unverified: vàng/xám + Unverified
        ↓
Show frame / save debug video
```

### Điều kiện qua phase

- [ ] Camera hoặc video chạy ổn định.
- [ ] Không crash khi không có mặt.
- [ ] Không lag quá mức do chạy recognition mỗi frame.
- [x] Có thể cấu hình xử lý mỗi N frame.
- [ ] Label và màu bbox đúng.

### Trạng thái triển khai

```text
Script: unknown_detection_system/run_webcam.py
Camera mặc định: --camera 0
Frame skip mặc định: --frame-skip 5
Known: khung xanh
Unknown: khung đỏ
Unverified: khung vàng
Quit: nhấn q
```

Lệnh chạy webcam:

```powershell
python unknown_detection_system/run_webcam.py --camera 0 --frame-skip 5
```

Nếu CPU lag, tăng skip frame:

```powershell
python unknown_detection_system/run_webcam.py --camera 0 --frame-skip 10
```

---

## 11. Phase 7A: Cảnh báo Unknown ổn định bản đơn giản

### Mục tiêu

Có bản cảnh báo người lạ đầu tiên trước khi làm tracking đầy đủ. Bản này dùng số frame xử lý liên tục có Unknown để tránh cảnh báo chỉ vì một frame đơn lẻ.

### Pipeline

```text
Webcam results
        ↓
Lọc recognition.status == "unknown"
        ↓
Đếm consecutive_unknown_frames
        ↓
Nếu đủ UNKNOWN_STABLE_FRAMES
        ↓
Kiểm tra cooldown UNKNOWN_ALERT_COOLDOWN_SECONDS
        ↓
Tạo warning stable_unknown_face
        ↓
Lưu full frame + face crop
        ↓
Ghi JSONL vào outputs/logs/events.jsonl
```

### Trạng thái triển khai

```text
Module: unknown_detection_system/unknown_event_detector.py
Module: unknown_detection_system/alert_manager.py
Updated: unknown_detection_system/run_webcam.py
Snapshots: unknown_detection_system/outputs/snapshots/
Event log: unknown_detection_system/outputs/logs/events.jsonl
Status: compile OK
```

### Config

```python
UNKNOWN_STABLE_FRAMES = 5
UNKNOWN_ALERT_COOLDOWN_SECONDS = 30
```

### Điều kiện qua phase

- [ ] Unknown ổn định tạo warning.
- [ ] Warning không spam nhờ cooldown.
- [ ] Có snapshot full frame.
- [ ] Có snapshot face crop.
- [ ] Có log JSONL.

---

## 12. Phase 7: Thêm tracking và voting

### Mục tiêu

Không kết luận người lạ dựa trên một frame đơn lẻ.

### Pipeline

```text
Frame detections
        ↓
Tracker assign track_id
        ↓
Lưu recognition history theo track_id
        ↓
Voting nhiều frame
        ↓
Final status theo track:
- known
- unknown
- unverified
        ↓
Draw stable label
```

### Rule voting ban đầu

```python
if known_count >= 5 and best_known_score >= FACE_THRESHOLD:
    final_status = "known"
elif unknown_count >= 10 and known_count == 0:
    final_status = "unknown"
else:
    final_status = "unverified"
```

### Điều kiện qua phase

- [ ] Mỗi người có `track_id` ổn định.
- [ ] Không nhấp nháy Known/Unknown liên tục.
- [x] Unknown chỉ được xác nhận sau nhiều frame.
- [ ] Có duration theo track.

### Trạng thái triển khai

```text
Module: unknown_detection_system/tracker.py
Updated: unknown_detection_system/unknown_event_detector.py
Updated: unknown_detection_system/alert_manager.py
Updated: unknown_detection_system/run_webcam.py
Tracking: centroid distance
Voting history: 30 processed frames
Unknown warning: cooldown theo track_id
Status: compile OK, cần test webcam thực tế
```

---

## 12. Phase 8: Thêm Zone / ROI

### Mục tiêu

Biết người lạ đang ở khu vực nào để phục vụ cảnh báo.

### Pipeline

```text
Track bbox
        ↓
Tính center point hoặc foot point
        ↓
Check point nằm trong polygon nào
        ↓
Gán zone cho track
        ↓
Đưa zone vào Rule Engine sau này
```

### Điều kiện qua phase

- [x] Cấu hình được zone theo camera.
- [x] Vẽ được polygon zone lên frame debug.
- [ ] Track được gán đúng zone.
- [x] Có zone mặc định là `none` nếu không nằm trong vùng nào.

### Trạng thái triển khai

```text
Module: unknown_detection_system/zone_manager.py
Config: CAMERA_ZONES trong unknown_detection_system/config.py
Updated: unknown_detection_system/run_webcam.py
Updated: unknown_detection_system/alert_manager.py
Updated: unknown_detection_system/unknown_event_detector.py
Zone mẫu: webcam_0 / gate
Event log: có thêm zone
Status: compile OK, cần test webcam để kiểm tra polygon có đúng vị trí không
```

---

## 13. Phase 9: Thêm Rule Engine cảnh báo

### Mục tiêu

Chỉ cảnh báo khi Unknown có điều kiện đáng ngờ, không spam khi vừa thấy Unknown.

### Pipeline

```text
Final track status
        ↓
Track duration
        ↓
Zone
        ↓
Current time
        ↓
Rule Engine
        ↓
Warning hoặc no warning
```

### Rule ban đầu

```text
Rule 1: Unknown ngoài giờ làm việc → High
Rule 2: Unknown đứng ở cổng quá N giây → Medium
Rule 3: Unknown vào restricted zone → Critical
Rule 4: Unknown xuất hiện nhiều lần trong M phút → Medium
Rule 5: Unverified vào restricted zone → Medium
```

### Điều kiện qua phase

- [ ] Unknown bình thường trong giờ làm không spam cảnh báo.
- [x] Unknown ngoài giờ có warning.
- [x] Unknown ở vùng cấm có warning.
- [x] Có cooldown theo `track_id` và `warning_type`.

### Trạng thái triển khai

```text
Module: unknown_detection_system/rule_engine.py
Updated: unknown_detection_system/unknown_event_detector.py
Config:
- WORKING_HOUR_START = "08:00"
- WORKING_HOUR_END = "17:30"
- RESTRICTED_ZONES
- GATE_ZONES
- UNKNOWN_GATE_WARNING_FRAMES
Cooldown: theo (track_id, warning_type)
Status: compile OK, cần test webcam theo tình huống thật
```

Rule đã có trong code:

```text
unknown_entered_restricted_area → critical
unknown_outside_working_hours → high
unknown_loitering_at_gate → medium
stable_unknown_face → low
unverified_in_restricted_area → medium
```

---

## 14. Phase 10: Snapshot, log và tích hợp Postgres

### Mục tiêu

Khi có warning, lưu bằng chứng để xem lại và debug.

### Pipeline

```text
Warning event
        ↓
Generate event_id
        ↓
Save full frame
        ↓
Save face crop
        ↓
Build event payload
        ↓
Write JSONL log trước
        ↓
Sau khi ổn định mới ghi Postgres table riêng nếu cần
```

### Dữ liệu log tối thiểu

```json
{
  "event_id": "EVT_20260521_101530_001",
  "camera_id": "gate_01",
  "track_id": 15,
  "status": "unknown",
  "zone": "gate",
  "best_match_employee_id": 7,
  "best_match_name": "Hoàng Mạnh Tiến",
  "best_score": 0.38,
  "warning_type": "unknown_outside_working_hours",
  "warning_level": "high",
  "snapshot_full": "outputs/snapshots/EVT_20260521_101530_001_full.jpg",
  "snapshot_face": "outputs/snapshots/EVT_20260521_101530_001_face.jpg"
}
```

### Điều kiện qua phase

- [ ] Có snapshot full frame.
- [ ] Có snapshot face crop.
- [x] Có JSONL log đọc lại được.
- [x] Có Postgres table `unknown_events` để lưu event chính thức.

### Trạng thái triển khai

```text
Script: scripts/init_event_schema.py
Module: unknown_detection_system/postgres_event_service.py
Updated: unknown_detection_system/alert_manager.py
Updated: setup.sh
Table: unknown_events
Indexes:
- created_at
- camera_id
- warning_level
- review_status
Status: schema tạo thành công, table hiện có 0 events
```

AlertManager hiện ghi song song:

```text
Snapshot full frame
Snapshot face crop
JSONL: unknown_detection_system/outputs/logs/events.jsonl
Postgres: unknown_events
```

---

## 15. Phase 11: Test thực tế và khóa threshold

### Mục tiêu

Chọn threshold và rule bằng dữ liệu camera thật, không chọn theo cảm tính.

### Pipeline đánh giá

```text
Tập ảnh/video nhân viên
        ↓
Tập ảnh/video người lạ
        ↓
Chạy pipeline batch
        ↓
Ghi score, status, best candidate
        ↓
Tính false accept / false reject
        ↓
Điều chỉnh FACE_THRESHOLD
        ↓
Chạy lại video realtime
```

### Chỉ số cần theo dõi

```text
Known accuracy
Unknown detection rate
False accept
False reject
Warning precision
Warning spam rate
Processing FPS
```

### Điều kiện hoàn tất bản dựng đầu tiên

- [ ] Có threshold tạm ổn trên dữ liệu camera thật.
- [ ] FPS đủ dùng trên máy local.
- [ ] Warning không spam.
- [ ] Snapshot/log đủ để truy vết lỗi.
- [ ] Biết rõ các case yếu: thiếu sáng, mặt nghiêng, khẩu trang, motion blur.

### Trạng thái triển khai

```text
Script: scripts/benchmark_pipeline.py
Report template: reports/benchmark.md
Output JSON: reports/benchmark_results.json
Status: compile OK, cần dataset ảnh/video thật để chạy benchmark
```

Lệnh chạy benchmark batch ảnh:

```powershell
python scripts/benchmark_pipeline.py --input path\to\image_or_folder
```

Dataset benchmark đề xuất:

```text
data/benchmark/known/
data/benchmark/unknown/
data/benchmark/hard_cases/
```

---

## 16. Production Roadmap

Phần core AI hiện tại mới là prototype/local pipeline. Để đạt chuẩn production cần bổ sung backend, frontend, login, admin dashboard, database schema chính thức, benchmark, báo cáo và tài liệu triển khai.

### Production pipeline tổng thể

```text
Camera / RTSP / Webcam
        ↓
AI Worker
- InsightFace detection
- InsightFace recognition
- Qdrant search
- Tracking + Voting
- Rule Engine
        ↓
Event Store
- Postgres events
- Snapshot storage
        ↓
Backend API
- Auth
- Camera management
- Alert management
- Employee lookup
- System metrics
        ↓
Frontend Admin
- Login
- Dashboard
- Live monitor
- Alert review
- Reports
        ↓
Report / Benchmark / Audit
```

---

## 17. Phase 12: Backend API production

### Mục tiêu

Dựng backend làm trung tâm điều phối hệ thống, không để frontend đọc file log trực tiếp.

### Công nghệ đề xuất

```text
FastAPI
Postgres
Qdrant client
JWT auth
Pydantic schema
Uvicorn
```

### Cấu trúc đề xuất

```text
backend/
├── main.py
├── config.py
├── auth/
│   ├── router.py
│   ├── service.py
│   └── security.py
├── cameras/
│   ├── router.py
│   └── service.py
├── alerts/
│   ├── router.py
│   └── service.py
├── employees/
│   ├── router.py
│   └── service.py
├── metrics/
│   ├── router.py
│   └── service.py
└── database/
    ├── postgres.py
    └── qdrant.py
```

### API tối thiểu

```text
POST /auth/login
GET  /auth/me

GET  /cameras
POST /cameras
PATCH /cameras/{camera_id}

GET  /alerts
GET  /alerts/{event_id}
PATCH /alerts/{event_id}/status

GET  /employees
GET  /employees/{employee_id}

GET  /system/health
GET  /system/metrics
```

### Điều kiện qua phase

- [x] Login trả JWT.
- [x] API đọc được danh sách alerts.
- [x] API đọc được snapshot path hoặc snapshot URL.
- [x] API kiểm tra health Postgres/Qdrant.
- [x] API có CORS cho frontend.

### Trạng thái triển khai

```text
Backend: FastAPI
Entry: backend/main.py
Auth: backend/auth/router.py, backend/auth/security.py
Alerts: backend/alerts/router.py
Employees: backend/employees/router.py
System health: backend/system/router.py
Database helper: backend/database/postgres.py
Dependencies: fastapi, uvicorn, PyJWT, httpx
Status: compile OK, TestClient OK
```

Test đã chạy:

```text
GET /system/health → {'status': 'ok', 'postgres': True, 'qdrant': True}
POST /auth/login admin/<password-from-env-or-export> → 200
GET /auth/me → {'username': 'admin'}
GET /employees → 56 records
GET /alerts → []
```

Lệnh chạy backend:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

---

## 18. Phase 13: Production database schema

### Mục tiêu

Chuyển từ JSONL log sang schema Postgres chính thức để dashboard và báo cáo truy vấn ổn định.

### Bảng đề xuất

```text
camera_sources
unknown_events
alert_snapshots
alert_rules
system_metrics
audit_logs
```

### Schema tối thiểu: unknown_events

```text
id
 event_id
 camera_id
 track_id
 status
 label
 best_score
 best_match_employee_id
 best_match_name
 warning_type
 warning_level
 zone
 bbox
 snapshot_full
 snapshot_face
 created_at
 reviewed_at
 reviewed_by
 review_status
 note
```

### Điều kiện qua phase

- [x] Có migration hoặc script tạo bảng.
- [x] AlertManager ghi được vào Postgres.
- [x] Vẫn giữ JSONL làm fallback debug nếu cần.
- [x] Có index theo `created_at`, `camera_id`, `warning_level`, `review_status`.

### Trạng thái triển khai

```text
Script: scripts/init_event_schema.py
Tables:
- camera_sources
- alert_rules
- unknown_events
- system_metrics
- audit_logs
Seed data:
- camera_sources: webcam_0
- alert_rules: 5 rules
Backend API added:
- GET /cameras
- GET /rules
Status: schema init OK, API test OK
```

Verify đã chạy:

```text
camera_sources: 1
alert_rules: 5
unknown_events: 0
system_metrics: 0
audit_logs: 0
GET /cameras → webcam_0
GET /rules → 5 rules
```

---

## 19. Phase 14: Frontend Admin + Login

### Mục tiêu

Có giao diện để admin giám sát, xem cảnh báo, xem snapshot và kiểm tra hệ thống.

### Trang cần có

```text
/login
/dashboard
/cameras
/alerts
/alerts/:event_id
/employees
/settings/rules
/reports
```

### Dashboard tối thiểu

```text
- Tổng số cảnh báo hôm nay
- Unknown mới nhất
- Cảnh báo theo mức Low / Medium / High / Critical
- Camera online/offline
- FPS hiện tại
- Latency pipeline
```

### Trang alert detail

```text
- Full frame snapshot
- Face crop snapshot
- Camera ID
- Time
- Track ID
- Status
- Best match gần nhất
- Score
- Warning type
- Warning level
- Review status
- Note của admin
```

### Điều kiện qua phase

- [x] Login/logout hoạt động ở frontend static.
- [x] Dashboard gọi backend API.
- [x] Xem được danh sách alerts.
- [ ] Xem được chi tiết alert + snapshot.
- [ ] Admin cập nhật trạng thái review được.

### Trạng thái triển khai

```text
Frontend type: static HTML/CSS/JS
Files:
- frontend/index.html
- frontend/styles.css
- frontend/app.js
API base: http://localhost:8000
Auth: JWT lưu localStorage
Views hiện có:
- Login
- Dashboard metrics
- Alerts list
- Cameras list
- Rules list
- Employees list
Status: frontend skeleton created, cần chạy backend + mở browser để test UI thật
```

Cách chạy backend:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Cách mở frontend:

```text
Mở file frontend/index.html trong browser
```

---

## 20. Phase 15: Camera Worker service

### Mục tiêu

Tách webcam script prototype thành worker chạy nền ổn định cho production.

### Pipeline worker

```text
Load camera_sources từ Postgres
        ↓
Start worker theo camera
        ↓
Read frame
        ↓
AI pipeline
        ↓
Tracking + Voting
        ↓
Rule Engine
        ↓
AlertManager ghi Postgres + snapshot
        ↓
Emit metrics
```

### Điều kiện qua phase

- [ ] Worker chạy được theo camera config.
- [x] Camera mất kết nối không làm chết toàn bộ app.
- [x] Có restart/backoff khi camera lỗi.
- [ ] Có health status cho từng camera.
- [ ] Có metrics FPS/latency theo camera.

### Trạng thái triển khai RTSP/source

```text
Updated: unknown_detection_system/run_webcam.py
Source hỗ trợ:
- Webcam index: --source 0
- RTSP URL: --source "rtsp://user:password@ip:554/path"
Camera ID: --camera-id gate_01
Reconnect: --reconnect-delay 3
Status: compile OK, cần test với RTSP thật
```

Lệnh webcam mới:

```powershell
python unknown_detection_system/run_webcam.py --camera-id webcam_0 --source 0
```

Lệnh RTSP:

```powershell
python unknown_detection_system/run_webcam.py --camera-id gate_01 --source "rtsp://user:password@192.168.1.10:554/stream1"
```

---

## 21. Phase 16: Rule Engine production

### Mục tiêu

Rule cảnh báo không hard-code trong code, mà cấu hình được từ admin/backend.

### Rule cần có

```text
stable_unknown_face
unknown_outside_working_hours
unknown_loitering_at_gate
unknown_entered_restricted_area
repeated_unknown_appearance
unverified_in_restricted_area
```

### Điều kiện qua phase

- [ ] Rule bật/tắt được.
- [ ] Threshold rule cấu hình được.
- [ ] Cooldown cấu hình được.
- [ ] Working hours cấu hình được.
- [ ] Restricted zones cấu hình được theo camera.

---

## 22. Phase 17: Benchmark và đánh giá chất lượng

### Mục tiêu

Có số liệu chứng minh hệ thống chạy được và biết giới hạn hiện tại.

### Benchmark kỹ thuật

```text
Detection latency
Recognition latency
Qdrant search latency
End-to-end latency
FPS realtime
CPU usage
RAM usage
Qdrant query time
Postgres write time
Snapshot write time
```

### Benchmark nhận diện

```text
Known accuracy
Unknown detection rate
False accept
False reject
Warning precision
Warning spam rate
Unverified rate
```

### Output cần có

```text
reports/benchmark.md
reports/benchmark_results.json
reports/sample_errors/
```

### Điều kiện qua phase

- [ ] Có script benchmark batch ảnh/video.
- [ ] Có kết quả latency trung bình/p95.
- [ ] Có bảng threshold thử nghiệm.
- [ ] Có thống kê false accept/false reject.
- [ ] Có nhận xét case yếu.

---

## 23. Phase 18: Báo cáo, sơ đồ pipeline và tài liệu mô hình

### Mục tiêu

Hoàn thiện tài liệu bàn giao giải pháp.

### Tài liệu cần có

```text
reports/final_report.md
reports/architecture.md
reports/pipeline.md
reports/model.md
reports/benchmark.md
reports/deployment.md
reports/user_guide.md
```

### Nội dung bắt buộc

```text
- Mục tiêu bài toán
- Kiến trúc hệ thống
- Sơ đồ pipeline
- Mô hình sử dụng
- Database sử dụng
- Threshold và rule cảnh báo
- Luồng Known / Unknown / Unverified
- Benchmark
- Hạn chế hiện tại
- Hướng cải thiện
- Hướng dẫn chạy setup/start/stop
```

### Mô hình sử dụng hiện tại

```text
InsightFace model pack: buffalo_l
Detection: det_10g.onnx
Recognition: w600k_r50.onnx
Runtime: onnxruntime CPUExecutionProvider
Vector DB: Qdrant employee_faces, 512-d, Cosine
Metadata DB: Postgres face_db
```

### Điều kiện qua phase

- [ ] Có sơ đồ pipeline dạng text/mermaid.
- [ ] Có báo cáo benchmark.
- [ ] Có tài liệu model.
- [ ] Có hướng dẫn vận hành.
- [ ] Có final report tổng hợp.

---

## 24. Phase 19: Deployment production

### Mục tiêu

Chuẩn hóa cách chạy hệ thống để deploy/lặp lại được.

### Thành phần cần có

```text
.env.example
docker-compose.yml
setup.sh
start.sh
stop.sh
backend Dockerfile
frontend Dockerfile
worker Dockerfile
healthcheck
log rotation
backup/restore scripts
```

### Điều kiện qua phase

- [ ] Một lệnh setup được môi trường.
- [ ] Một lệnh start chạy toàn bộ hệ thống.
- [ ] Một lệnh stop dừng an toàn.
- [ ] Healthcheck cho backend/Postgres/Qdrant/worker.
- [ ] Không hard-code secrets trong code.
- [ ] Có hướng dẫn backup/restore.

---

## 25. Cấu trúc thư mục production hiện tại

```text
phat_hien_anonymos/
├── .env                  # cấu hình local thật: DB, Qdrant, model, camera RTSP
├── .env.example          # template cấu hình không chứa secret thật
├── setup.sh              # cài dependency + import DB + init schema
├── start.sh              # start Postgres/Qdrant + verify
├── stop.sh               # stop services + release ports
├── core/
│   └── settings.py       # loader .env dùng chung
├── infra/
│   └── docker-compose.yml
├── backend/              # FastAPI admin/backend API
├── frontend/             # static admin UI skeleton
├── ai_worker/
│   ├── config.py         # bridge config từ .env vào AI pipeline
│   ├── run_webcam.py     # runner webcam/RTSP optimized
│   ├── face_pipeline.py
│   ├── tracker.py
│   ├── rule_engine.py
│   └── alert_manager.py
├── data/
│   └── exports/          # JSON exports gốc
├── storage/
│   ├── snapshots/
│   ├── logs/
│   └── debug_faces/
├── scripts/
│   ├── db/
│   ├── cameras/
│   ├── benchmark/
│   └── dev/
├── reports/
└── plan/
    └── plan.md
```

### Nguyên tắc cấu hình

- Thông tin nhạy cảm/camera/model/DB nằm trong `.env`.
- `.env.example` là template để bàn giao, không để password thật.
- Code đọc cấu hình qua `core/settings.py`.
- AI pipeline dùng `ai_worker/config.py` như bridge từ `.env`.
- Backend dùng `backend/config.py` đọc từ `.env`.

### Chạy camera bằng env

```powershell
python scripts/cameras/run_camera_from_env.py door_67b
python scripts/cameras/run_camera_from_env.py ai_pm_1
python scripts/cameras/run_camera_from_env.py ai_pm_2
```

---

## 26. Thứ tự làm ngay từ bây giờ

```text
Đã làm / đang prototype:
1. Phase 0: Khóa schema Qdrant/Postgres/manifest.
2. Phase 1: Dựng skeleton project tối thiểu.
3. Phase 2: Test Qdrant/Postgres bằng vector có sẵn.
4. Phase 3: Test InsightFace detection local.
5. Phase 4: Test InsightFace recognition local.
6. Phase 5: Nối ảnh/webcam → Known/Unknown.
7. Phase 6: Webcam realtime.
8. Phase 7A: Unknown warning bản đơn giản.
9. Phase 7: Tracking + voting đơn giản.

Nên làm tiếp để lên production:
10. Hoàn thiện Phase 8: Zone / ROI.
11. Hoàn thiện Phase 9: Rule Engine.
12. Hoàn thiện Phase 10: Ghi events vào Postgres.
13. Phase 12: Backend API production.
14. Phase 13: Production database schema.
15. Phase 14: Frontend Admin + Login.
16. Phase 15: Camera Worker service.
17. Phase 16: Rule Engine production.
18. Phase 17: Benchmark và đánh giá chất lượng.
19. Phase 18: Báo cáo, sơ đồ pipeline và tài liệu mô hình.
20. Phase 19: Deployment production.
```

Không nên gọi bản hiện tại là production. Bản hiện tại là AI core prototype đã chạy local; production cần backend/frontend/auth/admin/report/benchmark/deployment đầy đủ.
