# home assistant control
# references:
# - Home Assistant REST API
# - Python requests library (HTTP calls)

import os, requests
from dotenv import load_dotenv
load_dotenv()

HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")

def ha_available():
    if not HA_TOKEN:
        return False

    try:
        # check API status (basic GET request)
        r = requests.get(
            HA_URL + "/api/",
            headers={"Authorization": "Bearer " + HA_TOKEN},
            timeout=2
        )
        return r.status_code == 200
    except:
        return False

def ha_turn_on(device):
    try:
        # send POST request to turn on device
        requests.post(
            HA_URL + "/api/services/switch/turn_on",
            headers={"Authorization": "Bearer " + HA_TOKEN},
            json={"entity_id": device}
        )
    except Exception as e:
        print("HA error:", e)

def ha_turn_off(device):
    try:
        # send POST request to turn off device
        requests.post(
            HA_URL + "/api/services/switch/turn_off",
            headers={"Authorization": "Bearer " + HA_TOKEN},
            json={"entity_id": device}
        )
    except Exception as e:
        print("HA error:", e)