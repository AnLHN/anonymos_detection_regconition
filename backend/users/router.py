from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend.auth.login_events import read_login_events
from backend.auth.security import CurrentUser, require_permission, role_name, role_permissions
from backend.database.postgres import execute, fetch_all, fetch_one

router = APIRouter(prefix="/users", tags=["users"])
require_user_read = require_permission("users:read")
require_user_create = require_permission("users:create")
require_user_update = require_permission("users:update")
require_user_delete = require_permission("users:delete")

ALLOWED_ROLES = {0, 1, 5, 9}


class UserCreate(BaseModel):
    username: str
    email: str | None = None
    password: str
    role: int = 0
    is_active: bool = True


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: int | None = None
    is_active: bool | None = None


@router.get("")
def list_users(_current_user: CurrentUser = Depends(require_user_read)) -> list[dict[str, Any]]:
    users = fetch_all(
        """
        SELECT username, email, role, is_active, created_at, updated_at
        FROM accounts
        ORDER BY username
        """
    )
    for user in users:
        user["role_name"] = role_name(int(user.get("role") or 0))
        user["permissions"] = list(role_permissions(int(user.get("role") or 0)))
    return users


@router.get("/{username}/login-history")
def user_login_history(username: str, limit: int = 30, _current_user: CurrentUser = Depends(require_user_read)) -> list[dict[str, Any]]:
    public_user_data = public_user(username)
    if not public_user_data:
        raise HTTPException(status_code=404, detail="User not found")
    capped_limit = max(1, min(limit, 100))
    return read_login_events(username, capped_limit)


@router.post("")
def create_user(payload: UserCreate, current_user: CurrentUser = Depends(require_user_create)) -> dict[str, str]:
    username = payload.username.strip()
    email = normalize_email(payload.email)
    validate_user_input(username, payload.password, payload.role)
    try:
        execute(
            """
            INSERT INTO accounts (username, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username, email, payload.password, payload.role, payload.is_active),
        )
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Username or email already exists") from None
    write_user_audit(current_user.username, "create_user", username, None, public_user(username))
    return {"status": "ok"}


@router.patch("/{username}")
def update_user(username: str, payload: UserUpdate, current_user: CurrentUser = Depends(require_user_update)) -> dict[str, str]:
    before = public_user(username)
    if not before:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None:
        validate_role(payload.role)
    if payload.password is not None and len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if int(before.get("role") or 0) == 9 and (payload.role is not None and payload.role < 9 or payload.is_active is False):
        ensure_not_last_super(username)

    fields = []
    params: list[object] = []
    if payload.email is not None:
        fields.append("email = %s")
        params.append(normalize_email(payload.email))
    if payload.password is not None:
        fields.append("password_hash = %s")
        params.append(payload.password)
    if payload.role is not None:
        fields.append("role = %s")
        params.append(payload.role)
    if payload.is_active is not None:
        fields.append("is_active = %s")
        params.append(payload.is_active)
    if not fields:
        return {"status": "ok"}

    fields.append("updated_at = now()")
    params.append(username)
    try:
        execute(
            f"""
            UPDATE accounts
            SET {", ".join(fields)}
            WHERE username = %s
            """,
            tuple(params),
        )
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Username or email already exists") from None
    after = public_user(username)
    write_user_audit(current_user.username, "update_user", username, before, after)
    return {"status": "ok"}


@router.delete("/{username}")
def deactivate_user(username: str, current_user: CurrentUser = Depends(require_user_delete)) -> dict[str, str]:
    before = public_user(username)
    if not before:
        raise HTTPException(status_code=404, detail="User not found")
    if int(before.get("role") or 0) == 9:
        ensure_not_last_super(username)
    execute("UPDATE accounts SET is_active = false, updated_at = now() WHERE username = %s", (username,))
    after = public_user(username)
    write_user_audit(current_user.username, "deactivate_user", username, before, after)
    return {"status": "ok"}


def validate_user_input(username: str, password: str, role: int) -> None:
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    validate_role(role)


def validate_role(role: int) -> None:
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")


def normalize_email(email: str | None) -> str | None:
    value = (email or "").strip().lower()
    return value or None


def ensure_not_last_super(username: str) -> None:
    row = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM accounts
        WHERE role = 9 AND is_active = true AND username <> %s
        """,
        (username,),
    )
    if not row or int(row["total"]) < 1:
        raise HTTPException(status_code=409, detail="Cannot remove the last active admin_super")


def public_user(username: str) -> dict[str, Any] | None:
    user = fetch_one(
        """
        SELECT username, email, role, is_active, created_at, updated_at
        FROM accounts
        WHERE username = %s
        """,
        (username,),
    )
    if user:
        user["role_name"] = role_name(int(user.get("role") or 0))
        user["permissions"] = list(role_permissions(int(user.get("role") or 0)))
    return user


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value


def write_user_audit(actor: str, action: str, username: str, before: dict | None, after: dict | None) -> None:
    execute(
        """
        INSERT INTO audit_logs (actor, action, entity_type, entity_id, before_data, after_data)
        VALUES (%s, %s, 'account', %s, %s, %s)
        """,
        (
            actor,
            action,
            username,
            Jsonb(json_safe(before)) if before is not None else None,
            Jsonb(json_safe(after)) if after is not None else None,
        ),
    )
