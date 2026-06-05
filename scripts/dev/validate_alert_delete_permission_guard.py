from __future__ import annotations

import sys
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.alerts.router import router
from backend.auth.security import CurrentUser, require_admin_super


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def route_dependency_names(path: str, method: str) -> list[str]:
    for route in router.routes:
        if getattr(route, "path", None) == path and method.upper() in getattr(route, "methods", set()):
            return [dependency.call.__name__ for dependency in route.dependant.dependencies if dependency.call]
    raise AssertionError(f"Route not found: {method} {path}")


def assert_forbidden(user: CurrentUser) -> None:
    try:
        require_admin_super(user)
    except HTTPException as exc:
        assert_true(exc.status_code == 403, f"expected 403 for role {user.role}")
        return
    raise AssertionError(f"role {user.role} should not pass require_admin_super")


def main() -> None:
    assert_true("require_admin_super" in route_dependency_names("/alerts", "DELETE"), "bulk delete must require admin_super")
    assert_true("require_admin_super" in route_dependency_names("/alerts/{event_id}", "DELETE"), "single delete must require admin_super")

    assert_forbidden(CurrentUser(username="viewer", role=0, role_name="viewer"))
    assert_forbidden(CurrentUser(username="operator", role=1, role_name="operator"))
    assert_forbidden(CurrentUser(username="admin", role=5, role_name="admin"))

    allowed = CurrentUser(username="admin_super", role=9, role_name="admin_super")
    assert_true(require_admin_super(allowed) == allowed, "admin_super should pass require_admin_super")

    print("alert_delete_permission_guard: ok")


if __name__ == "__main__":
    main()
