# automation rules engine
# references:
# - APScheduler (background scheduling)
# - cron-style time-based execution

import json
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import get_all_rules
from simulator.devices_sim import turn_on, turn_off

scheduler = BackgroundScheduler()

def execute_rule(action_json):
    try:
        # parse JSON rule (standard json usage)
        data = json.loads(action_json)
        device = data.get("device")
        command = data.get("command", "off")

        # run action (project logic)
        if command == "on":
            turn_on(device)
        else:
            turn_off(device)

        print("[rule] executed", device, command)

    except Exception as e:
        print("[rule] error:", e)

def load_rules():
    scheduler.remove_all_jobs()

    rules = get_all_rules()

    for rule in rules:
        _, name, ttype, tval, action_json, _, _ = rule

        # schedule time-based rule (cron style)
        if ttype == "time" and tval:
            try:
                h, m = map(int, tval.split(":"))

                scheduler.add_job(
                    execute_rule,
                    "cron",
                    hour=h,
                    minute=m,
                    args=[action_json],
                    id=name,
                    replace_existing=True
                )

            except Exception as e:
                print("[rule] load error:", e)

def start_scheduler():
    load_rules()

    # reload rules every 5 minutes
    scheduler.add_job(load_rules, "interval", minutes=5)

    scheduler.start()