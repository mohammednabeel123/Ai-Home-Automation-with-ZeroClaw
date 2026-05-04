# 🧠Ai Home Automation with ZeroClaw Smart Home

An AI-powered smart home system that allows users to control real devices using natural language, automation rules, and a real-time dashboard.

This project combines **AI, backend systems, and hardware control** into a complete smart home platform.

---

## 🚀 What Makes It Special

* Control devices using plain English (AI-powered)
* Automate actions based on time or behavior
* Monitor everything in real-time
* Designed to work with real hardware (fan + light)

---

## 🔥 Features

### 🧠 AI Agent (Natural Language Control)

Send commands like:

> “Turn on the light”

…and the system executes them.

---

### ⏱ Automation Engine

Create rules like:

> “Turn on the fan at 7 PM”

---

### 🔌 Multi-Protocol Support

Designed to support:

* Tuya (primary)
* Zigbee
* X10

---

### 📊 Live Dashboard

Web interface to monitor and control devices in real time.

---

### 📜 Full Activity Logging

Every command and device action is stored.

---

### ⚡ FastAPI Backend

Clean API with interactive docs:

```
/docs
```

---

## ⚡ System Architecture

```
User / Voice / AI
        ↓
FastAPI Backend
        ↓
Service Layer (AI + Rules + Logic)
        ↓
Hardware Layer (Fan / Light)
        ↓
Real World Devices
```

---

## 🧱 Project Structure

```
app/
  api/         → API routes
  services/    → AI + automation logic
  hardware/    → fan + light control
  db/          → database handling
  static/      → JS/CSS
  templates/   → dashboard

protocols/     → zigbee / x10 (future)
simulator/     → testing environment
```

---

## 🚀 Quick Start

```bash
python -m app.main
```

Open in your browser:

```
http://localhost:8000/dashboard
http://localhost:8000/docs
```

---

## 🔌 API Examples

### Turn on fan

```http
POST /fan/on
```

### Turn off light

```http
POST /light/off
```

### AI command

```json
POST /command
{
  "message": "turn on the living room light"
}
```

---

## 🧠 What This Project Demonstrates

* Backend API design (FastAPI)
* AI integration (LLM command parsing)
* Hardware abstraction (GPIO, relay, MOSFET)
* Automation systems (rules engine)
* Full-stack system integration

---

## 🔗 Future Improvements

* 📱 Mobile app (Android) *(in progress)*
* MQTT integration
* Cloud deployment
* Advanced anomaly detection
* Multi-room support

---

