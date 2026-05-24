# Model Documentation

## Current model pack

The project uses InsightFace model pack:

```text
buffalo_l
```

Loaded models:

```text
det_10g.onnx      # face detection
w600k_r50.onnx    # face recognition embedding
```

## Embedding

- Dimension: 512
- Normalization: InsightFace `normed_embedding`
- Qdrant distance: Cosine
- Collection: `employee_faces`

## Important compatibility note

The recognition model must match the model used to generate embeddings stored in Qdrant.

Changing recognition model pack may require rebuilding all employee embeddings and re-importing Qdrant.

Safe changes:

- Tuning thresholds.
- RTSP/display optimizations.
- Detection/runtime performance tuning.

Risky changes:

- Changing recognition model.
- Changing embedding normalization.
- Changing vector distance.

## Runtime

Current runtime:

```text
onnxruntime CPUExecutionProvider
```

GPU/CUDA may improve performance but requires separate CUDA/ONNX Runtime GPU setup.
