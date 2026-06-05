from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.alerts.router import router as alerts_router
from backend.auth.router import router as auth_router
from backend.cameras.router import router as cameras_router
from backend.employees.router import router as employees_router
from backend.metrics import MetricsMiddleware, metrics_response
from backend.rules.router import router as rules_router
from backend.system.router import router as system_router
from backend.users.router import router as users_router

app = FastAPI(title="Unknown Detection API")
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(alerts_router)
app.include_router(cameras_router)
app.include_router(employees_router)
app.include_router(rules_router)
app.include_router(system_router)
app.include_router(users_router)

ROOT_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = ROOT_DIR / "storage"
SNAPSHOT_DIRS = [
    STORAGE_DIR / "snapshots",
    ROOT_DIR / "ai_worker" / "outputs" / "snapshots",
    ROOT_DIR / "unknown_detection_system" / "outputs" / "snapshots",
]

app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")


@app.get("/snapshots/{filename}")
def get_snapshot(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid snapshot filename")

    for snapshot_dir in SNAPSHOT_DIRS:
        path = snapshot_dir / safe_name
        if path.is_file():
            return FileResponse(path)

    raise HTTPException(status_code=404, detail="Snapshot not found")


@app.get("/")
def root() -> dict:
    return {"name": "Unknown Detection API", "status": "running"}


@app.get("/metrics", include_in_schema=False)
def metrics() -> object:
    return metrics_response()
