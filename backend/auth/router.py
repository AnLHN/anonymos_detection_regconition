from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.security import create_access_token, get_current_user
from backend.database.postgres import fetch_one

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(request: LoginRequest) -> dict:
    account = fetch_one(
        "SELECT id, username, password_hash, is_active FROM accounts WHERE username = %s",
        (request.username,),
    )
    if not account or not account["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if request.password != account["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token(account["username"]), "token_type": "bearer"}


@router.get("/me")
def me(current_user: str = Depends(get_current_user)) -> dict:
    return {"username": current_user}
