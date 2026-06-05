# User Guide

## Login

Run the Next.js frontend with `npm run dev --prefix frontend`, open `http://localhost:3000`, and sign in with an account from the imported `accounts` table.

## Dashboard

Use the dashboard to inspect system status, recent alerts and metrics exposed by the backend.

## Cameras

Camera sources are stored in Postgres table `camera_sources`. The frontend camera form can create or update a camera by `camera_id`.

Worker commands:

```powershell
python scripts/cameras/run_worker.py --camera-id door_67b
python scripts/cameras/run_worker.py
```

## Alerts

Alerts are written to:

- Postgres table `unknown_events`
- JSONL debug log `storage/logs/events.jsonl`
- snapshots under `storage/snapshots/`

In the frontend, click an alert row to open detail, view snapshots and update review status/note.

Review fields:

- `review_status`
- `reviewed_at`
- `reviewed_by`
- `note`

## Rules

The frontend rule editor can enable/disable a rule, change warning level and edit JSON config.

List rules:

```text
GET /rules
```

Update rule:

```text
PATCH /rules/{rule_code}
```

Example:

```json
{"is_enabled": true, "config": {"frames": 8, "cooldown_seconds": 30}}
```

## Benchmark

Place labeled images in:

```text
data/benchmark/known/
data/benchmark/unknown/
data/benchmark/hard_cases/
```

Run:

```powershell
python scripts/benchmark/benchmark_pipeline.py --input data/benchmark
```

Outputs:

```text
reports/benchmark_results.json
reports/benchmark.md
```
