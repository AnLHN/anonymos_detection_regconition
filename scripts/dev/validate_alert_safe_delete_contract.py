from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.alerts.router import AlertBulkDeleteRequest, AlertDeleteRequest, normalize_delete_reason

ALERTS_PANEL = ROOT / "frontend" / "src" / "components" / "AlertsPanel.tsx"
GLOBALS_CSS = ROOT / "frontend" / "src" / "app" / "globals.css"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    single = AlertDeleteRequest()
    bulk = AlertBulkDeleteRequest(event_ids=["event-1"])
    assert_true(single.delete_reason is None, "single delete reason should be optional")
    assert_true(bulk.delete_reason is None, "bulk delete reason should be optional")
    assert_true(normalize_delete_reason(None, "fallback") == "fallback", "missing delete reason should use fallback")
    assert_true(normalize_delete_reason("  custom  ", "fallback") == "custom", "provided delete reason should be trimmed")

    alerts_panel = ALERTS_PANEL.read_text(encoding="utf-8")
    globals_css = GLOBALS_CSS.read_text(encoding="utf-8")

    forbidden_panel_tokens = [
        "window.confirm",
        "deleteReason",
        "deleteConfirm",
        "bulkDeleteReason",
        "super-admin-panel",
        "delete-box",
        "repair-form",
    ]
    for token in forbidden_panel_tokens:
        assert_true(token not in alerts_panel, f"AlertsPanel should not contain legacy token: {token}")

    required_panel_tokens = [
        "pendingDelete",
        "alert-confirm-dialog",
        "alert-row-delete",
        "deleteDialogTitle",
        "deleteDialogDescription",
    ]
    for token in required_panel_tokens:
        assert_true(token in alerts_panel, f"AlertsPanel should contain safe-delete token: {token}")

    forbidden_css_tokens = [
        ".super-admin-panel",
        ".delete-box",
        ".repair-form",
    ]
    for token in forbidden_css_tokens:
        assert_true(token not in globals_css, f"globals.css should not contain legacy alert admin CSS: {token}")

    required_css_tokens = [
        ".alert-confirm-dialog",
        ".alert-row-delete",
        ".alert-bulk-bar.is-compact",
    ]
    for token in required_css_tokens:
        assert_true(token in globals_css, f"globals.css should contain safe-delete CSS: {token}")

    print("alert_safe_delete_contract: ok")


if __name__ == "__main__":
    main()
