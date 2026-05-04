print("Still integrating this...update on code will be posted here, Soon")
# app/hardware/fan.py

from app.db.database import update_device, log_event

def turn_on():
    print("[SIM] Fan ON")
    update_device("fan", "ON")
    log_event("Fan turned ON")

def turn_off():
    print("[SIM] Fan OFF")
    update_device("fan", "OFF")
    log_event("Fan turned OFF")
    