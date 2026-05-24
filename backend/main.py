from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.alerts.router import router as alerts_router
from backend.auth.router import router as auth_router
from backend.cameras.router import router as cameras_router
from backend.employees.router import router as employees_router
from backend.rules.router import router as rules_router
from backend.system.router import router as system_router

app = FastAPI(title="Unknown Detection API")

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


@app.get("/")
def root() -> dict:
    return {"name": "Unknown Detection API", "status": "running"}
