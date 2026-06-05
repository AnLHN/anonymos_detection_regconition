# Ke hoach nhung Grafana/Prometheus vao Admin Frontend

## Muc tieu

Tich hop monitoring vao Admin Console theo huong:

```text
Backend/worker metrics
  -> Prometheus scrape
  -> Grafana dashboard
  -> Frontend Admin nhung Grafana bang iframe
```

Nguoi dung admin co the vao frontend va xem dashboard monitoring ma khong can tu mo URL Grafana rieng.

## Hien trang

Project da co nen tang monitoring:

- Backend expose `/metrics` trong `backend/main.py`.
- `backend/metrics.py` da co Prometheus middleware cho HTTP requests:
  - `unknown_detection_http_requests_total`
  - `unknown_detection_http_request_duration_seconds`
- `infra/prometheus.yml` scrape backend:
  - job `unknown-detection-backend`
  - target `backend:8000`
- `infra/grafana-datasources.yml` da cau hinh datasource Prometheus.
- `infra/docker-compose.production.yml` co service Prometheus va Grafana.

Nhung hien tai:

- Frontend chua co page nhung Grafana.
- Chua thay dashboard JSON provisioned cho Grafana.
- Metrics camera/AI nhu `read_fps`, `camera_fps`, `ai_latency`, Redis frame freshness dang nam o Postgres/Redis, chua expose day du thanh Prometheus metrics.

## Kien truc de xuat

```text
ai_worker
  -> cap nhat camera_worker_status trong Postgres
  -> ghi system_metrics trong Postgres
  -> publish latest_meta vao Redis

backend /metrics
  -> expose HTTP metrics hien co
  -> expose camera/AI gauges moi tu Postgres/Redis

Prometheus
  -> scrape backend /metrics

Grafana
  -> datasource Prometheus
  -> load dashboard Unknown Detection tu provisioned JSON

Frontend Admin
  -> /system/monitoring
  -> iframe Grafana dashboard
```

## Phase 1 - Expose camera/AI metrics ra Prometheus

### Muc tieu

Grafana co du metrics quan trong de ve dashboard van hanh camera.

### Files du kien

- `backend/metrics.py`
- `backend/main.py` neu can
- `backend/database/postgres.py` neu can helper
- `backend/config.py`

### Metrics nen expose

Backend HTTP metrics da co:

```text
unknown_detection_http_requests_total
unknown_detection_http_request_duration_seconds
```

Them camera/AI metrics:

```text
unknown_detection_camera_worker_running{camera_id}
unknown_detection_camera_read_fps{camera_id}
unknown_detection_camera_fps{camera_id}
unknown_detection_camera_ai_latency_ms{camera_id}
unknown_detection_camera_last_seen_age_seconds{camera_id}
unknown_detection_camera_redis_frame_age_seconds{camera_id}
unknown_detection_camera_redis_frame_available{camera_id,type="raw|annotated|meta"}
```

Neu can alert/event metrics:

```text
unknown_detection_alerts_total{warning_level,warning_type,review_status}
unknown_detection_alerts_recent_total{warning_level,warning_type}
```

### Nguon du lieu

- `camera_worker_status` trong Postgres:
  - status
  - read_fps
  - camera_fps
  - ai_latency_ms
  - last_seen_at
- Redis keys:
  - `camera:{camera_id}:latest_raw_jpeg`
  - `camera:{camera_id}:latest_annotated_jpeg`
  - `camera:{camera_id}:latest_meta`
- `unknown_events` trong Postgres cho alert counters.

### Cach implement goi y

Trong `backend/metrics.py`:

- giu middleware hien co.
- them Gauge/Counter Prometheus cho camera metrics.
- trong `metrics_response()`, truoc `generate_latest()`, refresh gauges bang cach query Postgres/Redis.

Luu y:

- Khong de query `/metrics` qua nang.
- Gioi han query latest camera status va aggregate alert don gian.
- Neu Redis/Postgres loi, metric scrape khong nen lam backend crash.

### Tieu chi hoan thanh

Chay backend va goi:

```text
GET /metrics
```

Thay cac metric moi xuat hien.

## Phase 2 - Provision Grafana dashboard

### Muc tieu

Grafana tu load dashboard `Unknown Detection Monitoring` khi container start.

### Files du kien

- `infra/grafana-dashboards.yml` moi
- `infra/grafana-dashboard-unknown-detection.json` moi
- `infra/docker-compose.production.yml`
- co the cap nhat `infra/docker-compose.yml` neu local stack cung can

### Dashboard panels nen co

Backend/API:

- Request rate theo route/status.
- Request latency p50/p95.
- HTTP error rate 4xx/5xx.

Camera/AI:

- Worker running/offline theo camera.
- Read FPS theo camera.
- Camera FPS theo camera.
- AI latency ms theo camera.
- Worker last seen age.

Unified stream Redis:

- Redis annotated frame available.
- Redis raw frame available.
- Redis meta available.
- Redis frame age seconds.

Alerts:

- Alerts total theo warning level/type.
- Recent alerts count.

### Grafana provisioning

Datasource da co:

```text
infra/grafana-datasources.yml
```

Them dashboard provider:

```yaml
apiVersion: 1
providers:
  - name: Unknown Detection
    orgId: 1
    folder: Unknown Detection
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    options:
      path: /etc/grafana/provisioning/dashboards
```

Mount dashboard JSON vao Grafana container.

### Tieu chi hoan thanh

- Grafana start len co dashboard trong folder `Unknown Detection`.
- Dashboard dung datasource Prometheus.
- Panels khong loi query neu backend `/metrics` hoat dong.

## Phase 3 - Cho phep Grafana embedding an toan

### Muc tieu

Frontend co the nhung Grafana dashboard bang iframe.

### Files du kien

- `infra/docker-compose.production.yml`
- `infra/docker-compose.yml` neu local can
- `.env.example`
- `docs/deployment.md`

### Config can them

Trong Grafana service:

```text
GF_SECURITY_ALLOW_EMBEDDING=true
```

Neu muon xem iframe khong can login Grafana rieng trong mang noi bo:

```text
GF_AUTH_ANONYMOUS_ENABLED=true
GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
```

Neu khong bat anonymous:

- iframe se hien man login Grafana neu user chua login Grafana.
- An toan hon nhung UX kem hon.

### De xuat mac dinh

Cho local/dev:

```text
GF_SECURITY_ALLOW_EMBEDDING=true
GF_AUTH_ANONYMOUS_ENABLED=true
GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
```

Cho production:

- Can quyet dinh theo bao mat.
- Neu dashboard chi noi bo sau VPN/Nginx auth thi co the anonymous Viewer.
- Neu public internet thi khong nen anonymous.

### Tieu chi hoan thanh

- Grafana response khong chan iframe bang `X-Frame-Options: deny`.
- Dashboard co the load trong iframe cua frontend.

## Phase 4 - Them frontend page nhung Grafana

### Muc tieu

Admin co route monitoring trong frontend.

### Files du kien

- `frontend/src/app/system/monitoring/page.tsx` moi
- `frontend/src/components/AdminShell.tsx`
- `frontend/src/lib/config.ts`
- `frontend/src/app/globals.css`
- `.env.example`

### Frontend config

Them env public:

```text
NEXT_PUBLIC_GRAFANA_DASHBOARD_URL=http://localhost:3001/d/<uid>/unknown-detection?kiosk
```

Hoac neu qua Nginx path:

```text
NEXT_PUBLIC_GRAFANA_DASHBOARD_URL=/grafana/d/<uid>/unknown-detection?kiosk
```

### UI goi y

Them nav item:

```text
Monitoring
```

Role:

- chi admin role `>= 5`.

Page:

```tsx
<section className="monitoring-page">
  <div className="section-heading">
    <div>
      <h2>Monitoring</h2>
      <p>Grafana dashboard tu Prometheus metrics.</p>
    </div>
    <a href={grafanaUrl} target="_blank">Open Grafana</a>
  </div>
  <iframe src={grafanaUrl} className="monitoring-frame" />
</section>
```

Neu chua co URL:

- hien thong bao cau hinh `NEXT_PUBLIC_GRAFANA_DASHBOARD_URL`.

### Tieu chi hoan thanh

- Admin thay menu Monitoring.
- Iframe load Grafana dashboard.
- Co nut mo Grafana tab moi.
- User role < 5 khong thay monitoring nav/page.

## Phase 5 - Update docs va env

### Files du kien

- `.env.example`
- `docs/architecture.md`
- `docs/deployment.md`
- `docs/operations.md`

### Noi dung can ghi

- Prometheus scrape backend `/metrics`.
- Grafana dashboard provisioned.
- Cach mo Monitoring trong frontend.
- Cach cau hinh embedding/anonymous.
- Cach debug neu iframe bi chan.

Debug checklist:

```text
- Prometheus target backend UP?
- GET /metrics co metric moi?
- Grafana datasource Prometheus connected?
- Dashboard JSON da load?
- GF_SECURITY_ALLOW_EMBEDDING=true?
- URL iframe dung chua?
- Grafana auth/cookie co chan iframe khong?
```

## Phase 6 - Runtime verification

### Dieu kien can co

- Docker/compose chay du Prometheus + Grafana + backend.
- Backend `/metrics` reachable.
- It nhat mot camera worker neu muon xem camera metrics that.

### Kiem tra

1. Start services.
2. Goi:

```text
GET /metrics
```

Expect:

- HTTP metrics hien co.
- Camera/AI metrics moi neu co data.

3. Mo Prometheus:

```text
http://localhost:9090/targets
```

Expect:

- target `unknown-detection-backend` UP.

4. Query Prometheus:

```promql
unknown_detection_http_requests_total
unknown_detection_camera_ai_latency_ms
unknown_detection_camera_read_fps
```

5. Mo Grafana:

```text
http://localhost:3001
```

Expect:

- datasource Prometheus OK.
- dashboard Unknown Detection co panels.

6. Mo frontend:

```text
/system/monitoring
```

Expect:

- iframe load dashboard.
- nut Open Grafana mo dashboard tab moi.

### Verdict mong doi

PASS khi frontend monitoring page nhung duoc Grafana dashboard va dashboard lay data tu Prometheus.

## Rủi ro / tradeoff

### Grafana auth va iframe

Neu Grafana bat login rieng, iframe co the hien login page hoac bi cookie SameSite chan.

Giai phap:

- Dung same-domain reverse proxy `/grafana`.
- Hoac bat anonymous Viewer trong mang noi bo.
- Hoac de link Open Grafana song song voi iframe.

### Bao mat

Khong nen expose anonymous Grafana ra internet neu khong co reverse proxy auth/VPN.

### Metrics query overhead

Neu `/metrics` query Postgres/Redis moi scrape, can giu query nhe va co timeout/fallback.

### Camera metrics chua co data

Neu worker chua chay, panels camera co the trong. Dashboard nen chap nhan no-data.

## Thu tu uu tien de lam

1. Expose camera/AI metrics ra `/metrics`.
2. Provision Grafana dashboard JSON.
3. Cau hinh Grafana embedding.
4. Them frontend `/system/monitoring` iframe.
5. Update docs/env.
6. Verify runtime.

## Phase 7 - Runtime verification full stack

### Muc tieu

Chay full stack va xac nhan dashboard nhung trong frontend hoat dong that.

### Kiem tra

- `GET /metrics` co metric HTTP/camera/Redis/alerts.
- Prometheus target `unknown-detection-backend` UP.
- Grafana datasource Prometheus OK.
- Dashboard `Unknown Detection Monitoring` load duoc.
- Frontend `/system/monitoring` iframe load dashboard.

### Trang thai hien tai

Da verify duoc backend `/metrics`, compose config va frontend route. Chua PASS end-to-end vi Prometheus/Grafana chua chay trong runtime luc verify.

## Phase 8 - Them resource metrics CPU/RAM/Disk/Container

### Muc tieu

Them exporter de Grafana xem tai nguyen he thong va container.

### De xuat

- `node-exporter` cho CPU/RAM/Disk/Network cua host Linux/container host.
- `cadvisor` cho CPU/RAM/network theo container.
- Sau nay neu server Windows that thi can `windows_exporter` rieng ngoai Docker.

### Metrics/Panel

- CPU usage.
- Memory usage.
- Disk usage.
- Network RX/TX.
- Container CPU/memory.

## Phase 9 - Them Redis/Postgres/Qdrant metrics sau

### Muc tieu

Them exporter/metrics cho data stores.

### De xuat

- `redis_exporter` cho Redis memory/ops/clients/keyspace.
- `postgres_exporter` cho Postgres connections/db size/locks.
- Qdrant metrics neu version expose endpoint; neu khong thi backend expose health/collection summary.

## Phase 10 - Them AI inference metrics chi tiet

### Muc tieu

Quan sat chat luong AI pipeline sau hon.

### Metrics de them

- detection count.
- known/unknown/unverified count.
- face quality fail count.
- embedding latency.
- Qdrant search latency.
- frame publish FPS/size/errors.

### Files du kien

- `ai_worker/face_pipeline.py`
- `ai_worker/qdrant_http_service.py`
- `ai_worker/camera_worker.py`
- `backend/metrics.py`

## Phase 11 - Grafana alerting / Alertmanager

### Muc tieu

Canh bao van hanh khi service hoac pipeline co van de.

### Alert rules goi y

- Worker offline qua 2 phut.
- Redis frame stale > 10 giay.
- AI latency p95 cao.
- Backend 5xx tang.
- Disk gan day.
- Redis/Postgres/Qdrant down.

### Trang thai da lam

- Them `infra/prometheus-rules/unknown-detection-alerts.yml`.
- Cau hinh `infra/prometheus.yml` de nap rule va gui alert sang Alertmanager.
- Them `infra/alertmanager.yml` voi receiver mac dinh `noop`.
- Them service Alertmanager vao `infra/docker-compose.yml` va `infra/docker-compose.production.yml`.
- Them scrape job Qdrant de co alert `QdrantDown`.

### Can cau hinh tiep neu muon gui ra ngoai

- Sua `infra/alertmanager.yml` de them Email/Slack/Telegram/Webhook receiver.
- Restart Prometheus/Alertmanager sau khi doi rule hoac receiver.
- Kiem tra Prometheus `/alerts` va Alertmanager UI `http://localhost:9093`.

## Ket luan

Huong nay dung Grafana/Prometheus dung vai tro:

```text
Prometheus = thu thap time-series metrics
Grafana = ve dashboard
Frontend Admin = nhung dashboard cho admin xem truc tiep
```

Khong can frontend tu ve chart native ngay. Neu sau nay can UI don gian hon cho operator, co the them native summary cards rieng sau.
