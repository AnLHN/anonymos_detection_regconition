import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.errors import UniqueViolation
from pydantic import BaseModel

from backend.auth.login_events import write_login_event
from backend.auth.security import CurrentUser, create_access_token, get_current_user
from backend.database.postgres import execute, fetch_one

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


@router.post("/login")
def login(request: LoginRequest, http_request: Request) -> dict:
    account = fetch_one(
        "SELECT id, username, password_hash, role, is_active FROM accounts WHERE username = %s",
        (request.username,),
    )
    if not account or not account["is_active"]:
        write_login_event(request.username.strip(), "login", False, http_request)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(request.password, account["password_hash"]):
        write_login_event(account["username"], "login", False, http_request)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    write_login_event(account["username"], "login", True, http_request)
    return {"access_token": create_access_token(account["username"], int(account.get("role") or 0)), "token_type": "bearer"}


@router.post("/register")
def register(request: RegisterRequest) -> dict:
    username = request.username.strip()
    email = request.email.strip().lower()
    password = request.password
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    try:
        execute(
            """
            INSERT INTO accounts (id, username, email, password_hash, role, is_active)
            VALUES ((SELECT COALESCE(MAX(id), 0) + 1 FROM accounts), %s, %s, %s, 0, true)
            """,
            (username, email, password),
        )
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Username or email already exists") from None
    token = create_access_token(username, 0)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "username": current_user.username,
        "role": current_user.role,
        "role_name": current_user.role_name,
        "permissions": list(current_user.permissions),
    }


@router.post("/logout")
def logout(http_request: Request, current_user: CurrentUser = Depends(get_current_user)) -> dict:
    write_login_event(current_user.username, "logout", True, http_request)
    return {"status": "ok"}


def verify_password(password: str, stored_password: str) -> bool:
    if password == stored_password:
        return True
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == stored_password
