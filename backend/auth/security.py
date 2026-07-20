from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET
from backend.database.postgres import fetch_one

security = HTTPBearer()

ROLE_NAMES = {
    5: "sub_admin",
    9: "admin",
}

ALL_PERMISSIONS = {
    "alerts:read",
    "alerts:update",
    "alerts:delete",
    "alerts:restore",
    "alerts:repair",
    "cameras:read",
    "cameras:create",
    "cameras:update",
    "rules:read",
    "rules:create",
    "rules:update",
    "employees:read",
    "employees:create",
    "users:read",
    "users:create",
    "users:update",
    "users:delete",
    "system:read",
}

ROLE_PERMISSIONS = {
    5: {
        "alerts:read",
        "alerts:update",
        "cameras:read",
        "cameras:create",
        "cameras:update",
        "rules:read",
        "rules:create",
        "rules:update",
        "employees:read",
        "employees:create",
        "system:read",
    },
    9: ALL_PERMISSIONS,
}


@dataclass(frozen=True)
class CurrentUser:
    username: str
    role: int
    role_name: str
    permissions: tuple[str, ...]


def create_access_token(subject: str, role: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    if role is not None:
        payload["role"] = role
        payload["role_name"] = role_name(role)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> CurrentUser:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    account = fetch_one(
        "SELECT username, role, is_active FROM accounts WHERE username = %s",
        (str(subject),),
    )
    if not account or not account["is_active"]:
        raise HTTPException(status_code=401, detail="Inactive or missing account")
    role = int(account.get("role") or 0)
    return CurrentUser(username=account["username"], role=role, role_name=role_name(role), permissions=role_permissions(role))


def require_login(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return current_user


def require_operator(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return require_role(current_user, 1)


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return require_role(current_user, 5)


def require_admin_super(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return require_role(current_user, 9)


def require_permission(permission: str):
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_permission(current_user, permission):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return current_user

    return dependency


def require_role(current_user: CurrentUser, minimum_role: int) -> CurrentUser:
    if current_user.role < minimum_role:
        raise HTTPException(status_code=403, detail="Insufficient permission")
    return current_user


def has_permission(current_user: CurrentUser, permission: str) -> bool:
    return permission in current_user.permissions


def role_permissions(role: int) -> tuple[str, ...]:
    allowed: set[str] = set()
    for minimum_role, permissions in ROLE_PERMISSIONS.items():
        if role >= minimum_role:
            allowed.update(permissions)
    return tuple(sorted(allowed))


def role_name(role: int) -> str:
    return ROLE_NAMES.get(role, "viewer")
