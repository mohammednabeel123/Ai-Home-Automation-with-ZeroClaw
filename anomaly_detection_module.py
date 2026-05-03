"""
anomaly_detection_module.py
Week 12 - Smart Home Project
Detects unusual activity and sends Telegram alerts

Checks for:
- motion at night
- temperature too high or low
- a device left on too long
- too many commands in a short time (possible break-in)
- no activity for a long time (is someone okay?)

Sources used:
  [1] schedule library docs + PyPI page
      https://schedule.readthedocs.io/
      https://pypi.org/project/schedule/
  [2] Python sqlite3 docs
      https://docs.python.org/3/library/sqlite3.html
  [3] GitHub Gist - Programmatically send push notifications to telegram from python
      https://gist.github.com/dlaptev/7f1512ee80b7e511b0435d3ba95d88cc
  [4] aronhack.com - Use Telegram Bot API And Python To Send Text Messages And Photos
      https://aronhack.com/use-telegram-bot-api-and-python-to-send-text-messages-and-photos/
  [5] requests library docs (quickstart) - Making HTTP GET requests and using .json()
      https://requests.readthedocs.io/en/latest/user/quickstart/
  [6] Claude AI - helped structure the checks and threshold logic

Requirements:
    pip install requests schedule python-dotenv
"""

import os
import sqlite3
import time
import requests
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# settings - edit these to suit your home
TELEGRAM_TOKEN       = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "")
BACKEND_URL          = os.getenv("BACKEND_URL", "http://localhost:8000")
DB_PATH              = os.getenv("DB_PATH", "smart_home.db")
TEMP_MIN             = 10   # alert if temperature drops below this (celsius)
TEMP_MAX             = 35   # alert if temperature goes above this
QUIET_START          = 23   # night starts at 11pm
QUIET_END            = 6    # night ends at 6am
DEVICE_ON_MAX_HOURS  = 4    # alert if device is on longer than this
NO_ACTIVITY_HOURS    = 8    # alert if nobody uses the system for this long
RAPID_CMD_WINDOW     = 2    # minutes to check for rapid commands
RAPID_CMD_LIMIT      = 10   # commands in that window = suspicious

# my own - track when each alert was last sent so we dont spam telegram
last_sent = {}


# ==============================
# send telegram alert with cooldown
# [3] gist.github.com line: url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s' % (token, chat_id)
# [3] gist.github.com line: _ = requests.post(url, json={'text': '<message>'}, timeout=10)
# [4] aronhack.com line: message_url = f"{base_url}/sendMessage"
# [4] aronhack.com line: response = requests.post(message_url, params=message_params)
# [4] aronhack.com line: except Exception as e: print(f"An error occurred: {e}")
# my own - added cooldown logic and severity icons on top of the telegram pattern
# ==============================
def send_alert(alert_type, severity, message, cooldown_min=15):
    now = datetime.now()

    # my own - check cooldown so same alert doesnt spam
    if alert_type in last_sent:
        mins_since = (now - last_sent[alert_type]).total_seconds() / 60
        if mins_since < cooldown_min:
            return

    last_sent[alert_type] = now
    save_alert(alert_type, severity, message)

    # my own - emoji icons to show severity level in the telegram message
    icons = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
    icon = icons.get(severity, "⚠️")
    text = f"{icon} Smart Home Alert\n\nType: {alert_type}\nSeverity: {severity.upper()}\n\n{message}\n\n{now.strftime('%H:%M:%S %d/%m/%Y')}"

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            # [3] gist: url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s' % (token, chat_id)
            # [4] aronhack.com: message_url = f"{base_url}/sendMessage"
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)   # [3] gist: requests.post(url, ..., timeout=10)
            print(f"[anomaly] alert sent: {alert_type}")
        except Exception as e:
            print(f"[anomaly] telegram error: {e}")   # [4] aronhack.com: except Exception as e: print(f"An error occurred: {e}")
    else:
        print(f"[anomaly] {icon} {alert_type}: {message}")


# ==============================
# database - create table, save alerts, read alerts
# [2] Python sqlite3 docs line: conn = sqlite3.connect("example.db")
# [2] Python sqlite3 docs line: conn.execute("CREATE TABLE IF NOT EXISTS ...")
# [2] Python sqlite3 docs line: conn.execute("INSERT INTO ... VALUES (?,?,?,?)", (val1, val2, ...))
# [2] Python sqlite3 docs line: cursor.fetchall()
# [2] Python sqlite3 docs line: cursor.fetchone()
# [2] Python sqlite3 docs line: conn.commit()
# [2] Python sqlite3 docs line: conn.close()
# ==============================
def init_db():
    conn = sqlite3.connect(DB_PATH)   # [2] sqlite3 docs: conn = sqlite3.connect("example.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_alerts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT,
            alert_type   TEXT,
            severity     TEXT,
            message      TEXT,
            acknowledged INTEGER DEFAULT 0
        )
    """)   # [2] sqlite3 docs: CREATE TABLE IF NOT EXISTS pattern - only creates if it doesnt exist
    conn.commit()   # [2] sqlite3 docs: conn.commit() - saves the changes to disk
    conn.close()    # [2] sqlite3 docs: conn.close()


def save_alert(alert_type, severity, message):
    conn = sqlite3.connect(DB_PATH)   # [2] sqlite3 docs: conn = sqlite3.connect(...)
    conn.execute(
        "INSERT INTO anomaly_alerts (timestamp, alert_type, severity, message) VALUES (?,?,?,?)",
        (datetime.now().isoformat(), alert_type, severity, message)
    )   # [2] sqlite3 docs: use ? placeholders instead of string formatting to prevent SQL injection
    conn.commit()   # [2] sqlite3 docs: conn.commit()
    conn.close()    # [2] sqlite3 docs: conn.close()


def get_recent_alerts(minutes=60):
    conn = sqlite3.connect(DB_PATH)   # [2] sqlite3 docs: conn = sqlite3.connect(...)
    since = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    rows = conn.execute(
        "SELECT alert_type, message FROM anomaly_alerts WHERE timestamp > ? ORDER BY timestamp DESC",
        (since,)
    ).fetchall()   # [2] sqlite3 docs: cursor.fetchall() - returns all matching rows as a list
    conn.close()   # [2] sqlite3 docs: conn.close()
    return rows


# ==============================
# get data from the backend
# [5] requests docs line: r = requests.get('https://api.github.com/events')
# [5] requests docs line: r.json()
# [5] requests docs line: requests.get(url, timeout=5)
# my own - fetches sensor readings, device states, and command logs from smart home backend
# ==============================
def get_sensors():
    try:
        r = requests.get(f"{BACKEND_URL}/sensors", timeout=5)   # [5] requests docs: r = requests.get(url, timeout=5)
        return r.json()   # [5] requests docs: r.json() - parses the JSON response body
    except:
        return {}


def get_devices():
    try:
        r = requests.get(f"{BACKEND_URL}/devices", timeout=5)   # [5] requests docs: r = requests.get(url, timeout=5)
        return r.json()   # [5] requests docs: r.json()
    except:
        return {}


def get_recent_commands(minutes=10):
    try:
        r = requests.get(f"{BACKEND_URL}/logs?limit=100", timeout=5)   # [5] requests docs: r = requests.get(url, timeout=5)
        logs = r.json()   # [5] requests docs: r.json()
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent = []
        for entry in logs:
            try:
                ts = datetime.fromisoformat(entry.get("timestamp", ""))
                if ts > cutoff:
                    recent.append(entry)
            except:
                pass
        return recent
    except:
        return []


def get_last_activity():
    # check database for the most recent command timestamp
    try:
        conn = sqlite3.connect(DB_PATH)   # [2] sqlite3 docs: conn = sqlite3.connect(...)
        row = conn.execute("SELECT MAX(timestamp) FROM command_log").fetchone()   # [2] sqlite3 docs: .fetchone() - gets first result row
        conn.close()   # [2] sqlite3 docs: conn.close()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
    except:
        pass
    return None


# ==============================
# the actual anomaly checks
# my own logic for each check type - Claude helped pick the threshold values
# ==============================
def check_temperature():
    sensors = get_sensors()   # [5] requests docs: r = requests.get(...) / r.json() used inside
    temp = sensors.get("temperature")
    if temp is None:
        return
    temp = float(temp)
    if temp < TEMP_MIN:
        send_alert("temperature_low", "high", f"Temperature is too LOW: {temp}°C (min is {TEMP_MIN}°C)")
    elif temp > TEMP_MAX:
        send_alert("temperature_high", "high", f"Temperature is too HIGH: {temp}°C (max is {TEMP_MAX}°C)")


def check_motion_at_night():
    sensors = get_sensors()   # [5] requests docs: r.json() used inside get_sensors()
    motion = sensors.get("motion", False)
    hour = datetime.now().hour
    is_night = hour >= QUIET_START or hour < QUIET_END   # my own - check if current hour is in night window
    if motion and is_night:
        send_alert("motion_night", "high",
                   f"Motion detected at {datetime.now().strftime('%H:%M')} - outside normal hours!",
                   cooldown_min=5)


def check_device_on_too_long():
    devices = get_devices()   # [5] requests docs: r.json() used inside get_devices()
    conn = sqlite3.connect(DB_PATH)   # [2] sqlite3 docs: conn = sqlite3.connect(...)
    for device, is_on in devices.items():
        if not is_on:
            continue
        # find when this device was last switched on
        row = conn.execute(
            "SELECT timestamp FROM command_log WHERE action='on' AND device=? ORDER BY timestamp DESC LIMIT 1",
            (device,)
        ).fetchone()   # [2] sqlite3 docs: .fetchone() - returns just the first matching row
        if row:
            try:
                on_since = datetime.fromisoformat(row[0])
                hours_on = (datetime.now() - on_since).total_seconds() / 3600
                if hours_on > DEVICE_ON_MAX_HOURS:
                    send_alert(f"device_on_{device}", "medium",
                               f"{device} has been ON for {hours_on:.1f} hours - did you forget?",
                               cooldown_min=60)
            except:
                pass
    conn.close()   # [2] sqlite3 docs: conn.close()


def check_rapid_commands():
    recent = get_recent_commands(minutes=RAPID_CMD_WINDOW)   # [5] requests docs: r.json() used inside
    if len(recent) >= RAPID_CMD_LIMIT:
        send_alert("rapid_commands", "medium",
                   f"{len(recent)} commands in {RAPID_CMD_WINDOW} minutes - unusual activity!",
                   cooldown_min=10)


def check_no_activity():
    last = get_last_activity()
    if last is None:
        return
    hours_ago = (datetime.now() - last).total_seconds() / 3600
    if hours_ago > NO_ACTIVITY_HOURS:
        send_alert("no_activity", "low",
                   f"No activity for {hours_ago:.1f} hours - is everything okay?",
                   cooldown_min=120)


def run_all_checks():
    print(f"[anomaly] running checks at {datetime.now().strftime('%H:%M:%S')}")
    check_temperature()
    check_motion_at_night()
    check_device_on_too_long()
    check_rapid_commands()
    check_no_activity()


# ==============================
# fastapi routes - plug into main.py
# my own addition - REST endpoints so the frontend can read and acknowledge alerts
# ==============================
def get_anomaly_routes():
    """
    To use in main.py:
        from anomaly_detection_module import get_anomaly_routes
        app.include_router(get_anomaly_routes())
    """
    from fastapi import APIRouter
    router = APIRouter(prefix="/anomaly", tags=["anomaly"])

    @router.get("/alerts")
    def list_alerts(minutes: int = 60):
        alerts = get_recent_alerts(minutes)
        return [{"type": a[0], "message": a[1]} for a in alerts]

    @router.post("/acknowledge/{alert_id}")
    def acknowledge(alert_id: int):
        conn = sqlite3.connect(DB_PATH)   # [2] sqlite3 docs: conn = sqlite3.connect(...)
        conn.execute("UPDATE anomaly_alerts SET acknowledged=1 WHERE id=?", (alert_id,))
        conn.commit()   # [2] sqlite3 docs: conn.commit()
        conn.close()    # [2] sqlite3 docs: conn.close()
        return {"status": "acknowledged"}

    return router


# ==============================
# start - schedule all checks and loop forever
# [1] schedule docs (pypi.org) line: schedule.every(10).minutes.do(job)
# [1] schedule docs (pypi.org) line: while True: schedule.run_pending()
# [1] schedule docs (pypi.org) line: time.sleep(1)
# ==============================
if __name__ == "__main__":
    init_db()
    print("[anomaly] anomaly detector started")
    send_alert("system_start", "low", "Anomaly detection system started", cooldown_min=0)

    # [1] pypi/schedule docs: schedule.every(N).minutes.do(function_name)
    schedule.every(1).minutes.do(check_motion_at_night)     # [1] schedule docs: schedule.every(1).minutes.do(job)
    schedule.every(2).minutes.do(check_temperature)         # [1] schedule docs: schedule.every(2).minutes.do(job)
    schedule.every(5).minutes.do(check_device_on_too_long)  # [1] schedule docs: schedule.every(5).minutes.do(job)
    schedule.every(2).minutes.do(check_rapid_commands)      # [1] schedule docs: schedule.every(2).minutes.do(job)
    schedule.every(30).minutes.do(check_no_activity)        # [1] schedule docs: schedule.every(30).minutes.do(job)

    run_all_checks()   # my own - run all checks immediately on startup before waiting

    # [1] pypi/schedule docs: while True: schedule.run_pending() / time.sleep(1)
    try:
        while True:
            schedule.run_pending()   # [1] schedule docs: schedule.run_pending() - runs any jobs that are due now
            time.sleep(30)           # [1] schedule docs: time.sleep(1) in the loop - we use 30 seconds to save CPU
    except KeyboardInterrupt:
        print("\n[anomaly] stopped")
