from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EmployeePayload:
    employee_id: int
    emp_code: str
    name: str
    department: str
    is_active: bool

    @classmethod
    def from_qdrant_payload(cls, payload: dict[str, Any]) -> "EmployeePayload":
        return cls(
            employee_id=int(payload["employee_id"]),
            emp_code=str(payload.get("emp_code", "")),
            name=str(payload["name"]),
            department=str(payload.get("department", "")),
            is_active=bool(payload.get("is_active", True)),
        )


@dataclass(frozen=True)
class SearchCandidate:
    point_id: int | str
    score: float
    payload: EmployeePayload


@dataclass(frozen=True)
class RecognitionResult:
    status: str
    label: str
    score: float | None
    employee: EmployeePayload | None
    candidates: list[SearchCandidate]
