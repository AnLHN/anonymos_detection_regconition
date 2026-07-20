# Kế hoạch triển khai tracker-first recognition pipeline theo từng phase

## Mục tiêu triển khai

Triển khai pipeline theo hướng:

- Chỉ chạy InsightFace một lần trên mỗi frame AI xử lý.
- Dùng ngưỡng thấp để tracker bám mặt/người ổn định.
- Dùng ngưỡng cao hơn + quality filter để quyết định nhận diện.
- Unknown alert bám theo `track_id`, không spam khi người đứng lâu.
- Nếu unknown về sau được nhận diện thành known thì resolve cảnh báo cũ.

File thiết kế nền:

- [tracker_first_recognition_pipeline_plan.md](/home/ntcai/anonymos_detection_regconition/plan/tracker_first_recognition_pipeline_plan.md)
- [Danh_gia_pipeline_Face_Recognition.md](/home/ntcai/anonymos_detection_regconition/Danh_gia_pipeline_Face_Recognition.md)

## Nguyên tắc triển khai

- Không đổi quá nhiều tầng trong cùng một phase.
- Sau mỗi phase phải chạy được worker realtime.
- Sau mỗi phase phải có test/validation nhỏ để biết lỗi nằm ở đâu.
- Không thay ByteTrack ngay từ đầu; giữ CentroidTracker cho đến khi identity logic ổn.
- Không xóa dữ liệu alert vật lý ở phase đầu; ưu tiên `resolved_known` hoặc soft-delete có audit.

## Trạng thái triển khai

- 2026-07-01: Đã chạy benchmark camera thật 5 phút sau triển khai.
- 2026-07-01: Đã triển khai Phase 1.
- 2026-07-01: Đã triển khai lõi Phase 2.
- 2026-07-01: Đã thêm field nền của Phase 3 vào `FacePipelineResult`.
- 2026-07-01: Đã triển khai Phase 4 ở mức track identity state; alert vẫn giữ vote/stable-frame cũ cho đến Phase 5.
- 2026-07-01: Đã triển khai Phase 5 cho rule `stable_unknown_face`: stable theo giây và không bắn lại khi track đã có unknown alert.
- 2026-07-01: Đã triển khai Phase 6: unknown alert được auto resolve thành `resolved_known` khi cùng track đủ vote known.
- 2026-07-01: Đã triển khai Phase 7: thêm face quality filter nhẹ bằng size/detection/blur/brightness.
- 2026-07-01: Đã triển khai Phase 8: track lưu best face/best embedding/best quality.
- 2026-07-01: Đã triển khai Phase 9: known identity dùng majority vote trong cửa sổ gần nhất.
- 2026-07-01: Đã triển khai Phase 10: unknown re-id cache bằng Redis để giảm alert lặp khi cùng unknown quay lại nhanh.
- 2026-07-01: Phase 11 đã triển khai ByteTrack bằng `supervision.ByteTrack`, có fallback CentroidTracker nếu dependency không khả dụng.
- 2026-07-01: Đã hoàn thiện Phase 3 contract runtime: backend forward `identity_status`, `unknown_alert_sent`, `unknown_alert_event_id`; frontend type đã khai báo các field mới.
- 2026-07-01: Đã sửa `read_fps`/Resize FPS từ đo tức thời sang rolling window 5 giây và clamp theo FPS RTSP để tránh số ảo.
- 2026-07-01: Bổ sung kế hoạch Phase 12-15 cho landmark-based face quality/pose gate. Mục tiêu là xử lý mặt cúi, xoay, che khuất mà không cần thay model recognition hiện tại.

## Benchmark 5 phút sau triển khai

- `ai_pm_1`: RTSP 25.0 FPS, Model trung bình 24.22 FPS, latency trung bình 22.90 ms, track trung bình 2.02.
- `ai_pm_2`: RTSP 25.0 FPS, Model trung bình 24.17 FPS, latency trung bình 25.97 ms, track trung bình 0.25.
- `door_67B`: RTSP 20.0 FPS, Model trung bình 19.64 FPS, latency trung bình 8.94 ms, track trung bình 0.00.
- Sau khi sửa `read_fps`, mẫu nhanh xác nhận Resize ổn quanh `25/25/20 FPS`, không còn spike `700-1400 FPS`.

## Phase 0 - Chốt cấu hình và baseline hiện tại

### Mục tiêu

Ghi nhận trạng thái hiện tại trước khi sửa pipeline để có điểm so sánh.

### Việc cần làm

- Ghi lại FPS hiện tại của từng camera:
  - `RTSP`
  - `Resize`
  - `Model`
  - `ai_latency_ms`
- Ghi lại số lượng:
  - known tracks
  - unknown/unverified tracks
  - unknown alerts tạo trong 5-10 phút
- Chụp log worker hiện tại:
  - model provider
  - det threshold
  - recognition threshold
  - min face size

### File liên quan

- `.runtime/worker.log`
- `ai_worker/config.py`
- `ai_worker/camera_worker.py`
- `frontend/src/components/LiveMonitor.tsx`

### Tiêu chí pass

- Có baseline trước khi sửa.
- Biết rõ worker đang chạy threshold nào.
- Dashboard live vẫn chạy bình thường.

## Phase 1 - Tách threshold tracker và recognition

### Mục tiêu

Tách rõ ngưỡng detect cho tracker và ngưỡng detect cho recognition.

### Cấu hình đề xuất

```env
TRACK_DETECTION_SCORE=0.55
RECOGNITION_DETECTION_SCORE=0.85
FACE_THRESHOLD=0.28
TRACK_MIN_FACE_SIZE=40
RECOGNITION_MIN_FACE_SIZE=40
BEST_FACE_MIN_SIZE=60
```

### Việc cần làm

1. Thêm config mới trong `ai_worker/config.py`:
   - `TRACK_DETECTION_SCORE`
   - `RECOGNITION_DETECTION_SCORE`
   - `TRACK_MIN_FACE_SIZE`
   - `RECOGNITION_MIN_FACE_SIZE`
   - `BEST_FACE_MIN_SIZE`
2. Cập nhật `.env.example`.
3. Tạm giữ `MIN_DETECTION_SCORE` nếu còn code cũ dùng, nhưng đánh dấu là legacy hoặc map sang `RECOGNITION_DETECTION_SCORE`.
4. Log worker phải in đủ threshold mới.

### File cần sửa

- `ai_worker/config.py`
- `.env.example`
- `ai_worker/camera_worker.py`

### Test cần chạy

```bash
.venv/bin/python -m py_compile ai_worker/config.py ai_worker/camera_worker.py
bash ./start.sh
tail -n 80 .runtime/worker.log
```

### Tiêu chí pass

- Worker log thấy:

```text
track_det=0.4 recognition_det=0.85 reco_thresh=0.28
track_min_face=30 recognition_min_face=40 best_face_min=60
```

- Chưa thay đổi behavior lớn, chỉ chuẩn bị config.

## Phase 2 - Detector chạy ngưỡng thấp, recognition tự filter lại

### Mục tiêu

InsightFace trả về nhiều bbox hơn cho tracker, nhưng recognition chỉ xử lý mặt đủ chuẩn.

### Việc cần làm

1. Trong `ai_worker/insightface_recognizer.py`, đổi `det_thresh` của `FaceAnalysis.prepare` sang `TRACK_DETECTION_SCORE`.
2. Trong `ai_worker/recognition_decision.py`, tách helper:

```python
is_trackable_face(face)
is_recognition_quality_face(face)
```

3. Đảm bảo face `det_score >= 0.4` có thể đi vào tracker.
4. Đảm bảo face không đủ `RECOGNITION_DETECTION_SCORE` hoặc size nhỏ thì không query Qdrant.

### File cần sửa

- `ai_worker/insightface_recognizer.py`
- `ai_worker/recognition_decision.py`
- `ai_worker/face_pipeline.py`

### Test cần chạy

- Unit/validation nhỏ với mock face:
  - det `0.45`, size `50x50` -> trackable, not recognition eligible.
  - det `0.86`, size `50x50` -> trackable, recognition eligible.
  - det `0.92`, size `30x30` -> trackable nếu size tracking đạt, not recognition eligible.

### Tiêu chí pass

- Qdrant không bị gọi cho face chỉ đủ tracking.
- Live UI có thể có box cho mặt chưa đủ recognition.
- Không tăng false unknown alert chỉ vì tracker nhận thêm bbox score thấp.

## Phase 3 - Mở rộng `FacePipelineResult`

### Mục tiêu

Mỗi kết quả face phải nói rõ nó dùng cho tracking hay recognition.

### Struct đề xuất

```python
@dataclass(frozen=True)
class FacePipelineResult:
    face: FaceEmbedding
    recognition: RecognitionResult
    trackable: bool
    recognition_eligible: bool
    quality_score: float = 0.0
```

### Việc cần làm

1. Cập nhật `FacePipelineResult`.
2. Trong `FaceRecognitionPipeline.process_image`:
   - skip face không trackable.
   - tạo `RecognitionResult(status="tracking_only")` hoặc `unverified` cho face chưa eligible.
   - chỉ query Qdrant khi `recognition_eligible=True`.
3. Cập nhật stats:
   - `detected_faces`
   - `trackable_faces`
   - `recognition_eligible_faces`
   - `known_faces`
   - `unknown_faces`
   - `unverified_faces`

### File cần sửa

- `ai_worker/face_pipeline.py`
- `ai_worker/data_contract.py` nếu cần thêm status.
- `backend/metrics.py` nếu muốn expose metrics mới.

### Test cần chạy

- Mock Qdrant service để đảm bảo Qdrant chỉ được gọi với eligible face.
- Run camera thật 2-5 phút, xem worker không lỗi.

### Tiêu chí pass

- Tracker vẫn nhận bbox.
- Recognition không chạy với mặt score thấp/size nhỏ.
- Stats không bị sai hoặc crash vì status mới.

## Phase 4 - Track identity state

### Mục tiêu

Track giữ identity state riêng, không còn chỉ vote history thô.

### Field cần thêm vào `Track`

```python
identity_status: str = "tracking"
identity_label: str | None = None
identity_score: float | None = None
identity_confidence: float = 0.0
unknown_first_seen_at: float | None = None
unknown_alert_sent: bool = False
unknown_alert_event_id: str | None = None
last_seen_at: float = 0.0
last_recognition_at: float = 0.0
```

### Việc cần làm

1. Thêm method:

```python
track.apply_pipeline_result(result, now)
track.is_known()
track.is_unknown_candidate()
track.is_unknown_stable(now)
track.mark_unknown_alert_sent(event_id)
track.resolve_as_known(label, score)
```

2. `tracking_only/unverified` không được tính là unknown.
3. Nếu result known thì track chuyển known ngay hoặc qua voting ở phase sau.
4. Nếu result unknown eligible thì bắt đầu unknown candidate.

### File cần sửa

- `ai_worker/tracker.py`
- `ai_worker/camera_worker.py`
- `ai_worker/visualization.py`

### Test cần chạy

- Test track từ unverified -> known.
- Test track từ tracking -> unknown_candidate.
- Test unverified nhiều frame không tạo unknown.

### Tiêu chí pass

- Live UI vẫn hiện track label đúng.
- Unknown không bị tạo từ face tracking-only.
- Track state không reset loạn khi cùng người đứng lâu.

## Phase 5 - Unknown stable theo thời gian

### Mục tiêu

Đổi unknown stable từ số frame sang số giây để không phụ thuộc FPS.

### Cấu hình đề xuất

```env
UNKNOWN_STABLE_SECONDS=1.5
```

### Việc cần làm

1. Thêm `UNKNOWN_STABLE_SECONDS` vào config.
2. `Track` lưu `unknown_first_seen_at`.
3. `UnknownEventDetector` chỉ alert khi:

```text
track.identity_status == "unknown"
now - track.unknown_first_seen_at >= UNKNOWN_STABLE_SECONDS
```

4. Giữ cooldown Redis theo `camera_id + warning_type + track_id`.

### File cần sửa

- `ai_worker/config.py`
- `ai_worker/tracker.py`
- `ai_worker/unknown_event_detector.py`
- `.env.example`

### Test cần chạy

- Người lạ xuất hiện dưới 1.5s -> không alert.
- Người lạ đứng trên 1.5s -> alert 1 lần.
- Người lạ đứng 5 phút -> vẫn chỉ alert 1 lần cho track đó.

### Tiêu chí pass

- Không spam alert.
- Behavior giống nhau giữa camera 20 FPS và 25 FPS.

## Phase 6 - Alert resolve khi unknown thành known

### Mục tiêu

Nếu track đã tạo unknown alert nhưng sau đó nhận diện được known, hệ thống resolve cảnh báo cũ.

### Hướng khuyến nghị

Dùng `review_status="resolved_known"` trước, chưa soft delete.

### Việc cần làm

1. Khi alert được tạo:

```python
event = alert_manager.save_unknown_warning(...)
track.mark_unknown_alert_sent(event["event_id"])
```

2. Khi track chuyển known:

```python
if track.unknown_alert_event_id:
    resolve_unknown_as_known(event_id, label, score)
```

3. Thêm service:

```text
AlertResolutionService.resolve_unknown_as_known(...)
```

4. Frontend alert list:
   - hoặc ẩn `resolved_known` mặc định.
   - hoặc hiển thị badge "Đã tự resolve".

### File cần sửa

- `ai_worker/alert_manager.py`
- `ai_worker/unknown_event_detector.py`
- `ai_worker/tracker.py`
- `ai_worker/postgres_event_service.py` hoặc service mới.
- `backend/alerts/router.py`
- `frontend/src/components/AlertsPanel.tsx`
- `frontend/src/lib/alertText.ts`

### Test cần chạy

- Tạo unknown alert.
- Sau đó mock/đưa face known vào cùng track.
- Alert cũ chuyển `resolved_known`.
- Sidebar không tiếp tục báo unknown cho track đã known.

### Tiêu chí pass

- Không mất audit.
- Không còn alert unknown active cho track đã known.

## Phase 7 - Face Quality filter

### Mục tiêu

Recognition không chỉ dựa vào detection score, mà thêm chất lượng ảnh mặt.

### Quality signals

- Face size.
- Detection score.
- Blur.
- Brightness.
- Pose nếu InsightFace trả kps/pose đủ dùng.
- Occlusion nếu có thể suy ra sơ bộ.

### Việc cần làm

1. Thêm module:

```text
ai_worker/face_quality.py
```

2. Hàm gợi ý:

```python
def compute_face_quality(frame, face) -> FaceQuality:
    ...
```

3. `FacePipelineResult` lưu `quality_score`.
4. Recognition chỉ chạy khi quality pass.

### File cần sửa

- `ai_worker/face_quality.py`
- `ai_worker/face_pipeline.py`
- `ai_worker/recognition_decision.py`

### Test cần chạy

- Ảnh blur -> không recognition.
- Ảnh tối quá -> không recognition.
- Ảnh rõ -> recognition bình thường.

### Tiêu chí pass

- Ít nhận nhầm hơn trong trường hợp mặt mờ/xấu.
- Tracker vẫn bám dù face quality thấp.

## Phase 8 - Best Face Cache theo track

### Mục tiêu

Track lưu face/embedding tốt nhất để nhận diện ổn định hơn.

### Field cần thêm

```python
best_face: FaceEmbedding | None
best_embedding: list[float] | None
best_quality: float = 0.0
best_face_updated_at: float = 0.0
```

### Việc cần làm

1. Khi có result eligible:

```python
if result.quality_score > track.best_quality:
    track.update_best_face(result)
```

2. Qdrant search có thể dùng:
   - embedding hiện tại nếu quality tốt.
   - hoặc best embedding nếu best tốt hơn.
3. Alert snapshot vẫn dùng full frame, nhưng event metadata có thể lưu `best_quality`.

### File cần sửa

- `ai_worker/tracker.py`
- `ai_worker/face_pipeline.py`
- `ai_worker/unknown_event_detector.py`

### Test cần chạy

- Người đi từ xa tới gần: best quality tăng dần.
- Track ban đầu unknown vì mặt kém, sau đó known khi best face tốt hơn.

### Tiêu chí pass

- Recognition ổn định hơn khi người tiến lại gần.
- Không query quá nhiều nếu quality không cải thiện.

## Phase 9 - Recognition voting

### Mục tiêu

Không kết luận identity chỉ từ 1 frame đơn.

### Cách đơn giản ban đầu

Majority voting trên N kết quả eligible gần nhất:

```env
RECOGNITION_VOTE_WINDOW=5
KNOWN_MIN_VOTES=2
UNKNOWN_STABLE_SECONDS=1.5
```

### Việc cần làm

1. Track lưu `identity_votes`.
2. Known cần đủ số vote hoặc confidence.
3. Unknown cần stable theo thời gian và không có known vote mạnh.

### File cần sửa

- `ai_worker/tracker.py`
- `ai_worker/recognition_decision.py`
- `ai_worker/unknown_event_detector.py`

### Test cần chạy

Chuỗi:

```text
Known, Known, Unknown, Known, Known
```

Phải ra known.

### Tiêu chí pass

- Ít nhảy known/unknown.
- Unknown alert không tạo chỉ vì 1 frame xấu.

## Phase 10 - Unknown re-identification cache

### Mục tiêu

Cùng một người lạ rời camera rồi quay lại trong thời gian ngắn thì không tạo alert mới.

### Cấu hình đề xuất

```env
UNKNOWN_REID_TTL_SECONDS=60
UNKNOWN_REID_THRESHOLD=0.35
```

### Việc cần làm

1. Khi tạo unknown alert, lưu embedding tốt nhất vào cache Redis:

```text
unknown_reid:{camera_id}:{event_id}
```

2. Khi track unknown mới ổn định, so với cache:
   - Nếu giống unknown cũ và chưa hết TTL: suppress alert mới.
   - Nếu không giống: tạo alert mới.

### File cần sửa

- `ai_worker/redis_state.py`
- `ai_worker/unknown_event_detector.py`
- `ai_worker/alert_manager.py`

### Test cần chạy

- Người lạ ra khỏi khung 10s rồi quay lại -> không alert mới.
- Người lạ khác xuất hiện -> alert mới.
- Hết TTL -> có thể alert lại.

### Tiêu chí pass

- Giảm spam khi track bị mất tạm thời.
- Không suppress nhầm người lạ khác quá nhiều.

## Phase 11 - Cân nhắc ByteTrack

### Mục tiêu

Nâng tracker nếu CentroidTracker không đủ trong môi trường đông người.

### Khi nào cần làm

- Nhiều người đi cắt nhau.
- Track ID đổi liên tục.
- Một người bị tách thành nhiều track.
- Unknown alert vẫn spam do tracker mất ID.

### Việc cần làm

1. Benchmark CentroidTracker sau phase 1-10.
2. Nếu chưa đạt, thêm ByteTrack.
3. Giữ interface `Tracker.update(results) -> tracks` để ít ảnh hưởng code còn lại.

### File cần sửa

- `ai_worker/tracker.py`
- Có thể thêm `ai_worker/bytetrack_tracker.py`
- `requirements.txt` nếu dùng thư viện ngoài.

### Tiêu chí pass

- Track ID ổn định hơn.
- Alert theo track ít spam hơn.
- Không làm latency tăng quá mạnh.

## Phase 12 - Expose landmark từ InsightFace nhưng chưa đổi quyết định

### Mục tiêu

Đưa landmark/pose signal vào contract nội bộ để đo chất lượng mặt, nhưng chưa thay đổi logic `Known/Unknown`.

Phase này chỉ quan sát, không thay behavior. Đây là lớp đệm để nếu landmark có vấn đề thì rollback dễ.

### Nguyên tắc

- Không thay model recognition.
- Không chạy thêm detector lần thứ hai.
- Dùng landmark có sẵn từ InsightFace nếu model pack trả về.
- Nếu landmark không có hoặc shape lạ, pipeline vẫn chạy bằng quality cũ.

### Field cần thêm vào `FaceEmbedding`

```python
landmark_5: list[list[float]] | None
landmark_2d_106: list[list[float]] | None
pose: tuple[float, float, float] | None
```

Ghi chú:

- `landmark_5` thường đủ để tính roll/yaw proxy cơ bản.
- `landmark_2d_106` nếu có thì dùng để đánh giá mắt, mũi, miệng tốt hơn.
- Không bắt buộc có đủ cả ba field.

### Việc cần làm

1. Inspect object `face` từ InsightFace:
   - `face.kps`
   - `face.landmark_2d_106`
   - `face.pose`
2. Cập nhật `ai_worker/insightface_recognizer.py` để copy các field có sẵn vào `FaceEmbedding`.
3. Log một dòng sample khi worker start hoặc debug:
   - có `kps` không
   - có `landmark_2d_106` không
   - có `pose` không
4. Không dùng các field này để block recognition ở phase này.

### File cần sửa

- `ai_worker/insightface_recognizer.py`
- `ai_worker/insightface_detector.py` nếu còn test/manual dùng class riêng.
- `ai_worker/tests_manual/test_detect_image.py`

### Test cần chạy

```bash
.venv/bin/python -m py_compile ai_worker/insightface_recognizer.py
PYTHONPATH=ai_worker .venv/bin/python ai_worker/tests_manual/test_detect_image.py <image>
bash ./start.sh
tail -n 120 .runtime/worker.log
```

### Tiêu chí pass

- Worker realtime vẫn chạy.
- Log/manual test xác nhận lấy được ít nhất `kps` hoặc `landmark_2d_106`.
- Không tăng latency đáng kể vì chưa thêm model mới.
- Không đổi số lượng alert/unknown vì chưa gate.

### Rollback

- Nếu InsightFace object trên máy này không có landmark field, giữ field `None`.
- Không làm fail pipeline chỉ vì thiếu landmark.

## Phase 13 - Landmark quality/pose scorer

### Mục tiêu

Tạo module riêng tính điểm mặt có đủ tốt để nhận diện không, đặc biệt cho các case:

- Cúi đầu.
- Quay ngang nhiều.
- Chỉ thấy tóc/trán/góc mặt.
- Landmark méo hoặc không cân đối.

### Module đề xuất

Thêm file:

```text
ai_worker/landmark_quality.py
```

Output:

```python
@dataclass(frozen=True)
class LandmarkQuality:
    score: float
    passed: bool
    yaw_score: float
    pitch_score: float
    roll_score: float
    visibility_score: float
    reason: str
```

### Cách tính phase đầu

Không cần pose 3D thật ngay. Dùng heuristic từ landmark:

- `roll`: độ nghiêng đường nối hai mắt.
- `yaw_proxy`: mũi lệch quá nhiều khỏi trung tâm hai mắt/miệng.
- `pitch_proxy`: khoảng cách mắt-mũi-miệng bất thường khi cúi/ngửa.
- `visibility`: landmark mắt/mũi/miệng có nằm hợp lý trong bbox không.

Nếu có `face.pose` từ InsightFace:

- Dùng `yaw/pitch/roll` trực tiếp làm tín hiệu ưu tiên.
- Vẫn giữ heuristic landmark làm fallback.

### Config đề xuất

```env
FACE_POSE_GATE_ENABLED=true
FACE_POSE_MAX_YAW=35
FACE_POSE_MAX_PITCH=30
FACE_POSE_MAX_ROLL=25
FACE_LANDMARK_MIN_SCORE=0.45
```

### File cần sửa

- `ai_worker/config.py`
- `.env.example`
- `ai_worker/landmark_quality.py`
- `ai_worker/face_quality.py`

### Test cần chạy

Tạo unit test/manual với dữ liệu giả:

- Hai mắt ngang, mũi giữa, miệng hợp lý -> pass.
- Mũi lệch nhiều -> fail yaw.
- Mắt-mũi-miệng nén bất thường -> fail pitch.
- Không có landmark -> neutral fallback hoặc fail mềm tùy config.

### Tiêu chí pass

- Hàm scorer không crash với landmark thiếu/None.
- Score dễ debug bằng `reason`.
- Chưa block recognition nếu chưa bật gate ở Phase 14.

## Phase 14 - Tích hợp landmark gate vào recognition eligibility

### Mục tiêu

Chỉ cho recognition/Qdrant chạy khi mặt đủ tốt theo cả:

- detection score
- size
- blur/brightness
- landmark/pose

Mặt cúi/xoay như ảnh thực tế sẽ giữ `Unverified`, tracker vẫn bám nhưng chưa chốt `Unknown`.

### Flow mới

```text
Face detected
  -> trackable check
  -> base quality check: size/det/blur/brightness
  -> landmark pose check
  -> nếu pass: recognition_eligible=True, query Qdrant
  -> nếu fail: recognition_eligible=False, status=Unverified
```

### Việc cần làm

1. Mở rộng `FaceQuality`:

```python
landmark_score: float
pose_passed: bool
quality_reason: str
```

2. Trong `FaceRecognitionPipeline.process_image`:
   - `recognition_eligible = base_quality.passed and landmark_quality.passed`
3. Trong `Track.latest_face_quality_text()`:
   - hiển thị ngắn lý do fail khi debug.
4. Không đưa mặt fail pose vào unknown history.

### File cần sửa

- `ai_worker/face_quality.py`
- `ai_worker/face_pipeline.py`
- `ai_worker/tracker.py`
- `ai_worker/visualization.py` nếu muốn debug overlay.

### Test cần chạy

- Ảnh mặt cúi:
  - có bbox/tracker
  - `recognition_eligible=False`
  - không Qdrant search
  - không unknown alert
- Ảnh mặt thẳng:
  - `recognition_eligible=True`
  - recognition bình thường
- Camera thật 5 phút:
  - không có `ai_pipeline_error`
  - FPS không giảm đáng kể

### Tiêu chí pass

- Người cúi đầu không bị chốt `Unknown` ngay.
- Khi người ngẩng lên, cùng track có thể chuyển `Known` hoặc `Unknown`.
- Unknown alert chỉ phát khi đã có mặt đủ chất lượng mà vẫn không match.

## Phase 15 - Runtime observability, UI và tuning landmark gate

### Mục tiêu

Cho vận hành biết vì sao một bbox đang là `Unverified`, tránh hiểu nhầm là model lỗi.

### Metadata nên publish

Trong track/runtime meta có thể thêm:

```json
{
  "quality_score": 0.62,
  "pose_passed": false,
  "quality_reason": "pitch_high",
  "recognition_eligible": false
}
```

### UI đề xuất

- Live overlay:
  - Known: tên người quen.
  - Unknown: `Unknown`.
  - Unverified: `Unverified: pose` hoặc tooltip/debug text ngắn.
- Alert detail:
  - snapshot full frame vẫn có bbox.
  - thông tin kỹ thuật có thêm `quality_reason` nếu alert được tạo.

### Metrics đề xuất

Thêm metrics:

```text
landmark_pose_failed_faces
recognition_blocked_by_pose
recognition_eligible_faces
```

### Tuning ban đầu

```env
FACE_POSE_MAX_YAW=35
FACE_POSE_MAX_PITCH=30
FACE_POSE_MAX_ROLL=25
FACE_LANDMARK_MIN_SCORE=0.45
```

Nếu bỏ sót người quen do gate quá chặt:

- tăng `FACE_POSE_MAX_YAW/PITCH/ROLL`
- giảm `FACE_LANDMARK_MIN_SCORE`

Nếu vẫn báo unknown khi mặt cúi/xoay:

- giảm `FACE_POSE_MAX_PITCH`
- tăng `FACE_LANDMARK_MIN_SCORE`

### Test cần chạy

- So sánh trước/sau trên cùng camera:
  - số `Unknown` giảm với mặt cúi/xoay
  - số `Known` khi mặt thẳng không giảm nhiều
  - FPS không tụt quá mức
- Log 20-30 sample `quality_reason` để tune threshold.

### Tiêu chí pass

- Vận hành hiểu vì sao mặt bị giữ `Unverified`.
- Alert người lạ ít false positive hơn.
- Không làm mất khả năng nhận diện khi mặt rõ.

## Checklist triển khai tổng

- [x] Phase 0: baseline hiện tại và benchmark camera thật.
- [x] Phase 1: tách config threshold.
- [x] Phase 2: detector threshold thấp, recognition filter cao.
- [x] Phase 3: mở rộng `FacePipelineResult` và runtime contract.
- [x] Phase 4: thêm track identity state.
- [x] Phase 5: unknown stable theo giây.
- [x] Phase 6: resolve unknown -> known.
- [x] Phase 7: face quality.
- [x] Phase 8: best face cache.
- [x] Phase 9: recognition voting.
- [x] Phase 10: unknown re-id cache.
- [x] Phase 11: triển khai ByteTrack.
- [ ] Phase 12: expose landmark từ InsightFace, chưa đổi behavior.
- [ ] Phase 13: thêm landmark quality/pose scorer.
- [ ] Phase 14: gate recognition/unknown bằng landmark quality.
- [ ] Phase 15: publish quality reason, UI/metrics/tuning.

## Bộ lệnh verify tối thiểu sau mỗi phase

```bash
.venv/bin/python -m py_compile ai_worker/*.py backend/**/*.py
npm run typecheck --prefix frontend
bash ./start.sh
tail -n 120 .runtime/worker.log
```

Nếu phase có frontend:

```bash
npm run typecheck --prefix frontend
```

Nếu phase có API:

```bash
curl -fsS http://127.0.0.1:8000/
```

## Tiêu chí hoàn tất toàn bộ

- Tracker có bbox ổn định từ face detect score thấp.
- Recognition chỉ chạy khi mặt đủ chuẩn.
- Known/unknown không nhảy loạn theo từng frame.
- Unknown đứng lâu chỉ alert 1 lần theo track.
- Unknown quay lại nhanh không spam nhờ re-id cache.
- Unknown về sau thành known thì alert cũ được resolve.
- Mặt cúi/xoay/che khuất giữ `Unverified`, không chốt `Unknown` khi chưa đủ chất lượng.
- Live UI hiển thị bbox/label theo track state mới.
- Không tăng latency quá mức so với baseline.
