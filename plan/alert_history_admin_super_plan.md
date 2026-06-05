# Plan: Alert History Delete, Edit Lock, And admin_super Permission

## Current State

- The `accounts` table already has a `role SMALLINT` column.
- The backend does not enforce roles yet. Most routers only use `get_current_user`, so any logged-in account can access admin APIs.
- JWT tokens currently store only `sub = username`; they do not include role or permission claims.
- Alert history is stored in `unknown_events`.
- Alert review status can currently be updated by any logged-in user through `PATCH /alerts/{event_id}/status`.
- There is an `audit_logs` table, but alert edits/deletes are not consistently audited yet.

## Goal

Make alert history safe for non-technical admins:

- Normal admins can view alert history and update normal review fields.
- Destructive or historical repair actions are hidden from normal admins.
- Only `admin_super` can delete alerts or unlock/edit protected history.
- Alert history is locked by default.
- Delete should be easy in the UI but protected by confirmation and audit logging.

## Proposed Roles

Use numeric roles for compatibility with the existing `accounts.role` column:

- `0`: viewer
- `1`: operator
- `5`: admin
- `9`: `admin_super`

The backend should expose role labels to the frontend:

```json
{
  "username": "admin_super",
  "role": 9,
  "role_name": "admin_super"
}
```

## Role Permissions

Use roles across the whole admin system, not only alert history:

| Feature | viewer | operator | admin | admin_super |
| --- | --- | --- | --- | --- |
| View dashboard | Yes | Yes | Yes | Yes |
| View live monitor | Yes | Yes | Yes | Yes |
| View alerts | Yes | Yes | Yes | Yes |
| Update alert review status/note | No | Yes | Yes | Yes |
| Delete/restore alerts | No | No | No | Yes |
| Unlock/repair alert history | No | No | No | Yes |
| View cameras | Yes | Yes | Yes | Yes |
| Create/update cameras | No | No | Yes | Yes |
| View rules | Yes | Yes | Yes | Yes |
| Create/update rules | No | No | Yes | Yes |
| View employees | Yes | Yes | Yes | Yes |
| Manage users | No | No | No | Yes |
| Change user roles | No | No | No | Yes |
| Deactivate users | No | No | No | Yes |
| View audit logs | No | No | Yes | Yes |

Role meaning for non-technical users:

- `viewer`: Chỉ xem dashboard, live monitor, cảnh báo, camera, rule, employees.
- `operator`: Nhân sự trực ca. Được xử lý cảnh báo bằng trạng thái/ghi chú, không được sửa cấu hình.
- `admin`: Quản trị vận hành. Được sửa camera/rule, không được sửa hoặc xóa lịch sử cảnh báo.
- `admin_super`: Quyền tối cao. Được quản lý người dùng, phân quyền, xóa/khôi phục/sửa chữa lịch sử cảnh báo.

## Initial admin_super Account

Create or upsert one super admin account during schema initialization:

- Username: `admin_super`
- Temporary password: store outside Git in a private operator note or secret manager.
- Role: `9`
- Active: `true`

Important: this password is a local bootstrap password and should be changed after first login.

## Database Changes

Add soft-delete fields to `unknown_events`:

```sql
ALTER TABLE unknown_events
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_by TEXT,
    ADD COLUMN IF NOT EXISTS delete_reason TEXT;
```

Add edit-lock fields:

```sql
ALTER TABLE unknown_events
    ADD COLUMN IF NOT EXISTS is_editable BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS edit_unlocked_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS edit_unlocked_by TEXT,
    ADD COLUMN IF NOT EXISTS edit_lock_reason TEXT;
```

Recommended default:

- New alerts are not editable: `is_editable = false`.
- Normal review workflow can still update `review_status`, `note`, `reviewed_by`, `reviewed_at`.
- Historical repair fields require `admin_super` and `is_editable = true`.

## Backend Auth Changes

Update `backend/auth/security.py`:

- Add `CurrentUser` model/dataclass:
  - `username`
  - `role`
  - `role_name`
- Make `get_current_user` load account details from Postgres.
- Add helper dependencies:
  - `require_login`
  - `require_operator`
  - `require_admin`
  - `require_admin_super`

Update `/auth/me`:

- Return username and role.
- Frontend uses this to hide or show super-admin controls.

## User Management APIs

Add a new router:

```text
backend/users/router.py
```

Endpoints:

```http
GET /users
```

- Only `admin_super`.
- Returns username, email, role, role_name, is_active, created_at, updated_at.
- Never returns password hash.

```http
POST /users
```

- Only `admin_super`.
- Creates a user with username, email, password, role.
- Role must be one of `0`, `1`, `5`, `9`.

```http
PATCH /users/{username}
```

- Only `admin_super`.
- Allows changing email, role, is_active, and password reset.
- Prevent `admin_super` from deactivating or demoting the last active super admin.

```http
DELETE /users/{username}
```

- Only `admin_super`.
- Prefer soft deactivate instead of hard delete:

```sql
UPDATE accounts SET is_active = false WHERE username = %s
```

Safety rules:

- No user can change their own role downward if they are the last active `admin_super`.
- Password reset should require confirmation in the UI.
- All user create/update/deactivate actions go to `audit_logs`.

## Frontend User Management

Add a sidebar tab:

```text
Users
```

Only visible for `admin_super`.

User page UX:

- Table columns:
  - Username
  - Email
  - Role
  - Status
  - Created at
  - Actions
- Role selector uses friendly Vietnamese labels:
  - `Chỉ xem`
  - `Trực ca`
  - `Quản trị`
  - `Quyền tối cao`
- Add user modal:
  - Username
  - Email
  - Temporary password
  - Role
- Edit user modal:
  - Email
  - Role
  - Active/inactive
  - Reset password
- Dangerous actions require confirmation.

Normal users should not see the Users tab at all.

## Permission Application By Router

Apply role dependencies consistently:

- `GET /alerts`: login required.
- `PATCH /alerts/{event_id}/status`: `operator` or higher.
- `DELETE /alerts/{event_id}`: `admin_super`.
- `PATCH /alerts/{event_id}/restore`: `admin_super`.
- `PATCH /alerts/{event_id}/edit-lock`: `admin_super`.
- `PATCH /alerts/{event_id}` historical repair: `admin_super`.
- `GET /cameras`: login required.
- `POST /cameras`, `PATCH /cameras/{camera_id}`: `admin` or higher.
- `GET /rules`: login required.
- `POST /rules`, `PATCH /rules/{rule_code}`: `admin` or higher.
- `GET /employees`: login required.
- `GET /users`, `POST /users`, `PATCH /users/{username}`, `DELETE /users/{username}`: `admin_super`.

## Backend Alert APIs

Update list/get alerts:

- By default, exclude soft-deleted alerts:

```sql
WHERE deleted_at IS NULL
```

- Add optional `include_deleted=true`, allowed only for `admin_super`.

Add delete endpoint:

```http
DELETE /alerts/{event_id}
```

Rules:

- Only `admin_super`.
- Soft-delete only, do not hard-delete rows.
- Require `delete_reason`.
- Write an `audit_logs` entry.

Add restore endpoint:

```http
PATCH /alerts/{event_id}/restore
```

Rules:

- Only `admin_super`.
- Clears `deleted_at`, `deleted_by`, `delete_reason`.
- Writes an audit log.

Add edit-lock endpoint:

```http
PATCH /alerts/{event_id}/edit-lock
```

Payload:

```json
{
  "is_editable": true,
  "reason": "Correct camera/zone after verification"
}
```

Rules:

- Only `admin_super`.
- Writes `edit_unlocked_at`, `edit_unlocked_by`, `edit_lock_reason`.
- When locking again, keep audit trail.

Add repair endpoint:

```http
PATCH /alerts/{event_id}
```

Rules:

- Only `admin_super`.
- Only works when `is_editable = true`.
- Allow limited fields only:
  - `camera_id`
  - `zone`
  - `warning_type`
  - `warning_level`
  - `review_status`
  - `note`
  - `reason`
- Write before/after values to `audit_logs`.

## Frontend UX

Make this usable for non-technical admins:

- Normal admin sees alert detail, review status, note, snapshots.
- Normal admin does not see delete, restore, unlock, or repair buttons.
- `admin_super` sees a protected section in the alert detail modal:
  - `Mở khóa sửa lịch sử`
  - `Khóa lại`
  - `Sửa thông tin cảnh báo`
  - `Xóa cảnh báo`
  - `Khôi phục cảnh báo` for deleted alerts

Delete flow:

- Button text: `Xóa cảnh báo`
- First click opens a confirmation dialog.
- Dialog requires:
  - Delete reason input
  - Confirmation text, for example `XOA`
- Final button should be visually dangerous.
- After delete, close modal and refresh list.

Edit flow:

- If locked:
  - Show badge: `Đang khóa sửa`
  - Show helper text: `Lịch sử cảnh báo mặc định không được sửa để tránh sai lệch dữ liệu.`
- If unlocked:
  - Show editable form fields.
  - Show badge: `Đang cho phép sửa`
  - Provide `Lưu sửa chữa` and `Khóa lại`.

## Audit Logging

Every super-admin action should insert into `audit_logs`:

- Delete alert
- Restore alert
- Unlock edit
- Lock edit
- Repair alert fields

Audit data should include:

- Actor username
- Action
- Entity type: `unknown_event`
- Entity ID: event ID
- Before data
- After data

## Startup And Seeding

Update `scripts/db/init_event_schema.py`:

- Add new columns idempotently.
- Ensure `admin_super` exists.
- Ensure old accounts default to role `0`.

Password handling:

- Current project uses plain/sha256-compatible password verification.
- For this phase, seed the temporary password using the current compatible format.
- Later hardening should replace this with bcrypt/argon2.

## Verification Checklist

- Login with normal admin.
- Normal admin can view alerts.
- Normal admin cannot see delete/repair controls.
- Normal admin cannot call delete/repair APIs directly.
- Login with `admin_super`.
- `admin_super` can delete an alert with reason.
- Deleted alert disappears from default alert list.
- `admin_super` can include deleted alerts and restore one.
- `admin_super` can unlock an alert, repair allowed fields, and lock it again.
- All super-admin actions are recorded in `audit_logs`.

## Implementation Status

- Backend role dependencies, soft delete, restore, edit lock, repair, users API and audit logging are implemented.
- Frontend Users tab is restricted to `admin_super`.
- Alerts page supports filters, include deleted, bulk delete, restore, repair form and super-admin-only controls.
- Added missing single-alert delete confirmation flow requiring reason and `XOA`.
- Added missing alert edit-lock controls for opening and locking history from the detail modal.
- Verified frontend TypeScript with `npm.cmd run typecheck --prefix frontend`.
