# Plan: Alert History Safe Delete/Edit Mode UX

## Muc tieu

Chinh lai trai nghiem `Lich su canh bao` de mac dinh la che do xem an toan, khong hien cac thao tac xoa/sua gay roi mat. Chi khi `admin_super` chu dong bat co `Cho phep chinh sua/xoa` thi UI moi hien cac control xoa/sua.

Phan xoa can don gian hon:

- Khong hien khu `Quan tri lich su canh bao` trong modal mac dinh.
- Khong bat nhap ly do xoa.
- Khong bat nhap `XOA` de xac nhan.
- Co the giu xoa nhieu, nhung bo o ly do xoa hang loat.
- Khi bat co cho phep, moi card canh bao hien icon thung rac nho de xoa nhanh.

## Nguyen tac UX

- Mac dinh: xem, loc, mo chi tiet, cap nhat trang thai/ghi chu.
- Thao tac nguy hiem: an het neu chua bat co.
- Co xoa/sua chi hien voi `admin_super`.
- Confirm xoa ngan gon, ro rang, khong dung form dai.
- Audit/backend van can ghi nhan nguoi thao tac va thoi gian.
- UI phai dong bo voi admin console hien tai, khong tao block do lon hoac form canh bao qua nang.

## Pham vi

### Trong pham vi

- `frontend/src/components/AlertsPanel.tsx`
- `frontend/src/lib/api.ts`
- `backend/alerts/router.py`
- CSS lien quan trong `frontend/src/app/globals.css`
- Test/typecheck frontend va compile backend.

### Ngoai pham vi

- Khong thay doi schema database neu khong bat buoc.
- Khong thay doi role model tong the.
- Khong lam lai toan bo trang Alerts.
- Khong bo audit log.
- Khong xoa mem thanh xoa that; van giu soft-delete.

## Current State

- Trang alert hien co nut `Tat chinh sua/xoa` hoac cac control quan tri dang lo dien qua nhieu.
- Modal chi tiet co khu `Quan tri lich su canh bao` gom:
  - Ly do thao tac.
  - Mo khoa sua.
  - Ly do xoa.
  - O xac nhan `XOA`.
  - Nut xoa canh bao lon.
- Danh sach co thanh xoa nhieu gom:
  - Checkbox chon trang.
  - So luong da chon.
  - O ly do xoa hang loat.
  - Nut xoa canh bao da chon.
- Backend delete hien yeu cau `delete_reason`.

## Desired State

### Mac dinh

- Khong hien checkbox tung canh bao.
- Khong hien thanh xoa nhieu.
- Khong hien icon thung rac tren card.
- Khong hien khu `Quan tri lich su canh bao` trong modal.
- Khong hien nut `Tat chinh sua/xoa`.
- Admin binh thuong khong thay bat ky control xoa/sua lich su nao.

### Khi admin_super bat co `Cho phep chinh sua/xoa`

- Hien checkbox chon tung canh bao.
- Hien checkbox `Chon trang nay`.
- Hien nut `Xoa canh bao da chon` khi co it nhat 1 canh bao duoc chon.
- Moi card canh bao hien mot icon thung rac nho.
- Icon thung rac xoa 1 canh bao sau confirm ngan.
- Bulk delete xoa nhieu sau confirm ngan.
- Khong co o ly do xoa.
- Khong co o nhap `XOA`.

## Phase 1: UX State And Feature Flag

### Muc tieu

Them state UI rieng cho `admin_super` de bat/tat che do thao tac nguy hiem.

### Viec can lam

- Trong `AlertsPanel.tsx`, them state:
  - `const [managementMode, setManagementMode] = useState(false)`
- Khi `isSuperAdmin` false:
  - Ep `managementMode = false`.
  - Khong render toggle.
- Khi `isSuperAdmin` true:
  - Render nut/toggle `Cho phep chinh sua/xoa`.
  - Khi bat: doi label thanh `Dang cho phep chinh sua/xoa`.
  - Khi tat: clear selected ids.

### Acceptance Criteria

- User thuong khong thay toggle.
- `admin_super` thay toggle nhung mac dinh tat.
- Tat toggle thi moi selection bi clear.

## Phase 2: Clean Default Alert List

### Muc tieu

Danh sach canh bao mac dinh chi la list doc/xem, khong co UI xoa.

### Viec can lam

- Chi render checkbox tung row khi:
  - `isSuperAdmin && managementMode && !alert.deleted_at`
- Chi render `alert-bulk-bar` khi:
  - `isSuperAdmin && managementMode`
- Bo o nhap ly do xoa hang loat.
- Nut bulk delete chi enable khi `selectedAlertIds.length > 0`.
- Neu `managementMode` false:
  - Row khong dung layout `is-managing`.
  - Khong de khoang trong cho checkbox.

### Acceptance Criteria

- Trang list mac dinh gon nhu list canh bao binh thuong.
- Khong con o ly do xoa hang loat.
- Khong con checkbox neu chua bat toggle.

## Phase 3: Single Delete Trash Icon

### Muc tieu

Cho phep xoa nhanh tung canh bao bang icon thung rac nho tren card, chi hien khi bat co.

### Viec can lam

- Them button icon thung rac vao moi alert row khi:
  - `isSuperAdmin && managementMode && !alert.deleted_at`
- Dat button o goc phai row, tach khoi button mo chi tiet de tranh click nham.
- Them `aria-label="Xoa canh bao ..."` cho accessibility.
- Khi click:
  - `event.stopPropagation()`
  - Goi confirm ngan: `Xoa canh bao nay?`
  - Neu dong y thi goi API xoa.
- Dung icon SVG/lucide neu project da co icon lib; neu khong co, dung ky hieu text/icon CSS don gian, khong dung emoji.

### Acceptance Criteria

- Icon thung rac khong hien mac dinh.
- Icon chi hien khi toggle bat.
- Click icon khong mo modal chi tiet.
- Xoa xong refresh list.

## Phase 4: Remove Heavy Delete UI From Detail Modal

### Muc tieu

Modal chi tiet khong con khu xoa/sua dai va cac truong ly do mac dinh.

### Viec can lam

- An/bo khu `Quan tri lich su canh bao` trong modal mac dinh.
- Bo cac state/input UI:
  - `deleteReason`
  - `deleteConfirm`
  - O `Ly do xoa`
  - O `Nhap XOA de xac nhan`
- Neu van can giu repair/edit lock cho admin_super:
  - Chi render khi `isSuperAdmin && managementMode`.
  - Uu tien tach thanh khu nho `Sua du lieu lich su`, collapsed hoac button phu.
- Theo yeu cau hien tai:
  - Khong can hien form repair chi tiet trong modal.
  - Chi giu cap nhat trang thai/ghi chu va thong tin ky thuat.

### Acceptance Criteria

- Modal chi tiet khong con box do lon nhu anh 1.
- Khong con bat nhap ly do thao tac de xoa.
- Khong con nut xoa lon trong modal.

## Phase 5: Bulk Delete Without Reason Input

### Muc tieu

Giu xoa nhieu nhung don gian.

### Viec can lam

- Bo input `Ly do xoa hang loat`.
- Nut bulk delete hien text:
  - `Xoa canh bao da chon`
  - Hoac `Xoa N canh bao`
- Khi click:
  - Confirm `Xoa N canh bao da chon?`
  - Neu dong y thi goi API.
- Sau khi xoa:
  - Clear selected ids.
  - Refresh list.

### Acceptance Criteria

- Khong con o ly do trong bulk bar.
- Khong xoa neu chua chon alert.
- Xoa nhieu thanh cong va list cap nhat.

## Phase 6: Backend Delete Reason Simplification

### Muc tieu

Backend khong bat frontend nhap ly do, nhung van co audit/deleted reason mac dinh.

### Viec can lam

- Trong `backend/alerts/router.py`, doi request model:
  - `delete_reason: str | None = None`
- Tao helper:
  - `normalize_delete_reason(reason, fallback)`
- Single delete fallback:
  - `Xoa tu giao dien quan tri`
- Bulk delete fallback:
  - `Xoa hang loat tu giao dien quan tri`
- Van ghi:
  - `deleted_at`
  - `deleted_by`
  - `delete_reason`
  - audit log.

### Acceptance Criteria

- API delete van chap nhan body khong co `delete_reason`.
- API delete van chap nhan body co `delete_reason` de tuong thich cu.
- DB van co `delete_reason` khong rong sau khi xoa.

## Phase 7: Frontend API Cleanup

### Muc tieu

API frontend khong ep UI truyen ly do.

### Viec can lam

- Doi `deleteAlert(token, eventId, deleteReason)` thanh:
  - `deleteAlert(token, eventId, deleteReason?: string)`
- Doi `deleteAlertsBulk(token, eventIds, deleteReason)` thanh:
  - `deleteAlertsBulk(token, eventIds, deleteReason?: string)`
- Chi dua `delete_reason` vao body khi co value; hoac gui fallback an neu muon giu backend cu.

### Acceptance Criteria

- AlertsPanel khong can quan ly state ly do xoa.
- TypeScript khong loi.

## Phase 8: CSS And Visual Polish

### Muc tieu

UI moi gon, dong bo, khong bi block do nang ne.

### Viec can lam

- Them/sua CSS:
  - `.alert-management-toggle`
  - `.alert-row-delete`
  - `.alert-bulk-bar.is-compact`
  - `.alert-row.is-managing`
- Trash button:
  - Kich thuoc 36-40px.
  - Border nhe.
  - Mau danger chi hien ro khi hover/focus.
  - Co focus ring.
- Bulk bar:
  - Compact, 1 dong neu du rong.
  - Responsive mobile khong tran.
- Dam bao row title khong bi icon chen chu.

### Acceptance Criteria

- UI mac dinh sach.
- Khi bat toggle, controls xoa hien co trat tu.
- Khong co text/input bi tran hoac de len nhau.

## Phase 9: Verification

### Muc tieu

Kiem tra duong chay chinh va khong lam hong quyen.

### Commands

```bash
npm.cmd run typecheck --prefix frontend
python -m compileall backend
```

### Manual Test Checklist

- Dang nhap role khong phai `admin_super`:
  - Khong thay toggle.
  - Khong thay checkbox.
  - Khong thay icon thung rac.
  - Khong thay bulk delete.
- Dang nhap `admin_super`:
  - Toggle mac dinh tat.
  - Bat toggle thi thay checkbox, bulk delete, icon thung rac.
  - Tat toggle thi selection clear va controls bien mat.
- Xoa 1 alert:
  - Click icon thung rac.
  - Confirm.
  - Alert bien mat khoi list mac dinh.
- Xoa nhieu:
  - Chon nhieu alert.
  - Click bulk delete.
  - Confirm.
  - Alerts bien mat va selection clear.
- Include deleted:
  - Neu dang bat filter hien canh bao da xoa, alert da xoa hien badge `Da xoa`.
  - Alert da xoa khong con checkbox/icon xoa.

## Phase 10: Full-stack Manual Validation

### Muc tieu

Chay day du Docker infrastructure, backend, frontend va test destructive path that tren database local.

### Dieu kien can co

- Docker Desktop dang chay.
- `./start.sh` chay thanh cong.
- Backend listen tren `http://localhost:8000`.
- Frontend listen tren `http://localhost:3000`.
- Dang nhap bang `admin_super`.

### Commands

```bash
./start.sh
```

Neu shell hien tai bao khong ket noi duoc Docker:

```text
failed to connect to the docker API at unix:///var/run/docker.sock
```

thi mo Docker Desktop truoc, doi Docker bao `Running`, roi chay lai `./start.sh` trong Git Bash/MINGW64.

### Manual Browser Checklist

- Mo `http://localhost:3000/alerts`.
- Xac nhan mac dinh:
  - Khong co checkbox.
  - Khong co icon thung rac.
  - Khong co bulk delete.
  - Khong co box quan tri lich su trong modal chi tiet.
- Bat `Cho phep chinh sua/xoa`:
  - Checkbox hien tren tung alert chua xoa.
  - Icon thung rac hien tren tung alert chua xoa.
  - Bulk bar hien nhung khong co o ly do xoa.
- Xoa 1 alert:
  - Bam icon thung rac.
  - Dialog trong app hien `Xac nhan thao tac`.
  - Bam `Xoa`.
  - Alert bien mat khoi list mac dinh.
- Xoa nhieu:
  - Chon 2 alert.
  - Bam `Xoa canh bao da chon`.
  - Dialog trong app hien dung so luong.
  - Bam `Xoa`.
  - Alerts bien mat khoi list mac dinh.
- Include deleted:
  - Bat `Hien canh bao da xoa`.
  - Alert da xoa hien badge `Da xoa`.
  - Alert da xoa khong co checkbox/icon thung rac.

### API/DB Expectations

- Single delete body co the la `{}`.
- Bulk delete body co the chi can `{ "event_ids": [...] }`.
- Backend tu set `delete_reason` fallback:
  - `Xoa tu giao dien quan tri`
  - `Xoa hang loat tu giao dien quan tri`
- `deleted_at`, `deleted_by`, `delete_reason` duoc ghi.
- `audit_logs` co record tuong ung.

## Phase 11: Offline Hardening And Contract Guard

### Muc tieu

Khi chua the chay full-stack do Docker daemon chua san sang, them lop kiem tra offline de tranh safe-delete UX bi regression trong cac lan sua tiep theo.

### Viec da lam

- Xoa CSS cu khong con duoc dung:
  - `.super-admin-panel`
  - `.delete-box`
  - `.repair-form`
- Them script:
  - `scripts/dev/validate_alert_safe_delete_contract.py`
- Script kiem tra:
  - Backend delete reason optional.
  - Backend fallback reason hoat dong.
  - `AlertsPanel.tsx` khong con `window.confirm`.
  - `AlertsPanel.tsx` khong con state/input ly do xoa cu.
  - `AlertsPanel.tsx` co in-app delete confirmation dialog.
  - `globals.css` khong con CSS quan tri lich su cu.
  - `globals.css` co CSS cho safe-delete mode moi.

### Commands

```bash
python scripts/dev/validate_alert_safe_delete_contract.py
npm.cmd run typecheck --prefix frontend
python -m compileall backend scripts/dev/validate_alert_safe_delete_contract.py
```

### Acceptance Criteria

- Script validation in ra `alert_safe_delete_contract: ok`.
- Frontend typecheck pass.
- Backend/script compile pass.

## Phase 12: Offline Backend Delete Flow Validation

### Muc tieu

Kiem tra duong chay delete route that o backend ma khong can Docker/Postgres, bang cach monkeypatch DB layer nhe.

### Viec da lam

- Them script:
  - `scripts/dev/validate_alert_delete_backend_flow.py`
- Script goi truc tiep:
  - `delete_alert(...)`
  - `delete_alerts_bulk(...)`
- Script kiem tra:
  - Single delete tra `{"status": "ok"}`.
  - Single delete dung fallback `Xoa tu giao dien quan tri`.
  - Bulk delete bo qua id rong.
  - Bulk delete bo qua alert da xoa san.
  - Bulk delete dung fallback `Xoa hang loat tu giao dien quan tri`.
  - Audit log duoc goi cho single va tung alert bulk da xoa.

### Commands

```bash
python scripts/dev/validate_alert_delete_backend_flow.py
python scripts/dev/validate_alert_safe_delete_contract.py
npm.cmd run typecheck --prefix frontend
python -m compileall backend scripts/dev/validate_alert_safe_delete_contract.py scripts/dev/validate_alert_delete_backend_flow.py
```

### Acceptance Criteria

- Script backend flow in ra `alert_delete_backend_flow: ok`.
- Script contract in ra `alert_safe_delete_contract: ok`.
- Frontend typecheck pass.
- Backend/scripts compile pass.

## Phase 13: Offline Permission Guard Validation

### Muc tieu

Kiem tra destructive alert delete endpoints khong bi mo nham cho role thap hon `admin_super`.

### Viec da lam

- Them script:
  - `scripts/dev/validate_alert_delete_permission_guard.py`
- Script kiem tra:
  - `DELETE /alerts` co dependency `require_admin_super`.
  - `DELETE /alerts/{event_id}` co dependency `require_admin_super`.
  - `viewer`, `operator`, `admin` bi `require_admin_super` reject voi HTTP 403.
  - `admin_super` pass `require_admin_super`.

### Commands

```bash
python scripts/dev/validate_alert_delete_permission_guard.py
python scripts/dev/validate_alert_delete_backend_flow.py
python scripts/dev/validate_alert_safe_delete_contract.py
npm.cmd run typecheck --prefix frontend
python -m compileall backend scripts/dev/validate_alert_safe_delete_contract.py scripts/dev/validate_alert_delete_backend_flow.py scripts/dev/validate_alert_delete_permission_guard.py
```

### Acceptance Criteria

- Script permission guard in ra `alert_delete_permission_guard: ok`.
- Backend flow validation pass.
- Safe-delete contract validation pass.
- Frontend typecheck pass.
- Backend/scripts compile pass.

## Rollback Plan

- Neu UI xoa moi co loi:
  - Tat render trash icon va bulk bar theo `managementMode`.
  - Backend optional delete reason van tuong thich nguoc nen khong can rollback DB.
- Neu backend optional reason loi:
  - Frontend tam thoi gui fallback string an khi goi delete.

## Done Definition

- `admin_super` co the bat/tat che do chinh sua/xoa.
- Mac dinh khong hien thao tac xoa/sua.
- Xoa tung alert bang icon thung rac.
- Xoa nhieu khong can nhap ly do.
- Modal chi tiet khong con khu quan tri dai va nang.
- Backend van audit va soft-delete dung.
- Typecheck frontend va compile backend pass.

## Implementation Status

Updated: 2026-06-04

- Phase 1: Done. Added `managementMode` gated by `admin_super`.
- Phase 2: Done. Default alert list hides checkboxes, bulk delete, and destructive controls.
- Phase 3: Done. Added per-alert trash button in management mode.
- Phase 4: Done. Removed the heavy super-admin history management/delete UI from alert detail modal.
- Phase 5: Done. Bulk delete no longer requires a reason input.
- Phase 6: Done. Backend delete reason is optional and falls back to an internal default reason.
- Phase 7: Done. Frontend delete APIs accept optional delete reason.
- Phase 8: Done. Added compact management-mode CSS and replaced browser confirm with an in-app delete confirmation dialog.
- Phase 9: Automated verification done. `npm.cmd run typecheck --prefix frontend`, `python -m compileall backend`, optional delete-reason model checks, and `GET http://localhost:3000/alerts` all pass.
- Phase 10: Blocked by local Docker daemon not running. `./start.sh` failed with `failed to connect to the docker API at unix:///var/run/docker.sock`; destructive API/manual browser testing still needs Docker Desktop running and the full stack started with `./start.sh`.
- Phase 11: Done. Removed unused legacy alert-admin CSS and added `scripts/dev/validate_alert_safe_delete_contract.py`; validation, frontend typecheck, and backend/script compile pass.
- Phase 12: Done. Added `scripts/dev/validate_alert_delete_backend_flow.py`; backend delete route simulation, contract validation, frontend typecheck, and backend/scripts compile pass.
- Phase 13: Done. Added `scripts/dev/validate_alert_delete_permission_guard.py`; permission guard validation, backend flow validation, contract validation, frontend typecheck, and backend/scripts compile pass.
