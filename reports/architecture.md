# Architecture

## Má»¥c tiÃªu

Há»‡ thá»‘ng phÃ¡t hiá»‡n ngÆ°á»i láº¡ tá»« RTSP báº±ng InsightFace local, Qdrant vector search vÃ  Postgres event store.

## ThÃ nh pháº§n

```text
Camera / RTSP
  -> AI Worker
  -> InsightFace detection + recognition
  -> Qdrant employee_faces search
  -> Tracking + voting
  -> Zone + Rule Engine
  -> AlertManager
  -> Postgres unknown_events + system_metrics
  -> FastAPI Backend
  -> Static Admin Frontend
```

## Runtime services

- Postgres: metadata nhÃ¢n viÃªn, camera source, rule, event, metrics.
- Qdrant: collection `employee_faces`, vector size 512, cosine distance.
- AI Worker: Ä‘á»c `camera_sources`, xá»­ lÃ½ tá»«ng camera vÃ  ghi cáº£nh bÃ¡o.
- Backend API: auth, employees, cameras, rules, alerts, health/metrics.
- Frontend: admin UI Next.js gá»i backend API.

## Data flow

1. Worker Ä‘á»c frame má»›i nháº¥t tá»« camera.
2. InsightFace phÃ¡t hiá»‡n khuÃ´n máº·t vÃ  táº¡o embedding 512 chiá»u.
3. Embedding search trong Qdrant.
4. Decision tráº£ `known`, `unknown` hoáº·c `unverified`.
5. Tracker gom káº¿t quáº£ nhiá»u frame theo track.
6. Rule Engine quyáº¿t Ä‘á»‹nh cÃ³ cáº£nh bÃ¡o hay khÃ´ng.
7. AlertManager lÆ°u snapshot, JSONL debug vÃ  Postgres event.
8. Backend/Frontend hiá»ƒn thá»‹ alert, camera, rule vÃ  metric.
