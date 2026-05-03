# ZeroClaw Smart Home v2

AI-powered smart home automation platform with multi-protocol device support, natural language control via Claude AI, time-based automation rules, and a real-time web dashboard.

---

## Features

- **Claude AI Agent** — control devices with plain English commands
- **Multi-Protocol** — Tuya (primary), Zigbee, and X10 support
- **Rules Engine** — APScheduler-powered time-based automation
- **Real-Time Dashboard** — live device status, charts, and command center
- **SQLite Logging** — full audit trail of all commands and device events
- **FastAPI Backend** — RESTful API with auto-generated `/docs`

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Run the server
python main.py

# 4. Open dashboard
# Browser → http://localhost:8000/dashboard
# API Docs → http://localhost:8000/docs
```

---

## Project Structure

```
zeroclaw/
├── main.py                  # FastAPI app + all routes
├── dashboard.html           # Real-time web dashboard
├── requirements.txt
├── .env.example
├── smarthome.db             # Created automatically on first run
├── backend/
│   ├── database.py          # SQLite helpers (log, rules, events)
│   ├── agent.py             # Claude AI command parser + executor
│   └── rules_engine.py      # APScheduler automation engine
├── simulator/
│   └── devices_sim.py       # In-memory device state store (12 devices)
├── x10/
│   └── x10_control.py       # X10 protocol adapter (stub)
└── zigbee/
    └── zigbee_control.py    # Zigbee protocol adapter (stub)
```

---

## API Reference

| Method   | Path            | Description                            |
|----------|-----------------|----------------------------------------|
| GET      | `/`             | Health check                           |
| POST     | `/command`      | AI natural language command            |
| GET      | `/status`       | Quick device state map                 |
| GET      | `/devices`      | Full device list with protocols        |
| GET      | `/logs`         | Last 50 command log entries            |
| GET      | `/rules`        | All active automation rules            |
| POST     | `/rules/add`    | Create a new time-based rule           |
| DELETE   | `/rules/{id}`   | Delete a rule                          |
| GET      | `/x10`          | X10 controller status                  |
| GET      | `/zigbee`       | Zigbee coordinator status              |
| GET      | `/dashboard`    | Serve the HTML dashboard               |

### Example: Send a command

```bash
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "message": "Turn on the living room lights"}'
```

### Example: Create an automation rule

```bash
curl -X POST http://localhost:8000/rules/add \
  -H "Content-Type: application/json" \
  -d '{"name": "Morning lights", "time": "07:30", "device": "living_room_light", "action": "on"}'
```

---

## Database Schema

| Table             | Purpose                                |
|-------------------|----------------------------------------|
| `command_log`     | All AI commands with timestamps        |
| `automation_rules`| Scheduled automation rules             |
| `behavior_log`    | Hourly device usage patterns           |
| `device_events`   | State change history per device        |

---

## Connecting Real Devices

### Tuya
Set `TUYA_CLIENT_ID`, `TUYA_CLIENT_SECRET`, and `TUYA_REGION` in `.env`, then replace simulator calls in `agent.py` with `tinytuya` SDK calls.

### Zigbee
Set `ZIGBEE_SERIAL_PORT` in `.env` and update `zigbee/zigbee_control.py` to use your coordinator (CC2531, Sonoff Zigbee 3.0, etc.) via zigbee2mqtt or ZHA.

### X10
Set `X10_SERIAL_PORT` in `.env` and update `x10/x10_control.py` to use your CM11A or CM17A serial interface.

---

## License

MIT — see LICENSE for details.
