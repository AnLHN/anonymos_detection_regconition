import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from backend.auth.security import get_current_user, require_permission
from backend.database.postgres import execute, fetch_all

router = APIRouter(prefix="/rules", tags=["rules"], dependencies=[Depends(get_current_user)])
require_rule_read = require_permission("rules:read")
require_rule_create = require_permission("rules:create")
require_rule_update = require_permission("rules:update")

ALLOWED_WARNING_LEVELS = {"low", "medium", "high", "critical"}
RULE_CODE_PATTERN = re.compile(r"^[a-z0-9_-]+$")


class RuleCreate(BaseModel):
    rule_code: str
    name: str
    warning_level: str
    is_enabled: bool = True
    config: dict[str, Any] = {}


class RuleUpdate(BaseModel):
    warning_level: str | None = None
    is_enabled: bool | None = None
    config: dict[str, Any] | None = None


@router.get("")
def list_rules(_current_user=Depends(require_rule_read)) -> list[dict]:
    return fetch_all(
        """
        SELECT rule_code, name, warning_level, is_enabled, config, created_at, updated_at
        FROM alert_rules
        ORDER BY rule_code
        """
    )


@router.post("")
def create_rule(payload: RuleCreate, _current_user=Depends(require_rule_create)) -> dict[str, str]:
    rule_code = payload.rule_code.strip()
    name = payload.name.strip()
    validate_rule_code(rule_code)
    validate_warning_level(payload.warning_level)
    if not name:
        raise HTTPException(status_code=400, detail="Rule name is required")
    try:
        execute(
            """
            INSERT INTO alert_rules (rule_code, name, warning_level, is_enabled, config)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (rule_code, name, payload.warning_level, payload.is_enabled, Jsonb(payload.config)),
        )
    except UniqueViolation:
        raise HTTPException(status_code=409, detail="Rule code already exists") from None
    return {"status": "ok"}


@router.patch("/{rule_code}")
def update_rule(rule_code: str, payload: RuleUpdate, _current_user=Depends(require_rule_update)) -> dict[str, str]:
    fields = []
    params = []
    if payload.warning_level is not None:
        validate_warning_level(payload.warning_level)
        fields.append("warning_level = %s")
        params.append(payload.warning_level)
    if payload.is_enabled is not None:
        fields.append("is_enabled = %s")
        params.append(payload.is_enabled)
    if payload.config is not None:
        fields.append("config = %s")
        params.append(Jsonb(payload.config))
    if not fields:
        return {"status": "ok"}

    fields.append("updated_at = now()")
    params.append(rule_code)
    execute(
        f"""
        UPDATE alert_rules
        SET {", ".join(fields)}
        WHERE rule_code = %s
        """,
        tuple(params),
    )
    return {"status": "ok"}


def validate_rule_code(rule_code: str) -> None:
    if not rule_code or not RULE_CODE_PATTERN.fullmatch(rule_code):
        raise HTTPException(status_code=400, detail="Rule code must use lowercase letters, numbers, underscore, or dash")


def validate_warning_level(level: str) -> None:
    if level not in ALLOWED_WARNING_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid warning level")
