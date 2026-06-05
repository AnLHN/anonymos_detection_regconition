import sys
from datetime import datetime
from pathlib import Path

import cv2
import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.security import get_current_user, require_permission
from backend.cameras.annotated_stream import get_latest_camera_frame
from backend.database.postgres import fetch_all, fetch_one
from backend.config import POSTGRES_DSN

ROOT = Path(__file__).resolve().parents[2]
AI_WORKER_DIR = ROOT / "ai_worker"
if str(AI_WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(AI_WORKER_DIR))

from config import MIN_DETECTION_SCORE, MIN_FACE_HEIGHT, MIN_FACE_WIDTH
from insightface_recognizer import FaceEmbedding, InsightFaceRecognizer
from qdrant_http_service import QdrantHttpService

router = APIRouter(prefix="/employees", tags=["employees"], dependencies=[Depends(get_current_user)])
require_employee_read = require_permission("employees:read")
require_employee_create = require_permission("employees:create")
EMPLOYEE_PHOTO_DIR = ROOT / "storage" / "employees"


class EmployeeEnrollRequest(BaseModel):
    emp_code: str
    name: str
    department: str
    camera_id: str


@router.get("")
def list_employees(limit: int = 100, offset: int = 0, _current_user=Depends(require_employee_read)) -> list[dict]:
    return fetch_all(
        """
        SELECT id, emp_code, name, department, photo_path, is_active
        FROM employees
        ORDER BY id
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )


@router.post("/enroll-from-camera")
def enroll_employee_from_camera(payload: EmployeeEnrollRequest, _current_user=Depends(require_employee_create)) -> dict:
    emp_code = payload.emp_code.strip()
    name = payload.name.strip()
    department = payload.department.strip()
    camera_id = payload.camera_id.strip()
    if not emp_code:
        raise HTTPException(status_code=400, detail="Mã nhân viên là bắt buộc")
    if not name:
        raise HTTPException(status_code=400, detail="Tên nhân viên là bắt buộc")
    if not camera_id:
        raise HTTPException(status_code=400, detail="Cần chọn camera để chụp khuôn mặt")
    if fetch_one("SELECT id FROM employees WHERE emp_code = %s", (emp_code,)):
        raise HTTPException(status_code=409, detail="Mã nhân viên đã tồn tại")

    camera = fetch_one(
        """
        SELECT camera_id, source_url, source_type, is_active, config
        FROM camera_sources
        WHERE camera_id = %s
        """,
        (camera_id,),
    )
    if not camera:
        raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    if not camera["is_active"]:
        raise HTTPException(status_code=400, detail="Camera đang tắt")
    if camera["source_type"] != "rtsp":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ enroll từ camera RTSP")

    frame = get_latest_camera_frame(camera["camera_id"], camera["source_url"], camera.get("config") or {}, timeout=10.0)
    if frame is None:
        raise HTTPException(status_code=503, detail="Chưa có frame mới từ camera worker")

    faces = [face for face in InsightFaceRecognizer().extract_embeddings(frame) if is_good_enrollment_face(face)]
    if not faces:
        raise HTTPException(status_code=400, detail="Không thấy khuôn mặt hợp lệ trong khung hình")
    if len(faces) > 1:
        raise HTTPException(status_code=400, detail="Chỉ được có 1 khuôn mặt khi thêm nhân viên")

    face = faces[0]
    photo_path = save_employee_face(frame, face, emp_code)
    employee = insert_employee(emp_code, name, department, photo_path)
    qdrant_payload = {
        "employee_id": employee["id"],
        "emp_code": employee["emp_code"],
        "name": employee["name"],
        "department": employee["department"],
        "is_active": employee["is_active"],
    }
    try:
        QdrantHttpService().upsert_employee_face(employee["id"], face.vector, qdrant_payload)
    except Exception as error:
        deactivate_employee(employee["id"])
        raise HTTPException(status_code=500, detail=f"Không enroll được khuôn mặt vào Qdrant: {error}") from error
    return employee


@router.get("/{employee_id}")
def get_employee(employee_id: int, _current_user=Depends(require_employee_read)) -> dict:
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


def is_good_enrollment_face(face: FaceEmbedding) -> bool:
    x1, y1, x2, y2 = face.bbox
    return (
        face.det_score >= MIN_DETECTION_SCORE
        and x2 - x1 >= MIN_FACE_WIDTH
        and y2 - y1 >= MIN_FACE_HEIGHT
    )


def save_employee_face(frame, face: FaceEmbedding, emp_code: str) -> str:
    EMPLOYEE_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    safe_code = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in emp_code)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = EMPLOYEE_PHOTO_DIR / f"{safe_code}_{timestamp}_face.jpg"
    x1, y1, x2, y2 = face.bbox
    height, width = frame.shape[:2]
    x1 = max(0, min(width, x1))
    x2 = max(0, min(width, x2))
    y1 = max(0, min(height, y1))
    y2 = max(0, min(height, y2))
    crop = frame[y1:y2, x1:x2]
    cv2.imwrite(str(path), crop)
    return str(path)


def insert_employee(emp_code: str, name: str, department: str, photo_path: str) -> dict:
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO employees (emp_code, name, department, photo_path, is_active)
                VALUES (%s, %s, %s, %s, true)
                RETURNING id, emp_code, name, department, photo_path, is_active
                """,
                (emp_code, name, department, photo_path),
            )
            row = cur.fetchone()
        conn.commit()
    return {
        "id": row[0],
        "emp_code": row[1],
        "name": row[2],
        "department": row[3],
        "photo_path": row[4],
        "is_active": row[5],
    }


def deactivate_employee(employee_id: int) -> None:
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE employees SET is_active = false, updated_at = now() WHERE id = %s", (employee_id,))
        conn.commit()
