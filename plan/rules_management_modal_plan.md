# Plan: Rules Management Modal UX

## Goal

Chuyen trang Rules tu form inline tren dau trang sang flow popup/modal:

- Mac dinh chi hien danh sach rule va nut `Them rule`.
- Bam `Them rule` mo modal tao rule.
- Bam tung rule mo modal chinh sua rule.
- Form khong con dinh tren dau list.
- Popup Rules va Camera nhin mem hon, khong nhu mot block rieng bi dan len man hinh.

## Phase 1: Modal State And Entry Points

- Them state `modalMode: 'create' | 'edit' | null`.
- Header co nut `Them rule`.
- Bam rule trong list mo modal edit.
- Dong modal bang close button, `Huy`, backdrop, Escape.

## Phase 2: Move Create/Edit Forms Into Modal

- Dua form them rule vao modal create.
- Dua form sua rule vao modal edit.
- Giu cac truong hien co:
  - Ma rule
  - Ten rule
  - Muc do canh bao
  - Bat/tat rule
  - Config truc quan theo rule
  - JSON config ky thuat

## Phase 3: Visual Polish

- Rule list la cac row/card click duoc.
- Row hien ten rule, trang thai, muc do, mo ta.
- Popup Rules/Cameras dung backdrop nhe hon.
- Header modal lien mach voi body, bot cam giac tach block.
- Mobile khong tran ngang.

## Phase 4: Verification

Commands:

```bash
npm.cmd run typecheck --prefix frontend
```

Manual checklist:

- Vao Rules khong con form inline tren dau.
- Bam `Them rule`, modal create hien.
- Bam tung rule, modal edit hien dung thong tin.
- Luu rule thanh cong va refresh list.
- Dong modal bang Huy, close, backdrop, Escape.
- Camera modal nhin bot bi tach khoi giao dien.

## Implementation Status

Updated: 2026-06-04

- Phase 1: Done. Added modal state, `Them rule` entry point, row click edit entry point, Escape/backdrop close.
- Phase 2: Done. Moved create/edit rule forms into popup modal and removed inline create/edit forms from default page.
- Phase 3: Done. Added rule modal CSS and softened shared Camera/Rules modal backdrop/header styling.
- Phase 4: Partially done. `npm.cmd run typecheck --prefix frontend` passes. Manual browser verification remains.
