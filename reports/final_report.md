# Final Report

## Má»¥c tiÃªu bÃ i toÃ¡n

XÃ¢y dá»±ng há»‡ thá»‘ng phÃ¡t hiá»‡n ngÆ°á»i láº¡ tá»« camera/RTSP báº±ng AI local. Há»‡ thá»‘ng nháº­n diá»‡n nhÃ¢n viÃªn Ä‘Ã£ cÃ³ trong cÆ¡ sá»Ÿ dá»¯ liá»‡u, phÃ¢n loáº¡i ngÆ°á»i khÃ´ng khá»›p lÃ  `unknown`, vÃ  chá»‰ cáº£nh bÃ¡o khi thá»a rule Ä‘á»ƒ trÃ¡nh spam.

## Kiáº¿n trÃºc há»‡ thá»‘ng

```text
Camera / RTSP
  -> AI Worker
  -> InsightFace local
  -> Qdrant vector search
  -> Tracking + voting
  -> Zone + Rule Engine
  -> Postgres event store
  -> FastAPI Backend
  -> Next.js Admin Frontend
```

Chi tiáº¿t: `reports/architecture.md`.

## MÃ´ hÃ¬nh sá»­ dá»¥ng

- InsightFace `buffalo_l`
- Detection: `det_10g.onnx`
- Recognition: `w600k_r50.onnx`
- Embedding: 512 chiá»u
- Vector search: Qdrant `employee_faces`, Cosine distance
- Metadata/event store: Postgres `face_db`

Chi tiáº¿t: `reports/model.md`.

## Database

Postgres tables chÃ­nh:

- `employees`
- `camera_sources`
- `alert_rules`
- `unknown_events`
- `system_metrics`
- `audit_logs`

Qdrant collection chÃ­nh:

- `employee_faces`

## Luá»“ng Known / Unknown / Unverified

```text
Face quality tháº¥p -> unverified
KhÃ´ng cÃ³ candidate -> unknown
Best score >= FACE_THRESHOLD vÃ  employee active -> known
NgÆ°á»£c láº¡i -> unknown
```

Chi tiáº¿t: `reports/pipeline.md`.

## Rule cáº£nh bÃ¡o

Rule Ä‘Æ°á»£c Ä‘á»c tá»« Postgres `alert_rules` khi worker khá»Ÿi Ä‘á»™ng, cÃ³ fallback `.env` náº¿u DB chÆ°a sáºµn sÃ ng.

Rule hiá»‡n cÃ³:

- `stable_unknown_face`
- `unknown_outside_working_hours`
- `unknown_loitering_at_gate`
- `unknown_entered_restricted_area`
- `unverified_in_restricted_area`

## Benchmark

Script benchmark:

```powershell
python scripts/benchmark/benchmark_pipeline.py --input data/benchmark
```

Outputs:

- `reports/benchmark_results.json`
- `reports/benchmark.md`

Metrics há»— trá»£:

- avg/min/max/P50/P95 latency
- faces processed
- known accuracy
- unknown detection rate
- false accept rate
- false reject rate
- unverified rate

Cáº§n dataset camera tháº­t Ä‘á»ƒ khÃ³a threshold production.

## HÆ°á»›ng dáº«n cháº¡y nhanh

Start infra:

```bash
./start.sh
```

Run backend:

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Run worker:

```powershell
python scripts/cameras/run_worker.py
```

Run frontend:

```powershell
npm install --prefix frontend
npm run dev --prefix frontend
```

Open:

```text
http://localhost:3000
```

## Káº¿t quáº£ smoke test backend/DB

```text
Date: 2026-05-25
Postgres: healthy, employees = 56
Qdrant: healthy, employee_faces points = 44
Production tables:
- camera_sources = 4
- alert_rules = 5
- unknown_events = 24
- system_metrics = 0
- camera_worker_status = 0
- audit_logs = 0
Backend smoke test:
- GET /system/health -> ok
- POST /auth/login admin/<dev password from DB> -> ok
- GET /auth/me -> admin
- GET /employees -> 56
- GET /cameras -> 4
- GET /rules -> 5
- GET /alerts -> 24
```

## Káº¿t quáº£ frontend

```text
Date: 2026-05-25
Frontend migrated to Next.js App Router + TypeScript.
Dev URL: http://localhost:3000
API base: NEXT_PUBLIC_API_BASE or http://localhost:8000
Features preserved:
- login/logout
- full-width admin shell with navigation
- dashboard metrics
- AI-annotated MJPEG canvas live monitor via backend `/cameras/{camera_id}/mjpeg`, designed for future camera grid expansion
- alerts page/list/detail/snapshot review
- camera management page + worker status
- rule management page
- employees management page
Verification:
- npm run typecheck --prefix frontend: pass
- npm run build --prefix frontend: pass
- Next.js route smoke test /: 200
Manual browser visual check: still recommended.
```

## Káº¿t quáº£ preflight worker/camera

```text
Date: 2026-05-25
camera_sources active: 4
- ai_pm_1: rtsp, ai_interval=0.7
- ai_pm_2: rtsp, ai_interval=0.7
- door_67b: rtsp, ai_interval=0.7
- door_67b: rtsp, ai_interval=0.7
Worker CLI: ok
CameraSourceRepository: ok
CameraWorkerConfig.from_camera_row: ok
worker_healthcheck: correctly fails without active worker heartbeat
Full worker RTSP/model run: still requires real camera/model runtime test.
```

## Káº¿t quáº£ kiá»ƒm tra benchmark dataset

```text
Date: 2026-05-25
Dataset folders prepared:
- data/benchmark/known/
- data/benchmark/unknown/
- data/benchmark/hard_cases/
Images found: 0
Benchmark run: blocked, No images found
Threshold lock: not possible until real labeled camera images are added.
```

## Káº¿t quáº£ preflight Docker production stack

```text
Date: 2026-05-25
Production env validation: failed
Blockers:
- POSTGRES_PASSWORD cÃ²n lÃ  giÃ¡ trá»‹ dev/default
- JWT_SECRET cÃ²n lÃ  giÃ¡ trá»‹ dev/default
Production compose config: passed
Current Docker:
- Postgres local healthy
- Qdrant local healthy
- Port 8080 Ä‘ang Ä‘Æ°á»£c websearch-searxng dÃ¹ng
Production stack start: skipped Ä‘á»ƒ trÃ¡nh cháº¡y vá»›i secret khÃ´ng an toÃ n vÃ  port conflict.
```

## Háº¡n cháº¿ hiá»‡n táº¡i

- ChÆ°a cÃ³ káº¿t quáº£ benchmark trÃªn dataset camera tháº­t.
- ChÆ°a khÃ³a threshold production.
- Frontend Ä‘Ã£ chuyá»ƒn sang Next.js, váº«n cáº§n test browser trá»±c quan sau migration.
- Worker chÆ°a cÃ³ service manager/healthcheck production.
- ChÆ°a cÃ³ Dockerfile riÃªng cho backend/frontend/worker.

## HÆ°á»›ng cáº£i thiá»‡n

- Thu tháº­p dataset `known/unknown/hard_cases` tá»« camera tháº­t.
- Cháº¡y benchmark Ä‘á»ƒ chá»n threshold vÃ  ghi nháº­n case yáº¿u.
- Bá»• sung Dockerfile, healthcheck, log rotation, backup/restore.
- HoÃ n thiá»‡n frontend alert detail vÃ  workflow review.
- ThÃªm tráº¡ng thÃ¡i health tá»«ng camera/worker vÃ o backend.
