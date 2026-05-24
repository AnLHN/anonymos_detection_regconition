from fastapi import APIRouter, Depends, HTTPException

from backend.auth.security import get_current_user
from backend.database.postgres import fetch_all, fetch_one

router = APIRouter(prefix="/employees", tags=["employees"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_employees(limit: int = 100, offset: int = 0) -> list[dict]:
    return fetch_all(
        """
        SELECT id, emp_code, name, department, photo_path, is_active
        FROM employees
        ORDER BY id
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )


@router.get("/{employee_id}")
def get_employee(employee_id: int) -> dict:
    employee = fetch_one(
        """
        SELECT id, emp_code, name, department, photo_path, is_active
        FROM employees
        WHERE id = %s
        """,
        (employee_id,),
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
