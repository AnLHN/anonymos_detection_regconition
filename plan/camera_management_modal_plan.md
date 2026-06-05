# Plan: Camera Management Modal UX

## Goal

Chuyen trang Camera tu form inline lon sang flow gon hon:

- Mac dinh chi hien danh sach camera va nut `Them camera`.
- Bam `Them camera` thi mo popup/modal tao camera.
- Bam tung camera thi mo popup/modal chinh sua camera do.
- Khong de form chiem nguyen man hinh tren trang list.

## Phase 1: Modal State And Entry Points

- Them state `modalMode: 'create' | 'edit' | null`.
- Them nut `Them camera` tren header.
- Bam camera trong list thi set selected camera va mo modal edit.
- Dong modal bang nut dong, nut huy, backdrop, hoac Escape.

## Phase 2: Move Camera Form Into Popup

- Dua form tao/sua camera vao modal.
- Tao camera:
  - Hien truong `Ma camera`.
  - Submit goi `saveCamera`.
- Sua camera:
  - `Ma camera` readonly/disabled.
  - Submit goi `updateCamera`.
- Giu cac truong:
  - Ten camera
  - RTSP URL
  - Vi tri
  - Camera dang hoat dong
  - Luon bat camera nay

## Phase 3: List And Visual Polish

- Camera list la cac row/card click duoc.
- Row hien:
  - Ten camera
  - Active/Inactive
  - Worker status
  - Vi tri hoac ma camera
  - Loi gan nhat neu co
- Modal nho gon, responsive, co focus/hover ro.

## Phase 4: Verification

Commands:

```bash
npm.cmd run typecheck --prefix frontend
```

Manual checklist:

- Vao trang Cameras, khong con form inline lon.
- Bam `Them camera`, modal tao camera hien.
- Dong modal bang `Huy`, close button, backdrop, Escape.
- Bam mot camera, modal sua camera hien dung thong tin.
- Luu camera thanh cong refresh list.

## Implementation Status

Updated: 2026-06-04

- Phase 1: Done. Added modal state, `Them camera` entry point, row click edit entry point, Escape/backdrop close.
- Phase 2: Done. Moved create/edit camera form into popup modal.
- Phase 3: Done. Added modal/list/header CSS and removed the inline form from the default page.
- Phase 4: Partially done. `npm.cmd run typecheck --prefix frontend` passes. Local browser/port check timed out while probing `http://localhost:3000/cameras`, so visual/manual verification still needs refreshing the running frontend or restarting the dev server.
