from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.alerts import router as alerts_router
from backend.auth.security import CurrentUser


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


@contextmanager
def patched_alert_router():
    original_execute = alerts_router.execute
    original_get_alert = alerts_router.get_alert
    original_write_audit_log = alerts_router.write_audit_log

    deleted_ids: set[str] = {"already-deleted"}
    execute_calls: list[tuple[str, tuple[Any, ...]]] = []
    audit_calls: list[tuple[str, str, str, dict | None, dict | None]] = []

    def fake_execute(query: str, params: tuple[Any, ...]) -> None:
        execute_calls.append((query, params))
        deleted_ids.add(str(params[-1]))

    def fake_get_alert(event_id: str, _current_user: CurrentUser) -> dict:
        return {
            "event_id": event_id,
            "deleted_at": "2026-06-04T00:00:00+00:00" if event_id in deleted_ids else None,
            "delete_reason": None,
        }

    def fake_write_audit_log(actor: str, action: str, event_id: str, before: dict | None, after: dict | None) -> None:
        audit_calls.append((actor, action, event_id, before, after))

    alerts_router.execute = fake_execute
    alerts_router.get_alert = fake_get_alert
    alerts_router.write_audit_log = fake_write_audit_log
    try:
        yield execute_calls, audit_calls
    finally:
        alerts_router.execute = original_execute
        alerts_router.get_alert = original_get_alert
        alerts_router.write_audit_log = original_write_audit_log


def main() -> None:
    current_user = CurrentUser(username="admin_super", role=9, role_name="admin_super")
    with patched_alert_router() as (execute_calls, audit_calls):
        single_result = alerts_router.delete_alert(
            "single-1",
            alerts_router.AlertDeleteRequest(),
            current_user,
        )
        assert_true(single_result == {"status": "ok"}, "single delete should return ok")
        assert_true(len(execute_calls) == 1, "single delete should execute one update")
        assert_true(execute_calls[0][1] == ("admin_super", "Xoa tu giao dien quan tri", "single-1"), "single delete should use fallback reason")
        assert_true(audit_calls[0][1] == "delete_alert", "single delete should write delete audit")

        bulk_result = alerts_router.delete_alerts_bulk(
            alerts_router.AlertBulkDeleteRequest(event_ids=["bulk-1", " ", "already-deleted", "bulk-2"]),
            current_user,
        )
        assert_true(bulk_result == {"status": "ok", "deleted": 2}, "bulk delete should skip blanks and already-deleted alerts")
        assert_true(len(execute_calls) == 3, "bulk delete should add two updates")
        assert_true(execute_calls[1][1] == ("admin_super", "Xoa hang loat tu giao dien quan tri", "bulk-1"), "bulk delete should use fallback reason")
        assert_true(execute_calls[2][1] == ("admin_super", "Xoa hang loat tu giao dien quan tri", "bulk-2"), "bulk delete should use fallback reason for every item")
        assert_true([call[1] for call in audit_calls] == ["delete_alert", "delete_alert_bulk", "delete_alert_bulk"], "delete audits should be written in order")

    print("alert_delete_backend_flow: ok")


if __name__ == "__main__":
    main()
