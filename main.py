import os, uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
import pathlib
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from backend.database import init_db, get_recent_logs, get_all_rules, get_all_rules_full, save_rule, delete_rule
from backend.rules_engine import start_scheduler, load_rules
from backend.agent import process
from simulator.devices_sim import get_all_states, DEVICE_STATES
from x10.x10_control import x10_status
from zigbee.zigbee_control import zigbee_status

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

class RuleIn(BaseModel):
    name: str
    time: str
    device: str
    action: str

@app.on_event("startup")
def startup():
    init_db()
    start_scheduler()
    print("[ZeroClaw] Startup complete.")

@app.get("/")
def root():
    return {"message": "ZeroClaw Smart Home v2 running", "docs": "/docs", "dashboard": "/dashboard"}

@app.post("/command")
def command(req: Cmd):
    """Send a natural language command to the AI agent."""
    return {"status": "ok", "response": process(req.user_id, req.message)}

@app.get("/status")
def status():
    """Quick device state map keyed by device ID."""
    return {"states": {k: v for k, v in get_all_states().items()}}

@app.get("/devices")
def devices():
    """Full device list with id, name, state, and protocol."""
    return [
        {"id": k, "name": v["name"], "state": v["state"], "protocol": v["protocol"]}
        for k, v in DEVICE_STATES.items()
    ]

@app.get("/x10")
def x10_info():
    """X10 controller status and house codes."""
    return {"info": x10_status()}

@app.get("/zigbee")
def zigbee_info():
    """Zigbee coordinator status and network info."""
    return {"info": zigbee_status()}

@app.get("/logs")
def logs():
    """Last 50 command log entries (newest first)."""
    return {"logs": get_recent_logs(50)}

@app.get("/rules")
def rules():
    """All enabled automation rules with full metadata."""
    return {"rules": get_all_rules_full()}

@app.post("/rules/add")
def add_rule(r: RuleIn):
    """Create a new time-based automation rule."""
    import json
    save_rule(r.name, "time", r.time, json.dumps({"device": r.device, "command": r.action}))
    load_rules()
    return {"status": "ok", "message": f"Rule '{r.name}' created"}

@app.delete("/rules/{rule_id}")
def remove_rule(rule_id: int):
    """Soft-delete a rule and reload the scheduler."""
    delete_rule(rule_id)
    load_rules()
    return {"status": "ok", "message": f"Rule {rule_id} deleted"}

@app.get("/dashboard")
def dashboard():
    """Serve the HTML dashboard."""
    for p in ["dashboard.html", "frontend/dashboard.html"]:
        if pathlib.Path(p).exists():
            return FileResponse(p)
    return {"error": "Dashboard not found"}

if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    print("=" * 55)
    print("  ZeroClaw Smart Home v2")
    print(f"  API:       http://localhost:{port}")
    print(f"  Docs:      http://localhost:{port}/docs")
    print(f"  Dashboard: http://localhost:{port}/dashboard")
    print("=" * 55)
    uvicorn.run("main:app", host=os.getenv("API_HOST", "0.0.0.0"), port=port, reload=True)
