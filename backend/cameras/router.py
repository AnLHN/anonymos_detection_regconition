from fastapi import APIRouter, Depends

from backend.auth.security import get_current_user
from backend.database.postgres import fetch_all

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_cameras() -> list[dict]:
    return fetch_all(
        """
        SELECT camera_id, name, source_type, source_url, location, is_active, config, created_at, updated_at
        FROM camera_sources
        ORDER BY camera_id
        """
    )
