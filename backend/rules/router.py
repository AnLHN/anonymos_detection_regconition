from fastapi import APIRouter, Depends

from backend.auth.security import get_current_user
from backend.database.postgres import fetch_all

router = APIRouter(prefix="/rules", tags=["rules"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_rules() -> list[dict]:
    return fetch_all(
        """
        SELECT rule_code, name, warning_level, is_enabled, config, created_at, updated_at
        FROM alert_rules
        ORDER BY rule_code
        """
    )
