# Pipeline

## AI recognition pipeline

```text
Input frame/image
  -> Face detection
  -> Quality filter
  -> Face embedding 512-d
  -> Qdrant top-k search
  -> Recognition decision
  -> known / unknown / unverified
```

## Decision logic

```text
Face quality low -> unverified
No candidate -> unknown
Best score >= FACE_THRESHOLD and employee active -> known
Otherwise -> unknown
```

## Realtime worker pipeline

```text
Load active camera_sources
  -> start reader thread per camera
  -> keep latest frame
  -> run AI every ai_interval seconds
  -> update tracker
  -> assign zone
  -> evaluate alert rules
  -> save warning event
  -> write FPS/latency metrics
```

## Alert rules

Rules are loaded from Postgres `alert_rules` when the worker starts. If Postgres is unavailable, the worker falls back to `.env` defaults.

Supported rule codes:

- `stable_unknown_face`
- `unknown_outside_working_hours`
- `unknown_loitering_at_gate`
- `unknown_entered_restricted_area`
- `unverified_in_restricted_area`

Supported config fields:

- `is_enabled`
- `warning_level`
- `cooldown_seconds`
- `start`, `end`
- `frames`
- `gate_zones`
- `restricted_zones`
