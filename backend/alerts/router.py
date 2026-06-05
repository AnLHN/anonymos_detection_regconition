import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend.auth.security import CurrentUser, get_current_user, has_permission, require_permission
from backend.database.postgres import execute, fetch_all, fetch_one

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])
require_alert_update = require_permission("alerts:update")
require_alert_read = require_permission("alerts:read")
require_alert_delete = require_permission("alerts:delete")
require_alert_restore = require_permission("alerts:restore")
require_alert_repair = require_permission("alerts:repair")


class AlertDeleteRequest(BaseModel):
    delete_reason: str | None = None


class AlertBulkDeleteRequest(BaseModel):
    event_ids: list[str]
    delete_reason: str | None = None


class AlertRestoreRequest(BaseModel):
    reason: str = ""


class AlertEditLockRequest(BaseModel):
    is_editable: bool
    reason: str


class AlertRepairRequest(BaseModel):
    camera_id: str | None = None
    zone: str | None = None
    warning_type: str | None = None
    warning_level: str | None = None
    review_status: str | None = None
    note: str | None = None
    reason: str | None = None


@router.get("")
def list_alerts(
    limit: int = 50,
    offset: int = 0,
    camera_id: str | None = None,
    review_status: str | None = None,
    warning_level: str | None = None,
    warning_type: str | None = None,
    zone: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    q: str | None = None,
    include_deleted: bool = False,
    current_user: CurrentUser = Depends(require_alert_read),
) -> list[dict]:
    if include_deleted and not has_permission(current_user, "alerts:delete"):
        raise HTTPException(status_code=403, detail="Insufficient permission")
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    filters = [] if include_deleted else ["deleted_at IS NULL"]
    params: list[object] = []

    if camera_id:
        filters.append("camera_id = %s")
        params.append(camera_id)
    if review_status:
        filters.append("review_status = %s")
        params.append(review_status)
    if warning_level:
        filters.append("warning_level = %s")
        params.append(warning_level)
    if warning_type:
        filters.append("warning_type = %s")
        params.append(warning_type)
    if zone:
        filters.append("zone = %s")
        params.append(zone)
    if created_from:
        filters.append("created_at >= %s")
        params.append(created_from)
    if created_to:
        filters.append("created_at <= %s")
        params.append(created_to)
    if q:
        search = f"%{q.strip()}%"
        filters.append(
            """
            (event_id ILIKE %s OR camera_id ILIKE %s OR zone ILIKE %s OR
             label ILIKE %s OR warning_type ILIKE %s OR reason ILIKE %s)
            """
        )
        params.extend([search, search, search, search, search, search])

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.extend([limit, offset])
    alerts = fetch_all(
        f"""
        SELECT event_id, camera_id, track_id, zone, status, label, score,
               warning_type, warning_level, review_status, snapshot_full,
               snapshot_face, recognition_threshold, detection_threshold, is_editable,
               deleted_at, deleted_by, delete_reason, created_at
        FROM unknown_events
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params),
    )
    return [normalize_alert_times(alert) for alert in alerts]


@router.get("/{event_id}")
def get_alert(event_id: str, current_user: CurrentUser = Depends(require_alert_read)) -> dict:
    alert = fetch_one("SELECT * FROM unknown_events WHERE event_id = %s", (event_id,))
    if not alert or (alert.get("deleted_at") and not has_permission(current_user, "alerts:delete")):
        raise HTTPException(status_code=404, detail="Alert not found")
    return normalize_alert_times(alert)


@router.delete("")
def delete_alerts_bulk(payload: AlertBulkDeleteRequest, current_user: CurrentUser = Depends(require_alert_delete)) -> dict:
    event_ids = [event_id.strip() for event_id in payload.event_ids if event_id.strip()]
    reason = normalize_delete_reason(payload.delete_reason, "Xoa hang loat tu giao dien quan tri")
    if not event_ids:
        raise HTTPException(status_code=400, detail="No alerts selected")

    deleted = 0
    for event_id in event_ids:
        before = get_alert(event_id, current_user)
        if before.get("deleted_at"):
            continue
        execute(
            """
            UPDATE unknown_events
            SET deleted_at = now(), deleted_by = %s, delete_reason = %s
            WHERE event_id = %s
            """,
            (current_user.username, reason, event_id),
        )
        after = get_alert(event_id, current_user)
        write_audit_log(current_user.username, "delete_alert_bulk", event_id, before, after)
        deleted += 1

    return {"status": "ok", "deleted": deleted}


@router.patch("/{event_id}/status")
def update_alert_status(event_id: str, review_status: str, note: str | None = None, current_user: CurrentUser = Depends(require_alert_update)) -> dict:
    execute(
        """
        UPDATE unknown_events
        SET review_status = %s,
            note = %s,
            reviewed_by = %s,
            reviewed_at = now()
        WHERE event_id = %s
        """,
        (review_status, note, current_user.username, event_id),
    )
    return get_alert(event_id, current_user)


@router.delete("/{event_id}")
def delete_alert(event_id: str, payload: AlertDeleteRequest, current_user: CurrentUser = Depends(require_alert_delete)) -> dict:
    reason = normalize_delete_reason(payload.delete_reason, "Xoa tu giao dien quan tri")
    before = get_alert(event_id, current_user)
    execute(
        """
        UPDATE unknown_events
        SET deleted_at = now(), deleted_by = %s, delete_reason = %s
        WHERE event_id = %s
        """,
        (current_user.username, reason, event_id),
    )
    after = get_alert(event_id, current_user)
    write_audit_log(current_user.username, "delete_alert", event_id, before, after)
    return {"status": "ok"}


@router.patch("/{event_id}/restore")
def restore_alert(event_id: str, payload: AlertRestoreRequest, current_user: CurrentUser = Depends(require_alert_restore)) -> dict:
    before = get_alert(event_id, current_user)
    execute(
        """
        UPDATE unknown_events
        SET deleted_at = NULL, deleted_by = NULL, delete_reason = NULL
        WHERE event_id = %s
        """,
        (event_id,),
    )
    after = get_alert(event_id, current_user)
    write_audit_log(current_user.username, "restore_alert", event_id, before, {**after, "restore_reason": payload.reason})
    return after


@router.patch("/{event_id}/edit-lock")
def set_alert_edit_lock(event_id: str, payload: AlertEditLockRequest, current_user: CurrentUser = Depends(require_alert_repair)) -> dict:
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Reason is required")
    before = get_alert(event_id, current_user)
    execute(
        """
        UPDATE unknown_events
        SET is_editable = %s,
            edit_unlocked_at = CASE WHEN %s THEN now() ELSE edit_unlocked_at END,
            edit_unlocked_by = CASE WHEN %s THEN %s ELSE edit_unlocked_by END,
            edit_lock_reason = %s
        WHERE event_id = %s
        """,
        (payload.is_editable, payload.is_editable, payload.is_editable, current_user.username, reason, event_id),
    )
    after = get_alert(event_id, current_user)
    write_audit_log(current_user.username, "unlock_alert_edit" if payload.is_editable else "lock_alert_edit", event_id, before, after)
    return after


@router.patch("/{event_id}")
def repair_alert(event_id: str, payload: AlertRepairRequest, current_user: CurrentUser = Depends(require_alert_repair)) -> dict:
    before = get_alert(event_id, current_user)
    if not before.get("is_editable"):
        raise HTTPException(status_code=409, detail="Alert history is locked")

    fields = []
    params: list[object] = []
    for field_name in ["camera_id", "zone", "warning_type", "warning_level", "review_status", "note", "reason"]:
        value = getattr(payload, field_name)
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)
    if not fields:
        return before

    params.append(event_id)
    execute(
        f"""
        UPDATE unknown_events
        SET {", ".join(fields)}
        WHERE event_id = %s
        """,
        tuple(params),
    )
    after = get_alert(event_id, current_user)
    write_audit_log(current_user.username, "repair_alert", event_id, before, after)
    return after


def normalize_delete_reason(reason: str | None, fallback: str) -> str:
    normalized = (reason or "").strip()
    return normalized or fallback


def write_audit_log(actor: str, action: str, event_id: str, before: dict | None, after: dict | None) -> None:
    execute(
        """
        INSERT INTO audit_logs (actor, action, entity_type, entity_id, before_data, after_data)
        VALUES (%s, %s, 'unknown_event', %s, %s, %s)
        """,
        (
            actor,
            action,
            event_id,
            Jsonb(json_safe(before)) if before is not None else None,
            Jsonb(json_safe(after)) if after is not None else None,
        ),
    )


def json_safe(value: dict) -> dict:
    return json.loads(json.dumps(value, default=json_default, ensure_ascii=False))


def json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def normalize_alert_times(alert: dict) -> dict:
    return {
        key: utc_datetime(value) if key.endswith("_at") and isinstance(value, datetime) else value
        for key, value in alert.items()
    }


def utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
