ZIGBEE_DEVICES = {
    "zigbee_bulb": {"name": "Zigbee Smart Bulb"},
    "zigbee_sensor": {"name": "Zigbee Motion Sensor"},
    "zigbee_plug": {"name": "Zigbee Smart Plug"}
}
ZIGBEE_STATES = {k: "off" for k in ZIGBEE_DEVICES}

def zigbee_turn_on(d):
    if d not in ZIGBEE_DEVICES:
        return False
    ZIGBEE_STATES[d] = "on"
    return True

def zigbee_turn_off(d):
    if d not in ZIGBEE_DEVICES:
        return False
    ZIGBEE_STATES[d] = "off"
    return True

def zigbee_status():
    lines = ["Zigbee (SIMULATOR):"]
    for k, d in ZIGBEE_DEVICES.items():
        state = "ON" if ZIGBEE_STATES[k] == "on" else "off"
        lines.append(f"  [{state}] {k}: {d['name']}")
    return "\n".join(lines)

def zigbee_send(device_id, command):
    return {"status": "ok", "device_id": device_id, "command": command}