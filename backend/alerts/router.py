from fastapi import APIRouter, Depends, HTTPException

from backend.auth.security import get_current_user
from backend.database.postgres import execute, fetch_all, fetch_one

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_alerts(limit: int = 50, offset: int = 0) -> list[dict]:
    return fetch_all(
        """
        SELECT event_id, camera_id, track_id, zone, status, label, score,
               warning_type, warning_level, review_status, snapshot_full,
               snapshot_face, created_at
        FROM unknown_events
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )


@router.get("/{event_id}")
def get_alert(event_id: str) -> dict:
    alert = fetch_one("SELECT * FROM unknown_events WHERE event_id = %s", (event_id,))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{event_id}/status")
def update_alert_status(event_id: str, review_status: str, note: str | None = None, current_user: str = Depends(get_current_user)) -> dict:
    execute(
        """
        UPDATE unknown_events
        SET review_status = %s,
            note = %s,
            reviewed_by = %s,
            reviewed_at = now()
        WHERE event_id = %s
        """,
        (review_status, note, current_user, event_id),
    )
    return get_alert(event_id)
