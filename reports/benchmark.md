# Benchmark pipeline

Chưa có dữ liệu benchmark thực tế.

## Cách chạy

```powershell
python scripts/benchmark/benchmark_pipeline.py --input path\to\image_or_folder
```

Output:

```text
reports/benchmark_results.json
reports/benchmark.md
```

## Chỉ số kỹ thuật cần đo

- End-to-end latency trung bình trên mỗi ảnh.
- P50/P95 latency.
- Số face xử lý được.
- Trạng thái trả về: Known / Unknown / Unverified.

## Chỉ số chất lượng cần có dataset có nhãn

- Known accuracy.
- Unknown detection rate.
- False accept.
- False reject.
- Warning precision.
- Warning spam rate.
- Unverified rate.

## Dataset cần chuẩn bị

```text
data/benchmark/
├── known/
│   ├── employee_001_*.jpg
│   └── employee_002_*.jpg
├── unknown/
│   ├── stranger_001_*.jpg
│   └── stranger_002_*.jpg
└── hard_cases/
    ├── blur_*.jpg
    ├── low_light_*.jpg
    └── side_face_*.jpg
```

Không nên khóa threshold production nếu chưa có dữ liệu camera thật.
