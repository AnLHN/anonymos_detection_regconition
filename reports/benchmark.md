# Benchmark pipeline

## Input

- Images: 2
- Faces processed: 4
- Labeled images: 2

## End-to-end latency

- Average: 1311.87 ms/image
- Min: 1211.94 ms
- Max: 1411.81 ms
- P50: 1211.94 ms
- P95: 1411.81 ms

## Recognition quality

- Known images: 1
- Unknown images: 1
- Known accuracy: 100.00%
- Unknown detection rate: 100.00%
- False accept rate: 100.00%
- False reject rate: 0.00%
- Unverified rate: 0.00%

## Per-image results

| Image | Expected | Latency ms | Faces | Statuses | Best score | Best label |
|---|---|---:|---:|---|---:|---|
| data\benchmark\known\manual_static_known_full.jpg | known | 1211.94 | 2 | unknown, known | 0.5826 | Hồ Văn Phương |
| data\benchmark\unknown\manual_static_unknown_full.jpg | unknown | 1411.81 | 2 | unknown, known | 0.5826 | Hồ Văn Phương |
