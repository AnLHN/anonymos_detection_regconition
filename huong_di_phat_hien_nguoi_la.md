# Hướng đi triển khai hệ thống phát hiện người lạ chạy InsightFace local và Qdrant

## 1. Mục tiêu bài toán

Hệ thống sẽ chạy **InsightFace trực tiếp trên máy của mình** để xử lý camera/video local. Không cần train lại model, chỉ dùng các model có sẵn của InsightFace cho hai phần chính:

- **Face detection**: phát hiện khuôn mặt trong frame.
- **Face recognition**: trích xuất embedding khuôn mặt để so khớp.
- Truy vấn database Qdrant để so khớp người đã đăng ký.
- Hiển thị người đã biết bằng **khung xanh + tên trong database**.
- Hiển thị người lạ bằng **khung đỏ + nhãn Unknown**.
- Xây dựng cơ chế cảnh báo khi người lạ có hành vi đáng ngờ, ví dụ:
  - Xuất hiện ngoài giờ làm việc.
  - Lảng vảng ở khu vực cổng.
  - Đi vào khu vực hạn chế.
  - Xuất hiện nhiều lần trong một khoảng thời gian ngắn.
- Khi có cảnh báo, hệ thống sẽ:
  - Chụp lại ảnh người lạ.
  - Lưu log sự kiện.
  - Gửi cảnh báo lên giao diện hoặc hệ thống thông báo.

---

## 2. Định hướng tổng thể

Hướng làm chính:

> Không train model mới, chạy model InsightFace local trên máy của mình, dùng detection để lấy bbox khuôn mặt và recognition để lấy embedding, sau đó query Qdrant để phân loại Known / Unknown rồi đưa vào Rule Engine phát hiện người lạ đáng nghi.

Model nguồn tham khảo:

- Detection: `https://github.com/deepinsight/insightface/tree/master/detection`
- Recognition: `https://github.com/deepinsight/insightface/tree/master/recognition`

Luồng tổng thể:

```text
Camera / Video Stream
        ↓
InsightFace local detection
        ↓
Crop / align face
        ↓
InsightFace local recognition
        ↓
Nhận embedding khuôn mặt
        ↓
Query Qdrant database
        ↓
Lấy top-1 hoặc top-k kết quả gần nhất
        ↓
So sánh score với threshold
        ↓
Known / Unknown / Unverified
        ↓
Hiển thị bounding box
        ↓
Rule Engine kiểm tra điều kiện cảnh báo
        ↓
Lưu snapshot + log + warning
```

---

## 3. Kiến trúc hệ thống đề xuất

```text
┌───────────────────────┐
│ Camera / RTSP / Video │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Frame Capture         │
│ OpenCV                │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ InsightFace Detection │
│ chạy local            │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ InsightFace Recognition│
│ chạy local, extract emb│
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Qdrant Vector Search  │
│ Search employee DB    │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Recognition Decision  │
│ Known / Unknown       │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Tracking + Voting     │
│ Reduce false alert    │
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Rule Engine           │
│ Time + Zone + Behavior│
└───────────┬───────────┘
            ↓
┌───────────────────────┐
│ Alert + Snapshot + Log│
└───────────────────────┘
```

---

## 4. Các trạng thái cần phân biệt

Không nên chỉ chia thành 2 trạng thái Known / Unknown. Nên chia thành 3 trạng thái:

| Trạng thái | Ý nghĩa | Hiển thị |
|---|---|---|
| `Known` | Người đã có trong database, score vượt threshold | Khung xanh + tên |
| `Unknown` | Có mặt rõ nhưng không khớp ai trong database | Khung đỏ + Unknown |
| `Unverified` | Không đủ điều kiện nhận diện: mặt mờ, nhỏ, quay lưng, che mặt | Khung vàng/xám + Unverified |

Lý do cần có `Unverified`:

- Nếu không thấy rõ mặt thì không nên kết luận chắc chắn là người lạ.
- Trạng thái này giúp giảm cảnh báo sai.
- Có thể dùng thêm rule riêng: nếu `Unverified` vào khu vực cấm hoặc ngoài giờ thì cảnh báo mức trung bình.

---

## 5. Logic nhận diện Known / Unknown

### 5.1. Input

- Frame từ camera/video.
- Bbox khuôn mặt từ InsightFace detection chạy local.
- Face crop hoặc aligned face.
- Embedding từ InsightFace recognition chạy local.
- Database Qdrant chứa embedding nhân viên.

### 5.2. Output

- `status`: Known / Unknown / Unverified.
- `name`: tên nhân viên hoặc Unknown.
- `score`: điểm tương đồng.
- `employee_id`: mã nhân viên nếu có.
- `bbox`: tọa độ khuôn mặt.
- `camera_id`: camera phát hiện.
- `timestamp`: thời gian phát hiện.

### 5.3. Logic cơ bản

```python
if face_quality_is_low:
    status = "unverified"
elif best_score >= FACE_THRESHOLD:
    status = "known"
    label = employee_name
    box_color = "green"
else:
    status = "unknown"
    label = "Unknown"
    box_color = "red"
```

### 5.4. Threshold ban đầu

Có thể thử ban đầu:

```python
FACE_THRESHOLD = 0.55  # hoặc 0.60
```

Tuy nhiên threshold không nên chọn cố định theo cảm tính. Cần test trên dữ liệu camera thật của công ty.

Gợi ý cách chọn threshold:

| Trường hợp | Ý nghĩa |
|---|---|
| Threshold thấp | Dễ nhận nhầm người lạ thành nhân viên |
| Threshold cao | Dễ nhận nhầm nhân viên thành người lạ |
| Threshold phù hợp | Cân bằng giữa false accept và false reject |

Nên thu dữ liệu test gồm:

- Ảnh nhân viên từ camera thật.
- Ảnh người ngoài không có trong database.
- Ảnh nhân viên ở nhiều góc khác nhau.
- Ảnh trong điều kiện thiếu sáng, ngược sáng, đi nhanh.

---

## 6. Vai trò của Qdrant

Qdrant được dùng làm vector database để lưu và truy vấn embedding khuôn mặt.

### 6.1. Dữ liệu trong Qdrant cần có

Mỗi vector nên có payload dạng:

```json
{
  "employee_id": "EMP001",
  "name": "Nguyen Van A",
  "department": "IT",
  "role": "Staff",
  "image_path": "employees/EMP001.jpg"
}
```

### 6.2. Điều kiện bắt buộc

Cần đảm bảo:

- Embedding trong Qdrant và embedding mới phải được tạo từ cùng model recognition của InsightFace.
- Nếu đổi model recognition local, phải tạo lại embedding trong Qdrant bằng đúng model đó.
- Cùng số chiều vector, ví dụ 512 chiều.
- Cùng cách normalize vector.
- Cùng metric search, ví dụ cosine similarity.
- Payload có đủ thông tin để hiển thị tên người.

### 6.3. Query Qdrant

Luồng query:

```text
Embedding mới
   ↓
Qdrant search top-1 hoặc top-5
   ↓
Lấy kết quả có score cao nhất
   ↓
So sánh với threshold
```

Ban đầu có thể dùng `top_k = 1`. Sau đó nếu muốn debug tốt hơn thì dùng `top_k = 5` để biết Unknown đang gần giống những ai.

---

## 7. Không cảnh báo ngay khi thấy Unknown

Một lỗi rất thường gặp là vừa phát hiện Unknown đã cảnh báo ngay. Điều này dễ gây spam và báo sai.

Nên chia thành 2 tầng:

```text
Tầng 1: Unknown Detection
Tầng 2: Suspicious Unknown Warning
```

Có nghĩa là:

- `Unknown` thông thường: chỉ vẽ khung đỏ.
- `Unknown + điều kiện đáng ngờ`: mới cảnh báo.

Ví dụ:

```text
Unknown xuất hiện trong giờ làm việc ở khu vực bình thường
→ Chỉ hiển thị khung đỏ

Unknown xuất hiện ngoài giờ làm việc
→ Warning

Unknown đứng ở cổng quá lâu
→ Warning

Unknown đi vào khu vực hạn chế
→ Warning
```

---

## 8. Rule Engine cảnh báo

Rule Engine là module quyết định khi nào cần cảnh báo.

### 8.1. Rule 1: Người lạ xuất hiện ngoài giờ làm việc

Ví dụ giờ làm việc:

```text
08:00 - 17:30
```

Logic:

```python
if status == "unknown" and not is_working_hour(current_time):
    warning_type = "unknown_outside_working_hours"
    level = "high"
```

Thông báo mẫu:

```text
WARNING: Người lạ xuất hiện ngoài giờ làm việc
Camera: gate_01
Time: 20:42:11
Status: Unknown
```

---

### 8.2. Rule 2: Người lạ lảng vảng ở cổng

Điều kiện:

```text
Unknown đứng trong vùng cổng hơn 10 giây
```

Logic:

```python
if status == "unknown" and zone == "gate" and track_duration >= 10:
    warning_type = "unknown_loitering_at_gate"
    level = "medium"
```

Cần có tracking để biết đây là cùng một người đang đứng lâu, không phải nhiều người khác nhau.

---

### 8.3. Rule 3: Người lạ vào khu vực hạn chế

Ví dụ khu vực hạn chế:

- Phòng server.
- Kho hàng.
- Khu vực tài sản.
- Hành lang nội bộ.
- Cửa sau.
- Bãi xe sau giờ làm.

Logic:

```python
if status == "unknown" and zone in RESTRICTED_ZONES:
    warning_type = "unknown_entered_restricted_area"
    level = "critical"
```

---

### 8.4. Rule 4: Người lạ xuất hiện nhiều lần trong thời gian ngắn

Ví dụ:

```text
Unknown xuất hiện >= 3 lần trong 5 phút
```

Logic:

```python
if unknown_count_in_5_minutes >= 3:
    warning_type = "repeated_unknown_appearance"
    level = "medium"
```

---

### 8.5. Rule 5: Unverified nhưng xuất hiện ở vùng nhạy cảm

Trường hợp không thấy rõ mặt nhưng người đó xuất hiện ở vùng quan trọng:

```python
if status == "unverified" and zone in RESTRICTED_ZONES:
    warning_type = "unverified_person_in_restricted_area"
    level = "medium"
```

---

## 9. Cấp độ cảnh báo đề xuất

| Điều kiện | Mức cảnh báo |
|---|---|
| Unknown xuất hiện bình thường trong giờ làm | Low |
| Unknown đứng ở cổng quá 10 giây | Medium |
| Unknown xuất hiện ngoài giờ làm việc | High |
| Unknown vào khu vực hạn chế | Critical |
| Unknown + ngoài giờ + khu vực hạn chế | Critical |
| Unverified vào khu vực hạn chế | Medium |

---

## 10. Tracking và Voting

### 10.1. Vì sao cần tracking?

Nếu xử lý từng frame riêng lẻ, hệ thống có thể cảnh báo liên tục:

```text
Frame 1: Unknown
Frame 2: Unknown
Frame 3: Unknown
Frame 4: Unknown
```

Điều này gây spam cảnh báo. Tracking giúp gom các frame thuộc cùng một người thành một `track_id`.

### 10.2. Tracking ID

Ví dụ:

```text
Track ID 12:
- Frame 1: Unknown
- Frame 2: Unknown
- Frame 3: Known: Nguyen Van A
- Frame 4: Known: Nguyen Van A
- Frame 5: Unknown
```

Sau khi voting:

```text
Track ID 12 = Nguyen Van A
```

### 10.3. Voting theo nhiều frame

Không nên kết luận bằng 1 frame. Nên dùng nhiều frame.

Ví dụ:

```text
Trong 30 frame:
- 22 frame nhận là Nguyen Van A
- 8 frame unknown

Kết luận: Nguyen Van A
```

Hoặc:

```text
Trong 30 frame:
- 25 frame unknown
- 0 frame known đủ threshold

Kết luận: Unknown
```

### 10.4. Gợi ý rule voting

```python
if known_count >= 5 and best_known_score >= FACE_THRESHOLD:
    final_status = "known"
elif unknown_count >= 10 and known_count == 0:
    final_status = "unknown"
else:
    final_status = "unverified"
```

---

## 11. Khu vực giám sát bằng ROI / Zone

Cần định nghĩa các vùng quan trọng trong camera.

Ví dụ:

```text
gate_zone
door_zone
server_room_zone
warehouse_zone
parking_zone
restricted_zone
```

Có thể định nghĩa bằng polygon:

```python
zones = {
    "gate": [(100, 200), (500, 200), (520, 600), (80, 600)],
    "restricted_area": [(600, 100), (900, 100), (900, 500), (600, 500)]
}
```

Kiểm tra người có nằm trong vùng hay không bằng điểm trung tâm bbox:

```python
center_x = (x1 + x2) / 2
center_y = (y1 + y2) / 2
```

Nếu điểm trung tâm nằm trong polygon thì xem như người đó đang ở vùng tương ứng.

---

## 12. Snapshot và Log

Khi có cảnh báo, hệ thống nên lưu:

- Ảnh full frame.
- Ảnh crop face.
- Ảnh crop person nếu có person detection.
- Thời gian.
- Camera ID.
- Track ID.
- Zone.
- Status.
- Best match gần nhất.
- Best score.
- Loại cảnh báo.
- Mức cảnh báo.

Ví dụ log:

```json
{
  "event_id": "EVT_20260519_204211_001",
  "track_id": 15,
  "camera_id": "gate_01",
  "time": "2026-05-19 20:42:11",
  "zone": "gate",
  "status": "unknown",
  "best_match_name": "Nguyen Van A",
  "best_score": 0.38,
  "warning_type": "unknown_outside_working_hours",
  "warning_level": "high",
  "snapshot_full": "snapshots/unknown/EVT_20260519_204211_001_full.jpg",
  "snapshot_face": "snapshots/unknown/EVT_20260519_204211_001_face.jpg"
}
```

---

## 13. Cấu trúc thư mục gợi ý

```text
unknown_detection_system/
├── main.py
├── config.py
├── insightface_detector.py
├── insightface_recognizer.py
├── qdrant_service.py
├── recognition.py
├── tracker.py
├── zone_manager.py
├── rule_engine.py
├── alert_manager.py
├── logger_service.py
├── utils/
│   ├── image_utils.py
│   ├── time_utils.py
│   └── geometry_utils.py
├── snapshots/
│   ├── unknown/
│   ├── unverified/
│   └── warnings/
├── logs/
│   └── events.jsonl
└── README.md
```

---

## 14. File config đề xuất

```python
# config.py

INSIGHTFACE_DETECTION_MODEL = "<local-detection-model>"
INSIGHTFACE_RECOGNITION_MODEL = "<local-recognition-model>"
INSIGHTFACE_DEVICE = "cuda"  # hoặc "cpu" nếu máy không có GPU

QDRANT_HOST = "<qdrant-ip>"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "employees_face"

FACE_THRESHOLD = 0.60

MIN_FACE_WIDTH = 60
MIN_FACE_HEIGHT = 60
MIN_DETECTION_SCORE = 0.75

WORKING_HOUR_START = "08:00"
WORKING_HOUR_END = "17:30"

LOITERING_SECONDS = 10
UNKNOWN_COUNT_WINDOW_SECONDS = 300
UNKNOWN_COUNT_THRESHOLD = 3

RESTRICTED_ZONES = [
    "server_room",
    "warehouse",
    "restricted_area"
]
```

---

## 15. Phase triển khai chi tiết

## Phase 0: Chuẩn bị môi trường chạy InsightFace local

### Mục tiêu

Máy của mình chạy được model InsightFace local cho detection và recognition.

### Việc cần làm

- Cài môi trường Python, OpenCV, InsightFace và runtime phù hợp.
- Chọn backend chạy model: GPU nếu có CUDA, CPU nếu không có GPU.
- Tải hoặc cấu hình model detection từ InsightFace.
- Tải hoặc cấu hình model recognition từ InsightFace.
- Chạy thử detection trên một ảnh mặt.
- Chạy thử recognition để lấy embedding.
- Kiểm tra Qdrant đang chạy ở đâu.
- Kiểm tra collection trong Qdrant tên gì.
- Kiểm tra vector size.
- Kiểm tra metric đang dùng: cosine, dot hoặc euclidean.
- Kiểm tra payload trong Qdrant có tên nhân viên chưa.

### Output

- Máy local detect được khuôn mặt.
- Máy local extract được embedding.
- Có thông tin Qdrant.
- Biết collection, vector size, metric.
- Biết payload có những trường nào.

### Checklist

- [ ] InsightFace detection chạy local thành công.
- [ ] InsightFace recognition chạy local thành công.
- [ ] Embedding trả về đúng chiều.
- [ ] Kết nối được tới Qdrant.
- [ ] Query thử một embedding thành công.
- [ ] Lấy được tên nhân viên từ payload.
- [ ] Biết threshold tạm thời để test.

---

## Phase 1: Kết nối InsightFace local và Qdrant

### Mục tiêu

Máy của mình tự detect mặt, tự extract embedding bằng InsightFace local, sau đó query database Qdrant.

### Việc cần làm

- Viết `insightface_detector.py` để detect khuôn mặt trong ảnh/frame.
- Viết `insightface_recognizer.py` để lấy embedding từ face crop/aligned face.
- Viết `qdrant_service.py` để query embedding.
- Lấy top-1 hoặc top-5 match.
- In ra kết quả match gồm:
  - employee_id
  - name
  - score

### Output

Có script test:

```text
Input: ảnh gốc
Output:
- Face bbox
- Best match
- Name
- Score
- Known / Unknown
```

### Checklist

- [ ] Detect được mặt từ ảnh gốc.
- [ ] Crop/align face đúng.
- [ ] Extract embedding local đúng chiều.
- [ ] Query Qdrant thành công.
- [ ] Lấy được top result.
- [ ] So sánh được với threshold.
- [ ] In ra Known / Unknown.

---

## Phase 2: Nhận diện Known / Unknown trên ảnh tĩnh

### Mục tiêu

Test nhận diện người quen / người lạ trên ảnh trước khi chạy realtime.

### Việc cần làm

- Chuẩn bị ảnh nhân viên.
- Chuẩn bị ảnh người lạ.
- Viết module `recognition.py`.
- Kiểm tra chất lượng mặt:
  - Face size.
  - Detection score.
  - Blur nếu cần.
- Nếu match vượt threshold thì Known.
- Nếu không vượt threshold thì Unknown.
- Nếu ảnh không đủ chất lượng thì Unverified.

### Output

Kết quả cho mỗi ảnh:

```text
Image: test_001.jpg
Status: Known
Name: Nguyen Van A
Score: 0.72
```

Hoặc:

```text
Image: unknown_001.jpg
Status: Unknown
Best candidate: Tran Van B
Score: 0.41
```

### Checklist

- [ ] Nhận diện ảnh nhân viên đúng.
- [ ] Ảnh người lạ trả về Unknown.
- [ ] Ảnh mờ/nhỏ trả về Unverified.
- [ ] Có log kết quả test.
- [ ] Có thống kê threshold sơ bộ.

---

## Phase 3: Chạy realtime camera và vẽ bounding box

### Mục tiêu

Xử lý video/camera realtime và hiển thị kết quả.

### Việc cần làm

- Mở camera RTSP hoặc webcam bằng OpenCV.
- Detect face trong từng frame bằng InsightFace detection local.
- Crop/align face.
- Extract embedding bằng InsightFace recognition local.
- Query Qdrant.
- Vẽ bounding box:
  - Known: khung xanh + tên.
  - Unknown: khung đỏ + Unknown.
  - Unverified: khung vàng/xám + Unverified.
- Hiển thị score nếu cần debug.

### Output

Giao diện realtime có:

```text
[Green box] Nguyen Van A - 0.72
[Red box] Unknown - 0.38
[Yellow box] Unverified
```

### Checklist

- [ ] Camera chạy ổn định.
- [ ] Bounding box hiển thị đúng.
- [ ] Known hiển thị tên từ DB.
- [ ] Unknown hiển thị khung đỏ.
- [ ] Không chạy detection/recognition quá dày gây lag.
- [ ] FPS ở mức chấp nhận được.

---

## Phase 4: Thêm Tracking và Voting

### Mục tiêu

Giảm cảnh báo sai và tránh spam cảnh báo theo từng frame.

### Việc cần làm

- Tích hợp tracking.
- Gán `track_id` cho mỗi người/khuôn mặt.
- Lưu lịch sử nhận diện theo từng `track_id`.
- Voting nhiều frame để quyết định final status.
- Chỉ cảnh báo khi track đã ổn định.

### Output

Mỗi người trong video có một track riêng:

```text
Track ID 12:
Status: Known
Name: Nguyen Van A
Score avg: 0.68
```

Hoặc:

```text
Track ID 15:
Status: Unknown
Unknown frames: 20
Duration: 12 seconds
```

### Checklist

- [ ] Có track_id cho từng người.
- [ ] Không cảnh báo lặp liên tục mỗi frame.
- [ ] Voting giúp giảm nhầm Known thành Unknown.
- [ ] Track duration được tính đúng.
- [ ] Unknown chỉ được xác nhận sau nhiều frame.

---

## Phase 5: Xây dựng Zone / ROI

### Mục tiêu

Biết người lạ đang ở khu vực nào để áp dụng rule cảnh báo.

### Việc cần làm

- Định nghĩa polygon cho từng vùng.
- Viết `zone_manager.py`.
- Kiểm tra bbox center có nằm trong vùng nào.
- Gán zone cho từng track.

### Output

Mỗi track có zone:

```json
{
  "track_id": 15,
  "status": "unknown",
  "zone": "gate",
  "duration": 12
}
```

### Checklist

- [ ] Định nghĩa được vùng cổng.
- [ ] Định nghĩa được vùng hạn chế.
- [ ] Detect đúng người đang ở zone nào.
- [ ] Có thể cấu hình zone theo từng camera.
- [ ] Có thể bật/tắt rule theo zone.

---

## Phase 6: Xây dựng Rule Engine cảnh báo

### Mục tiêu

Cảnh báo khi Unknown có điều kiện đáng ngờ.

### Việc cần làm

- Viết `rule_engine.py`.
- Kiểm tra rule ngoài giờ.
- Kiểm tra rule lảng vảng ở cổng.
- Kiểm tra rule vào khu vực cấm.
- Kiểm tra rule xuất hiện nhiều lần.
- Gán warning level.

### Output

Sự kiện cảnh báo:

```text
[HIGH] Unknown person outside working hours
Camera: gate_01
Zone: gate
Time: 20:42:11
```

### Checklist

- [ ] Unknown trong giờ làm không bị cảnh báo quá mức.
- [ ] Unknown ngoài giờ có warning.
- [ ] Unknown đứng lâu ở cổng có warning.
- [ ] Unknown vào vùng cấm có warning.
- [ ] Có phân cấp Low / Medium / High / Critical.
- [ ] Không spam cảnh báo liên tục.

---

## Phase 7: Snapshot, Log và Dashboard

### Mục tiêu

Lưu lại bằng chứng và hiển thị cảnh báo.

### Việc cần làm

- Viết `alert_manager.py`.
- Khi có warning:
  - Lưu full frame.
  - Lưu face crop.
  - Lưu person crop nếu có.
  - Ghi log vào JSONL/database.
- Hiển thị danh sách cảnh báo trên dashboard.
- Có thể gửi Telegram/Email nếu cần.

### Output

Thư mục snapshot:

```text
snapshots/
├── unknown/
│   └── UNK_20260519_204211_face.jpg
└── warnings/
    └── EVT_20260519_204211_full.jpg
```

Log sự kiện:

```json
{
  "event_id": "EVT_20260519_204211_001",
  "camera_id": "gate_01",
  "track_id": 15,
  "status": "unknown",
  "zone": "gate",
  "warning_type": "unknown_outside_working_hours",
  "warning_level": "high",
  "snapshot_full": "snapshots/warnings/EVT_20260519_204211_full.jpg"
}
```

### Checklist

- [ ] Có lưu ảnh khi warning.
- [ ] Có log đầy đủ thông tin.
- [ ] Có thể xem lại cảnh báo.
- [ ] Có thể debug score và best match.
- [ ] Có thể xuất báo cáo nếu cần.

---

## Phase 8: Test, đánh giá và tinh chỉnh

### Mục tiêu

Đánh giá hệ thống trong môi trường thật và giảm lỗi.

### Việc cần làm

- Test với nhân viên thật.
- Test với người không có trong database.
- Test trong giờ làm.
- Test ngoài giờ làm.
- Test ở cổng.
- Test ở khu vực hạn chế.
- Test ánh sáng yếu.
- Test mặt nghiêng, đeo khẩu trang, đi nhanh.
- Điều chỉnh threshold.
- Điều chỉnh thời gian loitering.
- Điều chỉnh rule warning.

### Chỉ số đánh giá

| Chỉ số | Ý nghĩa |
|---|---|
| Known accuracy | Tỉ lệ nhận đúng nhân viên |
| Unknown detection rate | Tỉ lệ phát hiện đúng người lạ |
| False accept | Người lạ bị nhận nhầm thành nhân viên |
| False reject | Nhân viên bị nhận nhầm thành Unknown |
| Warning precision | Cảnh báo có đúng không |
| Warning spam rate | Có bị cảnh báo quá nhiều không |
| Processing FPS | Tốc độ xử lý realtime |

### Checklist

- [ ] Test đủ nhân viên.
- [ ] Test đủ người lạ.
- [ ] Có bảng kết quả threshold.
- [ ] Có thống kê lỗi.
- [ ] Tinh chỉnh rule cảnh báo.
- [ ] Chạy thử ổn định trong nhiều giờ.

---

## 16. Pseudocode tổng thể

```python
for frame in camera_stream:
    faces = detect_faces(frame)

    for face in faces:
        face_crop = crop_face(frame, face.bbox)

        if not is_good_quality_face(face):
            status = "unverified"
            label = "Unverified"
            score = None
        else:
            aligned_face = insightface_detector.align(frame, face)
            embedding = insightface_recognizer.extract_embedding(aligned_face)
            search_result = qdrant_service.search(embedding, top_k=5)

            best_match = search_result[0]
            best_score = best_match.score

            if best_score >= FACE_THRESHOLD:
                status = "known"
                label = best_match.payload["name"]
            else:
                status = "unknown"
                label = "Unknown"

        track_id = tracker.update(face.bbox)

        tracker.update_recognition_history(
            track_id=track_id,
            status=status,
            label=label,
            score=score
        )

        final_status = tracker.get_voted_status(track_id)

        zone = zone_manager.get_zone(face.bbox)

        warning = rule_engine.check(
            track_id=track_id,
            status=final_status,
            zone=zone,
            current_time=now(),
            duration=tracker.get_duration(track_id)
        )

        if warning.should_alert:
            alert_manager.save_snapshot(
                frame=frame,
                face_crop=face_crop,
                track_id=track_id,
                warning=warning
            )

            alert_manager.write_log(
                track_id=track_id,
                status=final_status,
                zone=zone,
                warning=warning
            )

        draw_box(
            frame=frame,
            bbox=face.bbox,
            label=label,
            status=final_status
        )
```

---

## 17. Roadmap ngắn gọn

```text
Phase 0: Chuẩn bị môi trường InsightFace local
Phase 1: Kết nối InsightFace local + Qdrant
Phase 2: Nhận diện Known / Unknown trên ảnh tĩnh
Phase 3: Chạy realtime camera + bounding box
Phase 4: Thêm tracking + voting
Phase 5: Thêm zone / ROI
Phase 6: Thêm rule engine cảnh báo
Phase 7: Lưu snapshot + log + dashboard
Phase 8: Test thực tế + tinh chỉnh threshold/rule
```

---

## 18. Kết luận

Hướng triển khai hợp lý nhất là xây hệ thống theo mô hình:

```text
InsightFace local detection + InsightFace local recognition + Qdrant DB + Unknown Detection + Rule Engine + Snapshot/Log
```

Trong đó:

- Người có trong database: hiển thị khung xanh và tên.
- Người không có trong database: hiển thị khung đỏ và Unknown.
- Người không đủ chất lượng nhận diện: hiển thị Unverified.
- Unknown chỉ cảnh báo khi có điều kiện đáng ngờ:
  - Ngoài giờ làm việc.
  - Lảng vảng ở cổng.
  - Vào khu vực hạn chế.
  - Xuất hiện nhiều lần.

Điểm quan trọng nhất khi triển khai thực tế:

- Không cảnh báo chỉ dựa trên 1 frame.
- Cần tracking và voting theo nhiều frame.
- Cần chọn threshold bằng dữ liệu camera thật.
- Cần lưu log và snapshot để debug.
- Cần tách rõ nhận diện và cảnh báo thành hai module riêng.

---

## 19. Plan dựng hệ thống theo từng phase

Phần này là plan triển khai thực tế để dựng hệ thống từ dữ liệu hiện có. Mục tiêu là đi từng phase nhỏ, mỗi phase có output kiểm chứng được trước khi qua phase tiếp theo.

### Dữ liệu hiện có

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

### Pipeline tổng thể cần dựng

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

### Phase 0: Khóa schema và dữ liệu nền

#### Mục tiêu

Hiểu chắc dữ liệu Postgres, Qdrant và manifest trước khi viết pipeline xử lý ảnh.

#### Việc cần làm

- Đọc `manifest_20260521T080719Z.json` để xác nhận bộ export.
- Đọc schema Postgres, tập trung trước vào bảng `employees`.
- Đọc schema Qdrant, tập trung trước vào collection `employee_faces`.
- Xác nhận mapping giữa Qdrant payload và Postgres:
  - `payload.employee_id` ↔ `employees.id`
  - `payload.emp_code` ↔ `employees.emp_code`
  - `payload.name` ↔ `employees.name`
- Xác nhận vector size là `512` và distance là `Cosine`.
- Xác nhận chỉ dùng nhân viên `is_active = true` khi nhận diện.

#### Output cần có

```text
Data contract:
- employee_id lấy từ Qdrant payload
- name lấy từ Qdrant payload hoặc join Postgres employees
- vector size bắt buộc 512
- metric bắt buộc Cosine
```

#### Điều kiện qua phase

- [ ] Biết collection Qdrant chính xác: `employee_faces`.
- [ ] Biết bảng Postgres chính xác: `employees`.
- [ ] Biết key mapping giữa Qdrant và Postgres.
- [ ] Không còn mơ hồ embedding mới phải có shape bao nhiêu.

---

### Phase 1: Dựng project skeleton tối thiểu

#### Mục tiêu

Tạo bộ khung code nhỏ, chưa xử lý realtime, chỉ đủ để test từng module độc lập.

#### Cấu trúc đề xuất

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

#### Pipeline trong phase này

```text
Config
  ↓
Load Qdrant/Postgres connection info
  ↓
Load InsightFace model config
  ↓
Chạy từng script test độc lập
```

#### Điều kiện qua phase

- [ ] Có `config.py` chứa tên collection, threshold, device, model path/name.
- [ ] Có module Qdrant service nhưng chỉ search thử, chưa nối camera.
- [ ] Có module Postgres service nhưng chỉ lookup nhân viên, chưa ghi log.
- [ ] Có module detector/recognizer nhưng chưa realtime.

---

### Phase 2: Kết nối và kiểm thử Qdrant/Postgres trước

#### Mục tiêu

Đảm bảo phần DB hoạt động đúng trước khi đụng model ảnh.

#### Pipeline kiểm thử

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

#### Output mong muốn

```text
Query vector id: 7
Top 1:
- employee_id: 7
- emp_code: NV011
- name: Hoàng Mạnh Tiến
- score: gần 1.0 nếu search bằng chính vector gốc
```

#### Điều kiện qua phase

- [ ] Query Qdrant thành công.
- [ ] Top-1 trả về đúng nhân viên khi dùng vector gốc.
- [ ] Payload có đủ `employee_id`, `emp_code`, `name`.
- [ ] Lookup Postgres theo `employee_id` thành công nếu cần.

---

### Phase 3: Chạy InsightFace detection local trên ảnh tĩnh

#### Mục tiêu

Máy local detect được khuôn mặt ổn định trước khi recognition.

#### Pipeline

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

#### Output mong muốn

```text
Image: test_employee.jpg
Faces detected: 1
Face 1:
- bbox: [x1, y1, x2, y2]
- det_score: 0.92
- quality: pass
```

#### Điều kiện qua phase

- [ ] Detect được mặt trên ảnh nhân viên rõ.
- [ ] Không nhận mặt quá nhỏ/mờ nếu dưới ngưỡng.
- [ ] Lưu được ảnh debug bbox để nhìn bằng mắt.
- [ ] Biết FPS detection tạm thời trên máy local.

---

### Phase 4: Chạy InsightFace recognition local và kiểm tra embedding

#### Mục tiêu

Từ bbox đã detect, extract được embedding 512 chiều đúng chuẩn.

#### Pipeline

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

#### Output mong muốn

```text
Embedding shape: (512,)
Embedding norm: ~1.0 nếu đã normalize
```

#### Điều kiện qua phase

- [ ] Extract được embedding từ ảnh rõ mặt.
- [ ] Embedding có đúng 512 chiều.
- [ ] Cách normalize thống nhất với dữ liệu trong Qdrant.
- [ ] Nếu embedding search sai hoàn toàn, dừng lại kiểm tra model recognition có trùng model tạo DB không.

---

### Phase 5: Nối recognition local với Qdrant để phân loại Known/Unknown

#### Mục tiêu

Ảnh tĩnh đi hết pipeline từ ảnh gốc đến Known/Unknown.

#### Pipeline

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

#### Logic quyết định

```python
if face_quality_is_low:
    status = "unverified"
elif best_score >= FACE_THRESHOLD:
    status = "known"
else:
    status = "unknown"
```

#### Output mong muốn

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

#### Điều kiện qua phase

- [ ] Ảnh nhân viên trong DB có thể ra Known.
- [ ] Ảnh người ngoài DB có thể ra Unknown.
- [ ] Ảnh mờ/nhỏ ra Unverified.
- [ ] Có log top-k để debug threshold.

---

### Phase 6: Chạy video/camera nhưng chưa cảnh báo

#### Mục tiêu

Đưa pipeline ảnh tĩnh vào video realtime, chỉ vẽ bbox và label, chưa Rule Engine.

#### Pipeline

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

#### Điều kiện qua phase

- [ ] Camera hoặc video chạy ổn định.
- [ ] Không crash khi không có mặt.
- [ ] Không lag quá mức do chạy recognition mỗi frame.
- [ ] Có thể cấu hình xử lý mỗi N frame.
- [ ] Label và màu bbox đúng.

---

### Phase 7: Thêm tracking và voting

#### Mục tiêu

Không kết luận người lạ dựa trên một frame đơn lẻ.

#### Pipeline

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

#### Rule voting ban đầu

```python
if known_count >= 5 and best_known_score >= FACE_THRESHOLD:
    final_status = "known"
elif unknown_count >= 10 and known_count == 0:
    final_status = "unknown"
else:
    final_status = "unverified"
```

#### Điều kiện qua phase

- [ ] Mỗi người có `track_id` ổn định.
- [ ] Không nhấp nháy Known/Unknown liên tục.
- [ ] Unknown chỉ được xác nhận sau nhiều frame.
- [ ] Có duration theo track.

---

### Phase 8: Thêm Zone / ROI

#### Mục tiêu

Biết người lạ đang ở khu vực nào để phục vụ cảnh báo.

#### Pipeline

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

#### Điều kiện qua phase

- [ ] Cấu hình được zone theo camera.
- [ ] Vẽ được polygon zone lên frame debug.
- [ ] Track được gán đúng zone.
- [ ] Có zone mặc định là `none` nếu không nằm trong vùng nào.

---

### Phase 9: Thêm Rule Engine cảnh báo

#### Mục tiêu

Chỉ cảnh báo khi Unknown có điều kiện đáng ngờ, không spam khi vừa thấy Unknown.

#### Pipeline

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

#### Rule ban đầu

```text
Rule 1: Unknown ngoài giờ làm việc → High
Rule 2: Unknown đứng ở cổng quá N giây → Medium
Rule 3: Unknown vào restricted zone → Critical
Rule 4: Unknown xuất hiện nhiều lần trong M phút → Medium
Rule 5: Unverified vào restricted zone → Medium
```

#### Điều kiện qua phase

- [ ] Unknown bình thường trong giờ làm không spam cảnh báo.
- [ ] Unknown ngoài giờ có warning.
- [ ] Unknown ở vùng cấm có warning.
- [ ] Có cooldown theo `track_id` và `warning_type`.

---

### Phase 10: Snapshot, log và tích hợp Postgres

#### Mục tiêu

Khi có warning, lưu bằng chứng để xem lại và debug.

#### Pipeline

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

#### Dữ liệu log tối thiểu

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

#### Điều kiện qua phase

- [ ] Có snapshot full frame.
- [ ] Có snapshot face crop.
- [ ] Có JSONL log đọc lại được.
- [ ] Không ghi Postgres trực tiếp cho đến khi schema event ổn định.

---

### Phase 11: Test thực tế và khóa threshold

#### Mục tiêu

Chọn threshold và rule bằng dữ liệu camera thật, không chọn theo cảm tính.

#### Pipeline đánh giá

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

#### Chỉ số cần theo dõi

```text
Known accuracy
Unknown detection rate
False accept
False reject
Warning precision
Warning spam rate
Processing FPS
```

#### Điều kiện hoàn tất bản dựng đầu tiên

- [ ] Có threshold tạm ổn trên dữ liệu camera thật.
- [ ] FPS đủ dùng trên máy local.
- [ ] Warning không spam.
- [ ] Snapshot/log đủ để truy vết lỗi.
- [ ] Biết rõ các case yếu: thiếu sáng, mặt nghiêng, khẩu trang, motion blur.

---

### Thứ tự làm ngay từ bây giờ

```text
1. Phase 0: Khóa schema Qdrant/Postgres/manifest.
2. Phase 1: Dựng skeleton project tối thiểu.
3. Phase 2: Test Qdrant/Postgres bằng vector có sẵn.
4. Phase 3: Test InsightFace detection local trên ảnh tĩnh.
5. Phase 4: Test InsightFace recognition local và embedding 512 chiều.
6. Phase 5: Nối ảnh tĩnh → Known/Unknown.
```

Không nên nhảy thẳng vào realtime camera trước khi Phase 2 đến Phase 5 chạy ổn, vì nếu kết quả sai sẽ rất khó biết lỗi nằm ở model, embedding, threshold hay database.
