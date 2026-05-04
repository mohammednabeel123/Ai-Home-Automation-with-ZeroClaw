import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from app.db.database import init_db, get_devices, log_event, update_device
from app.hardware.fan import turn_on as fan_on_hw, turn_off as fan_off_hw
from app.hardware.light import turn_on as light_on_hw, turn_off as light_off_hw


# TEMP: old modules commented until moved properly
# from app.services.agent import process
# from app.services.rules_engine import start_scheduler, load_rules
# from app.protocols.x10_control import x10_status
# from app.protocols.zigbee_control import zigbee_status

load_dotenv()

app = FastAPI(title="ZeroClaw Smart Home v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Cmd(BaseModel):
    user_id: str = "default"
    message: str


@app.on_event("startup")
def startup():
    init_db()
    print("[ZeroClaw] Startup complete.")


@app.get("/")
def root():
    return {
        "message": "ZeroClaw Smart Home v2 running",
        "docs": "/docs",
        "dashboard": "/dashboard"
    }


@app.post("/command")
def command(req: Cmd):
    log_event(f"Command received from {req.user_id}: {req.message}")

    # temporary response until agent.py is connected
    return {
        "status": "ok",
        "response": f"Command received: {req.message}"
    }


@app.get("/status")
def status():
    return {
        "status": "online",
        "devices": get_devices()
    }


@app.post("/fan/on")
def fan_on():
    update_device("fan", "ON")
    log_event("Fan turned ON")
    return {"status": "ok", "device": "fan", "state": "ON"}


@app.post("/fan/off")
def fan_off():
    update_device("fan", "OFF")
    log_event("Fan turned OFF")
    return {"status": "ok", "device": "fan", "state": "OFF"}


@app.post("/light/on")
def light_on():
    update_device("light", "ON")
    log_event("Light turned ON")
    return {"status": "ok", "device": "light", "state": "ON"}


@app.post("/light/off")
def light_off():
    update_device("light", "OFF")
    log_event("Light turned OFF")
    return {"status": "ok", "device": "light", "state": "OFF"}


@app.get("/dashboard")
def dashboard():
    dashboard_path = Path("app/templates/dashboard.html")

    if dashboard_path.exists():
        return FileResponse(dashboard_path)

    return {"error": "Dashboard not found"}


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))

    print("=" * 55)
    print("  ZeroClaw Smart Home v2")
    print(f"  API:       http://localhost:{port}")
    print(f"  Docs:      http://localhost:{port}/docs")
    print(f"  Dashboard: http://localhost:{port}/dashboard")
    print("=" * 55)

    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=port,
        reload=True
    )