print("Still integrating this...update on code will be posted here, Soon")

# app/hardware/light.py

from app.db.database import update_device, log_event

def turn_on():
    print("[SIM] Light ON")
    update_device("light", "ON")
    log_event("Light turned ON")

def turn_off():
    print("[SIM] Light OFF")
    update_device("light", "OFF")
    log_event("Light turned OFF")
    