# Kế hoạch pipeline tracker-first detection + recognition

## Mục tiêu

Thiết kế lại AI camera pipeline theo hướng:

- Chỉ đọc camera và chạy model một lần trên mỗi frame cần xử lý.
- Cùng một kết quả detect/embedding được tách thành 2 nhánh logic:
  - Nhánh tracker: chấp nhận detect score thấp hơn, vì mục tiêu là bám đối tượng liên tục.
  - Nhánh recognition/alert: dùng điều kiện chất lượng cao hơn để kết luận known/unknown.
- Một người lạ đứng lâu trong camera chỉ tạo 1 cảnh báo theo `track_id`, không spam.
- Nếu track đã bị báo là unknown nhưng về sau được nhận diện là người quen, hệ thống cần resolve/suppress cảnh báo đó.

## Điểm cần lưu ý quan trọng

Nếu muốn tracker thấy được mặt có score `0.4`, detector thực tế phải chạy với threshold thấp `0.4`.

Không thể để InsightFace detector threshold `0.85` rồi mong tracker có bbox `0.4`, vì mặt dưới `0.85` đã bị model/provider lọc từ đầu.

Vì vậy pipeline mới nên có 2 threshold riêng:

```text
TRACK_DETECTION_SCORE = 0.40
RECOGNITION_DETECTION_SCORE = 0.85
FACE_THRESHOLD = 0.28
MIN_FACE_WIDTH = 40
MIN_FACE_HEIGHT = 40
```

Ý nghĩa:

- `TRACK_DETECTION_SCORE=0.40`: ngưỡng đầu vào của detector/model, dùng để lấy bbox cho tracker.
- `RECOGNITION_DETECTION_SCORE=0.85`: ngưỡng chất lượng để được phép đưa vào logic known/unknown.
- `FACE_THRESHOLD=0.28`: ngưỡng so khớp vector để kết luận người quen.
- `MIN_FACE_WIDTH/HEIGHT=40`: mặt nhỏ hơn thì chỉ track, không kết luận recognition.

## Pipeline mong muốn

```text
RTSP frame
  -> FaceAnalysis/InsightFace get(frame) với det_thresh = 0.40
  -> tạo danh sách face detections
  -> tất cả face det_score >= 0.40 được đưa vào tracker
  -> chỉ face đạt recognition quality mới query Qdrant và decide known/unknown
  -> gán recognition decision vào track
  -> track state điều khiển alert/suppress/resolve
  -> publish bbox + track label ra Redis meta/live UI
```

Vẫn là 1 lần model trên frame. Không tạo 2 worker, không đọc 2 stream, không chạy detect 2 lần.

## Phân loại kết quả trên từng face

### 1. Tracking candidate

Điều kiện:

```text
face.det_score >= TRACK_DETECTION_SCORE
```

Nếu đạt:

- Có bbox.
- Được đưa vào `CentroidTracker.update`.
- Track có thể hiện box trên live UI.
- Chưa chắc là known/unknown.

### 2. Recognition eligible

Điều kiện:

```text
face.det_score >= RECOGNITION_DETECTION_SCORE
face_width >= 40
face_height >= 40
```

Nếu không đạt:

- Track vẫn tiếp tục bám.
- Recognition status nên là `tracking_only` hoặc `unverified`.
- Không query Qdrant để tiết kiệm và tránh kết luận sai.
- Không tính là unknown để tạo alert.

Nếu đạt:

- Query Qdrant bằng embedding của face.
- Nếu best candidate active và `score >= FACE_THRESHOLD`, gán track là `known`.
- Nếu không có candidate hoặc score `< FACE_THRESHOLD`, gán track là `unknown_candidate`.

## Track state để tránh spam

Nên mở rộng `Track` để có state riêng thay vì chỉ vote history:

```python
identity_status: "tracking" | "known" | "unknown" | "unverified"
identity_label: str | None
identity_score: float | None
unknown_alert_sent: bool
unknown_alert_event_id: str | None
last_recognition_at: float
last_seen_at: float
```

Flow:

1. Track mới sinh ra từ bbox `det >= 0.4`.
2. Track ban đầu là `tracking`.
3. Mỗi khi có face recognition eligible:
   - Nếu known: set `identity_status = "known"`, gán label/score.
   - Nếu unknown: tăng bộ đếm unknown stable cho track.
4. Chỉ khi unknown ổn định mới tạo alert.
5. Sau khi tạo alert, set `unknown_alert_sent = True`.
6. Track đó đứng lâu vẫn không tạo thêm alert cùng rule, vì đã có `unknown_alert_sent` hoặc cooldown theo `track_id`.
7. Nếu track sau đó thành known:
   - Không tạo unknown alert nữa.
   - Nếu đã có alert cũ, resolve/suppress alert đó.

## Cách resolve alert nếu track về sau thành known

Có 2 hướng:

### Hướng an toàn hơn: auto resolve

Thêm trạng thái/note cho alert thay vì xóa vật lý:

```text
review_status = "resolved_known"
note = "Auto resolved: track later recognized as <name>"
```

Ưu điểm:

- Giữ audit trail.
- Vẫn xem lại được tại sao lúc đầu bị báo unknown.
- Ít rủi ro mất dữ liệu cảnh báo.

### Hướng dùng soft delete

Nếu muốn UI biến mất khỏi danh sách mặc định:

```text
deleted_at = now()
deleted_by = "system"
delete_reason = "Auto removed: track later recognized as known"
```

Ưu điểm:

- Không hiện thông báo nữa.

Nhược điểm:

- Cần đảm bảo audit log rõ ràng để tránh cảm giác mất dữ liệu.

Khuyến nghị: dùng `resolved_known` trước. Nếu UI cần gọn, filter `resolved_known` khỏi danh sách mặc định.

## Thay đổi code dự kiến

### 1. `ai_worker/config.py`

Thêm threshold riêng:

```python
TRACK_DETECTION_SCORE = get_float("TRACK_DETECTION_SCORE", 0.4)
RECOGNITION_DETECTION_SCORE = get_float("RECOGNITION_DETECTION_SCORE", 0.85)
FACE_THRESHOLD = get_float("FACE_THRESHOLD", 0.28)
MIN_FACE_WIDTH = get_int("MIN_FACE_WIDTH", 40)
MIN_FACE_HEIGHT = get_int("MIN_FACE_HEIGHT", 40)
```

`MIN_DETECTION_SCORE` hiện tại nên đổi tên hoặc dùng lại thành `RECOGNITION_DETECTION_SCORE` để tránh nhầm.

### 2. `ai_worker/insightface_recognizer.py`

InsightFace `FaceAnalysis.prepare(det_thresh=...)` nên dùng:

```python
det_thresh=TRACK_DETECTION_SCORE
```

Lý do: cần lấy bbox score thấp cho tracker.

### 3. `ai_worker/recognition_decision.py`

Tách `is_good_quality_face` thành:

```python
def is_trackable_face(face):
    return face.det_score >= TRACK_DETECTION_SCORE

def is_recognition_quality_face(face):
    return (
        face.det_score >= RECOGNITION_DETECTION_SCORE
        and width >= MIN_FACE_WIDTH
        and height >= MIN_FACE_HEIGHT
    )
```

`decide_recognition` chỉ query/decide known/unknown khi `is_recognition_quality_face` đạt.

### 4. `ai_worker/face_pipeline.py`

Hiện tại pipeline query Qdrant cho mọi face được recognizer trả về. Nên sửa thành:

```text
for face in faces:
  if not is_trackable_face(face):
    skip
  if not is_recognition_quality_face(face):
    recognition = tracking_only/unverified
    qdrant not called
  else:
    qdrant search
    decide known/unknown
  append FacePipelineResult
```

Cần thêm field để biết kết quả nào chỉ để tracking:

```python
FacePipelineResult(
  face=face,
  recognition=recognition,
  trackable=True,
  recognition_eligible=True/False,
)
```

### 5. `ai_worker/tracker.py`

Tracker vẫn update bằng tất cả `FacePipelineResult` có `trackable=True`.

Nhưng track state không nên xem `unverified/tracking_only` là unknown. Chỉ recognition eligible và kết luận unknown mới được tính vào unknown stable counter.

Cần thêm helper:

```python
track.apply_recognition(result)
track.is_known()
track.is_unknown_stable()
track.should_alert_unknown()
track.mark_unknown_alert_sent(event_id)
track.resolve_as_known(label, score)
```

### 6. `ai_worker/unknown_event_detector.py`

Chỉ alert khi:

```text
track.identity_status == "unknown"
track.unknown_alert_sent == False
track unknown stable enough
not redis cooldown
```

Sau khi alert:

```text
track.unknown_alert_sent = True
track.unknown_alert_event_id = event_id
```

Nếu track thành known:

```text
if track.unknown_alert_event_id:
    resolve alert
```

Có thể cần tách thêm service:

```text
AlertResolutionService.resolve_unknown_as_known(event_id, employee_name, score)
```

### 7. `ai_worker/alert_manager.py`

Khi tạo unknown event, trả về `event_id` và cho tracker lưu:

```python
event = alert_manager.save_unknown_warning(...)
track.mark_unknown_alert_sent(event["event_id"])
```

### 8. Database/API

Nếu dùng resolve thay vì delete, cần thêm hoặc tận dụng field:

```text
review_status = "resolved_known"
note = "Auto resolved by recognition"
```

Nếu status enum không ràng buộc DB thì có thể dùng luôn.

Frontend alert list nên ẩn `resolved_known` mặc định nếu user muốn chỉ xem cảnh báo đang cần xử lý.

## Bổ sung từ file đánh giá pipeline

File [Danh_gia_pipeline_Face_Recognition.md](/home/ntcai/anonymos_detection_regconition/Danh_gia_pipeline_Face_Recognition.md) không xung đột với kế hoạch này. Nội dung đó nên được xem là lớp cải tiến production phía trên thiết kế tracker-first.

Tóm lại:

- Kế hoạch hiện tại xử lý phần kiến trúc lõi: 2 luồng logic, 1 lần model, tracker trước, recognition sau.
- File đánh giá bổ sung các lớp nâng chất lượng: face quality, best face cache, voting, stable theo thời gian, unknown re-id cache.

Nếu thêm các đề xuất đó vào plan hiện tại, pipeline đầy đủ nên thành:

```text
Camera
  -> InsightFace Detect/Embedding 1 lần với det_thresh thấp cho tracker
  -> Tracking candidate filter
  -> Tracker / Track State
  -> Face Quality Filter
  -> Best Face Cache theo track
  -> Recognition eligible filter
  -> Qdrant Search
  -> Recognition Voting / Confidence Accumulation
  -> Identity State
  -> Unknown Stable theo thời gian
  -> Alert Manager
  -> Resolve Manager
  -> Unknown Re-identification Cache
  -> Redis / API / UI
```

### 1. Tách min face size theo mục đích

Camera hiện tại là 1280x720, nên `40x40` cho recognition là hợp lý. Không cần tăng lên `60x60` như camera 1080p/4K.

Nên tách cấu hình:

```env
TRACK_MIN_FACE_SIZE=30
RECOGNITION_MIN_FACE_SIZE=40
BEST_FACE_MIN_SIZE=60
```

Ý nghĩa:

- `TRACK_MIN_FACE_SIZE=30`: mặt đủ để tạo/bám track.
- `RECOGNITION_MIN_FACE_SIZE=40`: mặt đủ để được phép nhận diện.
- `BEST_FACE_MIN_SIZE=60`: mặt ưu tiên để lưu best face/best embedding cho track.

### 2. Face Quality không chỉ dựa vào detection score

Recognition không nên chỉ dựa vào `det_score`.

Nên thêm quality score tổng hợp:

```text
quality = f(det_score, face_size, blur, brightness, pose, occlusion)
```

Các tín hiệu nên có:

- Blur: ảnh mặt bị mờ thì không query Qdrant hoặc giảm trọng số.
- Pose: mặt nghiêng quá nhiều thì không kết luận known/unknown vội.
- Brightness: mặt quá tối/quá cháy sáng thì bỏ qua recognition.
- Occlusion: che khẩu trang, quay lưng, che mặt thì chỉ track.

Kết quả:

- Face quality thấp: tracker vẫn bám, recognition bỏ qua.
- Face quality tốt: được phép query Qdrant và update identity state.

### 3. Best Face Cache theo track

Mỗi `Track` nên lưu:

```python
best_face: FaceEmbedding | None
best_embedding: list[float] | None
best_quality: float
best_face_updated_at: float
```

Khi frame mới có chất lượng tốt hơn:

```text
if current_quality > track.best_quality:
    update best_face / best_embedding / best_quality
```

Lợi ích:

- Khi người tiến lại gần camera, hệ thống dùng face tốt nhất để nhận diện.
- Giảm trường hợp frame đầu hơi mờ làm track bị unknown sớm.
- Có thể dùng best face để resolve unknown về known sau này.

### 4. Unknown stable nên theo giây thay vì số frame

Hiện tại plan dùng `UNKNOWN_STABLE_FRAMES`. Với nhiều camera/FPS khác nhau, số frame dễ lệch.

Nên đổi sang:

```env
UNKNOWN_STABLE_SECONDS=1.5
```

Logic:

```text
track.identity_status == unknown_candidate
and now - track.unknown_first_seen_at >= UNKNOWN_STABLE_SECONDS
```

Lợi ích:

- Camera 20 FPS và 25 FPS cho hành vi cảnh báo tương đương.
- Ít phụ thuộc vào Model FPS.
- Dễ tune theo cảm giác vận hành: "người lạ xuất hiện ổn định 1.5 giây".

### 5. Recognition Voting / Confidence Accumulation

Không nên kết luận known chỉ từ một frame đơn nếu muốn ổn định hơn.

Ví dụ history:

```text
Known
Known
Unknown
Known
Known
```

Kết luận cuối nên là `known`.

Có thể dùng một trong hai cách:

#### Majority voting

```text
track.identity_votes = last N recognition decisions
identity_status = most common stable status
```

#### Confidence accumulation

```text
known_score_accumulator[label] += qdrant_score * quality
unknown_score_accumulator += unknown_quality
```

Khuyến nghị giai đoạn đầu: majority voting dễ làm và ít rủi ro hơn.

### 6. Unknown Re-identification Cache

Nếu cùng một người lạ ra khỏi camera rồi quay lại sau vài chục giây, track mới có thể sinh alert mới. Để giảm spam, nên cache unknown embedding.

Cache có thể lưu:

```python
unknown_embedding
event_id
camera_id
created_at
expires_at
```

Khi track unknown mới xuất hiện:

```text
compare best_embedding với unknown cache gần đây
if similarity >= UNKNOWN_REID_THRESHOLD and not expired:
    reuse/suppress previous event_id
    do not create new alert
```

Cấu hình gợi ý:

```env
UNKNOWN_REID_TTL_SECONDS=60
UNKNOWN_REID_THRESHOLD=0.35
```

Lưu ý: threshold này phải benchmark riêng, vì embedding người lạ không có nhãn chuẩn như employee.

### 7. Tracker: Centroid trước, ByteTrack sau

Centroid Tracker hiện tại đủ tốt để triển khai bước đầu, nhất là phòng họp/văn phòng ít người.

Nếu môi trường đông người, nhiều crossing/occlusion, nên nâng cấp:

- ByteTrack: khuyến nghị đầu tiên.
- DeepSORT: nếu muốn dùng appearance feature.
- BoT-SORT: mạnh hơn nhưng phức tạp hơn.

Kế hoạch triển khai nên làm theo 2 phase:

1. Giữ `CentroidTracker`, thêm track state + best face + voting.
2. Khi logic identity ổn rồi mới thay tracker bằng ByteTrack.

Không nên đổi tracker cùng lúc với đổi identity logic, vì khó debug.

### 8. Track state mở rộng sau khi thêm các cải tiến

Track state đầy đủ nên là:

```python
class Track:
    track_id: int
    bbox: tuple[int, int, int, int]

    best_face: FaceEmbedding | None
    best_embedding: list[float] | None
    best_quality: float

    identity_status: str
    identity_label: str | None
    identity_score: float | None
    identity_confidence: float
    identity_votes: deque

    unknown_first_seen_at: float | None
    unknown_alert_sent: bool
    unknown_alert_event_id: str | None

    last_seen_at: float
    last_recognition_at: float
```

### 9. Thứ tự triển khai khuyến nghị

Nên triển khai theo thứ tự này để dễ kiểm soát:

1. Tách threshold: `TRACK_DETECTION_SCORE` và `RECOGNITION_DETECTION_SCORE`.
2. Cho detector chạy threshold thấp, nhưng recognition filter threshold cao.
3. Thêm `recognition_eligible` vào `FacePipelineResult`.
4. Mở rộng `Track` với `identity_status`, `unknown_alert_sent`, `unknown_alert_event_id`.
5. Đổi unknown stable từ frame sang giây.
6. Thêm best face cache.
7. Thêm recognition voting.
8. Thêm resolve unknown -> known.
9. Thêm unknown re-id cache.
10. Sau cùng mới cân nhắc ByteTrack.

## State machine để dễ test

```text
tracking
  -> recognition eligible + known score >= 0.28
       -> known

tracking
  -> recognition eligible + not known
       -> unknown_candidate
       -> unknown stable N frames
       -> unknown_alerted

unknown_alerted
  -> later known
       -> known_resolved
       -> resolve previous alert

tracking/unverified
  -> low det / small face only
       -> keep tracking, no alert
```

## Test cases cần có

1. Face det `0.45`, size lớn:
   - Có bbox/tracker.
   - Không query Qdrant.
   - Không alert.

2. Face det `0.86`, size `50x50`, Qdrant score `0.30`:
   - Track becomes known.
   - UI hiện tên người quen.
   - Không alert unknown.

3. Face det `0.86`, size `50x50`, Qdrant score `0.20`:
   - Track becomes unknown candidate.
   - Sau stable frames tạo 1 alert.
   - Đứng trong camera 5 phút không spam alert cùng track.

4. Face lúc đầu unknown, sau đó quay mặt rõ hơn và score `0.31`:
   - Track becomes known.
   - Alert cũ được `resolved_known` hoặc soft deleted.
   - Sidebar notification không tiếp tục báo unknown cho track đó.

5. Mặt nhỏ `30x30`, det `0.92`:
   - Có thể track nếu đạt `0.4`.
   - Không recognition.
   - Không unknown alert.

6. Người ra khỏi khung rồi quay lại sau khi track cũ hết `max_missed`:
   - Tạo track mới.
   - Có thể alert lại nếu vẫn unknown, vì đây là lần xuất hiện mới.

## Cấu hình để dễ tune

Nên đưa các threshold vào `.env.example`:

```env
TRACK_DETECTION_SCORE=0.55
RECOGNITION_DETECTION_SCORE=0.85
FACE_THRESHOLD=0.28
TRACK_MIN_FACE_SIZE=40
RECOGNITION_MIN_FACE_SIZE=40
BEST_FACE_MIN_SIZE=60
UNKNOWN_STABLE_SECONDS=1.5
UNKNOWN_ALERT_COOLDOWN_SECONDS=300
UNKNOWN_REID_TTL_SECONDS=60
UNKNOWN_REID_THRESHOLD=0.35
```

Ghi chú:

- Tăng `TRACK_DETECTION_SCORE` nếu box tracker quá nhiều/nhiều false positive.
- Giảm `TRACK_DETECTION_SCORE` nếu tracker hay mất người.
- Tăng `RECOGNITION_DETECTION_SCORE` nếu nhận diện sai do mặt xấu.
- Giảm `FACE_THRESHOLD` sẽ dễ pass known hơn, nhưng tăng rủi ro nhận nhầm.
- Tăng `UNKNOWN_STABLE_SECONDS` để bớt cảnh báo người lạ thoáng qua.
- Tăng `UNKNOWN_REID_TTL_SECONDS` nếu muốn cùng một người lạ quay lại trong thời gian dài hơn vẫn không tạo alert mới.

## Kết luận

Thiết kế này đúng với ý tưởng "2 luồng logic, 1 lần model":

- Model/detector chỉ chạy một lần.
- Tracker được cấp bbox rộng hơn với detect score thấp.
- Recognition chỉ quyết định khi mặt đủ chất lượng.
- Track giữ identity state để không spam unknown.
- Unknown alert có thể được resolve nếu sau đó track được nhận diện là known.
- Các bổ sung từ file đánh giá giúp pipeline tiến gần production hơn: best face, face quality, voting, stable theo thời gian, re-id cache.
