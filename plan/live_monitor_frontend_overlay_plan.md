# LiveMonitor Frontend Overlay Plan

## Goal

Chuyển LiveMonitor production từ frame đã vẽ sẵn bởi worker/backend sang raw frame + frontend overlay bằng metadata.

## Phase 1: Audit Data Flow

Status: Done.

- LiveMonitor hiện fetch `/cameras/{camera_id}/mjpeg`.
- Backend `/mjpeg` hiện trả `annotated_mjpeg_frames()` từ Redis `latest_annotated_jpeg`.
- Worker đang gọi `draw_tracks()` và `zone_manager.draw_zones()` trước khi publish annotated frame.
- Runtime metadata đã có `tracks`, nhưng thiếu `source_width`, `source_height`, `zones`.
- `bbox` đang theo frame gốc vì pipeline/tracker xử lý trực tiếp trên `frame.copy()` từ reader.

## Phase 2: Metadata Contract

Status: Done.

Runtime meta cần có:

```json
{
  "camera_id": "ai_pm_1",
  "frame_id": 1,
  "source_width": 1280,
  "source_height": 720,
  "created_at": "2026-06-07T00:00:00.000+00:00",
  "tracks": [],
  "zones": {}
}
```

## Phase 3: Worker Production Raw Stream

Status: Done.

- Không vẽ bbox/label lên production raw frame.
- Giữ annotated debug nếu `debug_annotated_stream=true`.
- Publish raw frame + metadata đầy đủ.

## Phase 4: Backend Raw Stream

Status: Done.

- Thêm `/cameras/{camera_id}/raw.mjpeg`.
- Giữ `/cameras/{camera_id}/mjpeg` annotated cho debug/manual.
- `/cameras/runtime` trả `source_width`, `source_height`, `zones`.

## Phase 5: Frontend Overlay

Status: Done.

- LiveMonitor fetch raw MJPEG.
- Frontend vẽ bbox/label/status/score/ROI bằng SVG overlay từ runtime metadata.
- ROI editor dùng cùng hệ tọa độ source frame.

## Phase 6: Verification

Status: Done.

Run:

```bash
/home/ntcai/venv/bin/python -m py_compile ai_worker/camera_worker.py ai_worker/redis_frame_publisher.py backend/cameras/router.py backend/cameras/annotated_stream.py
npm run typecheck
```

## Phase 7: Runtime Probe

Status: Done.

File:

- `scripts/dev/validate_live_monitor_frontend_overlay_runtime.py`

Coverage:

- Login backend.
- `/cameras/runtime` có ít nhất một camera realtime với `source_width`, `source_height`.
- Runtime tracks giữ `track_id`, `label`, `status`, `score`, `bbox`, `zone`.
- Runtime zones là object.
- `/cameras/{camera_id}/raw.mjpeg` trả multipart JPEG.

Run:

```bash
/home/ntcai/venv/bin/python scripts/dev/validate_live_monitor_frontend_overlay_runtime.py
```

## Phase 8: MJPEG Overlay Query Compatibility

Status: Done.

Changes:

- `/cameras/{camera_id}/mjpeg` giữ mặc định annotated/debug stream.
- `/cameras/{camera_id}/mjpeg?overlay=0` trả raw production stream.
- `/cameras/{camera_id}/raw.mjpeg` vẫn là raw stream rõ nghĩa cho LiveMonitor production.
- Runtime probe kiểm tra cả `raw.mjpeg` và `mjpeg?overlay=0`.

## Phase 9: No Double Overlay Guard

Status: Done.

File:

- `scripts/dev/validate_live_monitor_no_double_overlay.py`

Coverage:

- LiveMonitor production fetch `/raw.mjpeg`, không fetch annotated `/mjpeg`.
- LiveMonitor vẫn render `StreamOverlay` và `TrackOverlay`.
- Backend giữ raw stream và annotated debug stream.
- `/mjpeg?overlay=0` vẫn chọn raw stream.
- Worker `publish_stream_frame()` không gọi `draw_tracks()` hoặc `draw_zones()` trực tiếp.
- Worker chỉ vẽ tracks/zones trong `build_debug_annotated_frame()`, có gate `debug_annotated_stream`.

## Phase 10: Redis Overlay Payload Probe

Status: Done.

File:

- `scripts/dev/validate_redis_overlay_payload.py`

Coverage:

- Redis có `camera:*:latest_meta`.
- Meta có `camera_id`, `frame_id`, `created_at`, `source_width`, `source_height`, `tracks`, `zones`.
- Track payload giữ `track_id`, `label`, `status`, `score`, `bbox`, `zone`.
- Zone payload là polygon `[x, y]`.
- Raw JPEG key tồn tại và có JPEG magic bytes.
- Annotated/debug JPEG key vẫn tồn tại cho debug/manual.

## Phase 11: Per-Camera Metadata Polling

Status: Done.

Changes:

- Thêm `GET /cameras/{camera_id}/meta` để lấy runtime metadata của một camera.
- LiveMonitor vẫn dùng `/cameras/runtime` cho summary, nhưng mỗi stream tile poll `/meta` nhanh hơn.
- Overlay dùng `displayRuntime` từ per-camera meta để bbox/label/ROI bám raw stream tốt hơn.
- Runtime probe kiểm tra `/meta` có `frame_id`, `source_width`, `source_height`, `tracks`, `zones`.

Defaults:

- `RUNTIME_POLL_INTERVAL_MS = 2000`
- `OVERLAY_META_POLL_INTERVAL_MS = 350`
