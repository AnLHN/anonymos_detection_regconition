# Model and Recognition Notes

## Models

- InsightFace model pack: `buffalo_l`
- Detection model: `det_10g.onnx`
- Recognition model: `w600k_r50.onnx`
- Runtime: ONNX Runtime, CPU by default

## Embedding contract

- Embedding dimension: 512
- Vector DB: Qdrant collection `employee_faces`
- Distance: Cosine
- Threshold config: `FACE_THRESHOLD`

## Recognition contract

Qdrant payload fields used by the system:

```text
employee_id
emp_code
name
department
is_active
```

Only active employees should be accepted as valid `known` matches.

## Quality filter

A face can become `unverified` if it does not meet:

- `MIN_DETECTION_SCORE`
- `MIN_FACE_WIDTH`
- `MIN_FACE_HEIGHT`

## Current limitations

- Threshold still needs real camera benchmark data.
- Low light, motion blur, side face and masks can increase unverified/false reject rate.
- CPU runtime may limit multi-camera FPS.
