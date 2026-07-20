# LiveMonitor ROI/Zone Editor Plan

## Goal

Cho phép `admin_super` vẽ, sửa, xóa ROI/Zone trực tiếp trên LiveMonitor. ROI được lưu vào `camera_sources.config.zones`, worker đọc zones động từ DB, vẽ ROI lên annotated stream và rule engine tiếp tục dùng zone để cảnh báo. User không phải `admin_super` chỉ được xem ROI, không thấy tool chỉnh sửa.

## Scope

- Backend FastAPI camera router.
- AI worker zone loading and drawing.
- Frontend LiveMonitor ROI editor.
- RBAC: chỉ role `admin_super` được tạo/sửa/xóa ROI.
- Không lưu ROI vào hard-code config nếu đã có DB camera config.
- Không làm mất các key camera config hiện tại như `always_on`, `ai_interval`, `stream_publish_fps`.
- Không phá phần LiveMonitor detection label hiện tại.

## Zone Data Contract

Zones lưu trong `camera_sources.config.zones`:

```json
{
  "gate": [[100, 100], [500, 100], [500, 400]],
  "restricted_area": [[600, 120], [900, 120], [900, 500]]
}
```

Rules:

- Key là tên zone.
- Value là polygon theo pixel frame gốc/canvas stream.
- Mỗi polygon tối thiểu 3 điểm.
- Mỗi điểm là `[x, y]`, ép về integer.
- Polygon invalid phải bị reject ở backend hoặc bị bỏ qua an toàn ở worker.

## Phase 1: Backend Zones API

File chính: `backend/cameras/router.py`

Status: Done.

1. Thêm validator/helper cho zones:
   - Validate object zones.
   - Validate mỗi polygon có ít nhất 3 điểm.
   - Validate mỗi point có đúng 2 số.
   - Ép tọa độ về `int`.
   - Giữ zone name dạng string không rỗng.

2. Thêm endpoint:

```text
GET /cameras/{camera_id}/zones
```

- Dependency: `require_camera_read`.
- Validate camera tồn tại.
- Trả `camera_sources.config.zones || {}`.

3. Thêm endpoint:

```text
PATCH /cameras/{camera_id}/zones
```

- Dependency: `require_admin_super`.
- Import đúng từ `backend.auth.security`.
- Validate camera tồn tại.
- Validate payload zones.
- Merge `zones` vào config hiện tại, không replace toàn bộ config.
- Update `camera_sources.config`.
- Nếu camera active/always_on, gọi lại logic apply/reload worker state nếu phù hợp.

## Phase 2: Worker Dynamic Zones

Files:

- `ai_worker/camera_worker.py`
- `ai_worker/zone_manager.py`

Status: Done.

1. Sửa `CameraWorkerConfig`:
   - Thêm field `zones`.
   - Trong `from_camera_row`, đọc `config.get("zones", {})`.

2. Sửa worker init:

```python
self.zone_manager = ZoneManager(config.zones)
```

3. Sửa `ZoneManager`:
   - Constructor nhận zones dict từ DB.
   - Convert JSON list sang tuple/int an toàn.
   - Bỏ polygon invalid dưới 3 điểm.
   - `draw_zones()` vẽ polygon và label zone.
   - `get_zone()` vẫn dùng center bbox để xác định zone.

4. Giữ `zone` trong `stream_track_payloads()` meta để rule/frontend dùng được.

## Phase 3: Frontend Types And API

Files:

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`

Status: Done.

1. Thêm type:

```ts
export type ZonePoint = [number, number];
export type CameraZones = Record<string, ZonePoint[]>;
```

2. Thêm API helpers:

```ts
getCameraZones(token: string, cameraId: string)
updateCameraZones(token: string, cameraId: string, zones: CameraZones)
```

## Phase 4: LiveMonitor ROI Editor

File chính: `frontend/src/components/LiveMonitor.tsx`

Status: Done.

1. Xác định quyền hiện tại:
   - Nhận `currentUser` từ parent nếu đã có.
   - Hoặc dùng permissions/role có sẵn trong AdminShell/AdminData.
   - Chỉ hiển thị ROI editor khi `currentUser.role >= 9`.

2. UI admin_super cần có:
   - Bật/tắt chế độ vẽ ROI.
   - Select/input zone name: `gate`, `restricted_area`, custom.
   - Save.
   - Undo điểm cuối.
   - Xóa vùng hiện tại.
   - Cancel.

3. Drawing behavior:
   - Click lên stream/canvas để thêm point.
   - Dùng overlay canvas hoặc HTML layer phía trên stream để preview polygon.
   - Scale tọa độ từ kích thước hiển thị về frame gốc.
   - Lưu tọa độ pixel theo frame gốc/canvas stream.

4. User thường:
   - Không thấy tool vẽ/sửa/xóa.
   - Vẫn xem ROI qua annotated frame từ worker.

5. Không phá phần detection hiện có:
   - Known person pills vẫn hiển thị.
   - Không spam Unknown/Unverified trong UI card.

## Phase 5: CSS

File: `frontend/src/app/globals.css`

Status: Done.

Thêm style cho:

- `.ops-roi-toolbar`
- `.ops-roi-button`
- `.ops-roi-overlay`
- `.ops-roi-point`
- `.ops-roi-label`

Design requirements:

- Toolbar gọn, không che camera quá nhiều.
- Điểm polygon dễ thấy.
- Màu zone:
  - `gate`: teal/xanh.
  - `restricted_area`: đỏ.
  - custom: vàng/xanh dương.
- Desktop/mobile không overlap, không kéo vỡ card.

## Phase 6: Verification

Status: Done.

Run checks:

```bash
/home/ntcai/venv/bin/python -m py_compile backend/cameras/router.py ai_worker/camera_worker.py ai_worker/zone_manager.py
npm run typecheck
```

Nếu môi trường Windows:

```powershell
npm.cmd run typecheck
```

Restart:

- Backend.
- Worker.
- Frontend nếu cần.

Manual acceptance:

1. Login `admin_super`:
   - Thấy tool vẽ ROI trên LiveMonitor.
   - Vẽ được polygon.
   - Lưu được.
   - Refresh trang vẫn còn ROI.

2. Login user role thấp:
   - Không thấy tool vẽ/sửa/xóa ROI.

3. Worker:
   - `draw_zones()` vẽ ROI lên annotated stream.
   - Track có `zone` đúng khi bbox center nằm trong polygon.

4. Rule:
   - `unknown_loitering_at_gate` hoạt động nếu zone là `gate`.
   - `unknown_entered_restricted_area` hoạt động nếu zone là `restricted_area`.

5. LiveMonitor:
   - Detection known hiện tên như hiện tại.
   - Không bị spam Unknown/Unverified trong phần UI card.

## Phase 7: Contract Guard

Status: Done.

File:

- `scripts/dev/validate_camera_zones_contract.py`

Coverage:

- Route `GET /cameras/{camera_id}/zones` tồn tại và không yêu cầu `admin_super`.
- Route `PATCH /cameras/{camera_id}/zones` bắt buộc `require_admin_super`.
- Role thấp bị chặn khi dùng `require_admin_super`.
- Backend normalize/reject zones đúng contract.
- `normalize_camera_config()` không làm mất `always_on`, `ai_interval`, `stream_publish_fps`.
- Worker `ZoneManager` nhận polygon hợp lệ, drop polygon lỗi, và trả zone theo bbox center.

Run:

```bash
/home/ntcai/venv/bin/python scripts/dev/validate_camera_zones_contract.py
```

## Phase 8: Frontend ROI Contract Guard

Status: Done.

File:

- `scripts/dev/validate_live_monitor_roi_contract.py`

Coverage:

- `AdminShell` truyền `currentUser` vào `LiveMonitor`.
- `LiveMonitor` chỉ bật ROI editor cho role `>= 9`.
- `LiveMonitor` dùng `getCameraZones()` và `updateCameraZones()`.
- Overlay ROI dùng frame size thật của canvas để scale tọa độ.
- Save ROI yêu cầu tối thiểu 3 điểm.
- Detection UI vẫn lọc `knownRuntimeTracks(runtime)` để không spam Unknown/Unverified.
- `frontend/src/lib/api.ts` và `frontend/src/lib/types.ts` có contract `CameraZones`.
- `frontend/src/app/globals.css` có class ROI overlay/toolbar và detection status pill.

Run:

```bash
/home/ntcai/venv/bin/python scripts/dev/validate_live_monitor_roi_contract.py
```

## Phase 9: ROI Smoke Command

Status: Done.

File:

- `scripts/dev/validate_live_monitor_roi_smoke.py`

Purpose:

- Gom các kiểm tra ROI/LiveMonitor vào một lệnh duy nhất.
- Chạy backend zones contract.
- Chạy frontend ROI contract.
- Compile các file Python liên quan.
- Chạy frontend `npm run typecheck`.

Run:

```bash
/home/ntcai/venv/bin/python scripts/dev/validate_live_monitor_roi_smoke.py
```

## Phase 10: Operations Documentation

Status: Done.

File:

- `docs/operations.md`

Content:

- Cách vẽ ROI/Zone trên Dashboard.
- Quyền chỉnh sửa chỉ dành cho `admin_super`.
- Data contract trong `camera_sources.config.zones`.
- Worker tự reload zones từ DB theo `CAMERA_ZONE_RELOAD_INTERVAL_SECONDS`.
- Lệnh smoke check ROI.
- Endpoint `GET/PATCH /cameras/{camera_id}/zones`.
- Troubleshooting nhanh khi ROI không hiện hoặc rule không match zone.
