
DEVICE_STATES = {
    'light':         {'state': 'off', 'name': 'Living Room Light',    'protocol': 'tuya'},
    'socket':        {'state': 'off', 'name': 'Smart Socket',         'protocol': 'tuya'},
    'fan':           {'state': 'off', 'name': 'Ceiling Fan',          'protocol': 'tuya'},
    'tv':            {'state': 'off', 'name': 'Smart TV',             'protocol': 'tuya'},
    'x10_lamp':      {'state': 'off', 'name': 'X10 Bedroom Lamp',     'protocol': 'x10'},
    'x10_appliance': {'state': 'off', 'name': 'X10 Appliance Module', 'protocol': 'x10'},
    'zigbee_bulb':   {'state': 'off', 'name': 'Zigbee Smart Bulb',    'protocol': 'zigbee'},
    'zigbee_sensor': {'state': 'off', 'name': 'Zigbee Motion Sensor', 'protocol': 'zigbee'},
    'zigbee_plug':   {'state': 'off', 'name': 'Zigbee Smart Plug',    'protocol': 'zigbee'},
}
ALIASES = {
    'lights': 'light', 'lamp': 'light', 'bulb': 'light',
    'plug': 'socket', 'ceiling fan': 'fan', 'television': 'tv',
    'bedroom lamp': 'x10_lamp', 'x10': 'x10_lamp',
    'zigbee light': 'zigbee_bulb', 'smart bulb': 'zigbee_bulb',
    'motion': 'zigbee_sensor', 'sensor': 'zigbee_sensor',
    'zigbee socket': 'zigbee_plug',
}
def turn_on(n):
    n = ALIASES.get(n.lower().strip(), n.lower().strip())
    if n in DEVICE_STATES: DEVICE_STATES[n]["state"] = "on"; return True
    return False
def turn_off(n):
    n = ALIASES.get(n.lower().strip(), n.lower().strip())
    if n in DEVICE_STATES: DEVICE_STATES[n]["state"] = "off"; return True
    return False
def turn_off_all():
    for n in DEVICE_STATES: DEVICE_STATES[n]["state"] = "off"
def get_state(n):
    n = ALIASES.get(n.lower().strip(), n.lower().strip())
    return DEVICE_STATES.get(n, {}).get("state", "unknown")
def get_all_states():
    return {k: v["state"] for k, v in DEVICE_STATES.items()}
def resolve_device(n):
    n = n.lower().strip()
    return n if n in DEVICE_STATES else ALIASES.get(n)
