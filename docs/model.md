# Model

Hệ thống dùng InsightFace chạy local để phát hiện và nhận diện khuôn mặt. Embedding được lưu và tìm kiếm trong Qdrant.

## Model Pack

```text
InsightFace model pack: buffalo_l
Detection model:        det_10g.onnx
Recognition model:      w600k_r50.onnx
Runtime mặc định:       onnxruntime CPUExecutionProvider
```

Nếu đổi model pack hoặc recognition model, toàn bộ embedding nhân viên trong Qdrant phải được rebuild để tránh sai lệch vector.

## Embedding Contract

| Thuộc tính | Giá trị |
|---|---|
| Vector size | `512` |
| Embedding dùng để search | `normed_embedding` |
| Vector DB | Qdrant |
| Collection | `employee_faces` |
| Distance | `Cosine` |
| Payload chính | `employee_id`, `emp_code`, `name`, `department`, `is_active` |

Embedding mới từ runtime phải tương thích với embedding đã import vào Qdrant.

## Luồng Nhận Diện

```text
Frame
  -> detect face
  -> filter by detection score and face size
  -> extract normed embedding
  -> search top-k in Qdrant
  -> compare best score with FACE_THRESHOLD
  -> return known / unknown / unverified
```

Input chính:

- Face bounding box.
- Detection score.
- Face width/height.
- 512-d embedding.
- Top-k kết quả Qdrant.

Output:

| Output | Điều kiện |
|---|---|
| `known` | Best score >= `FACE_THRESHOLD` |
| `unknown` | Quality đạt nhưng best score < `FACE_THRESHOLD` |
| `unverified` | Mặt quá nhỏ, mờ, detection score thấp hoặc thiếu dữ liệu để kết luận |

## Biến Cấu Hình Chính

```text
FACE_THRESHOLD
MIN_DETECTION_SCORE
MIN_FACE_WIDTH
MIN_FACE_HEIGHT
TOP_K
DEFAULT_AI_INTERVAL
UNKNOWN_ALERT_COOLDOWN_SECONDS
```

## Thay Đổi An Toàn

Có thể tuning sau benchmark:

- `FACE_THRESHOLD`
- `MIN_DETECTION_SCORE`
- `MIN_FACE_WIDTH`
- `MIN_FACE_HEIGHT`
- `DEFAULT_AI_INTERVAL`
- Rule/cooldown trong `alert_rules`

Mỗi lần tuning nên ghi lại benchmark để so sánh.

## Thay Đổi Rủi Ro Cao

Cần rebuild hoặc kiểm thử lại toàn bộ:

- Đổi model pack.
- Đổi recognition model.
- Đổi embedding normalization.
- Đổi Qdrant distance.
- Đổi vector size.
- Đổi logic quality gate.

## Benchmark Khuyến Nghị

Dataset:

```text
data/benchmark/known/
data/benchmark/unknown/
data/benchmark/hard_cases/
```

Chạy benchmark:

```powershell
python scripts/benchmark/benchmark_pipeline.py --input data/benchmark
```

Chỉ nên chốt threshold production sau khi có:

- Known accuracy.
- Unknown detection rate.
- False accept rate.
- False reject rate.
- Unverified rate.
- Latency p50/p95.

## Checklist Trước Khi Đổi Threshold Production

- Dataset benchmark có đủ nhân viên thật và người lạ thật.
- Có hard cases: góc nghiêng, ánh sáng yếu, khẩu trang, motion blur.
- Qdrant collection đang dùng đúng model pack.
- So sánh trước/sau bằng cùng dataset.
- Smoke test ít nhất một camera active.
- Theo dõi alert volume sau khi deploy.
