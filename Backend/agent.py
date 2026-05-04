# AI agent for smart home control
# references:
# - Groq API (LLM chat completion usage)
# - general chatbot design (system + user messages)

import os, json
from dotenv import load_dotenv
load_dotenv()

from simulator.devices_sim import turn_on, turn_off, turn_off_all, get_all_states
from backend.database import log_command, log_behavior

_histories = {}

# load AI (based on Groq docs)
try:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    AI_OK = True
except:
    AI_OK = False

# prompt inspired by common LLM usage
SYSTEM = """You are a smart home assistant.
Devices: light, fan, tv, socket

Reply:
{"action":"turn_on","device":"light"}
Then short text.
"""

def process(user_id, message):
    hist = _histories.setdefault(user_id, [])
    hist.append({"role": "user", "content": message})

    # include current device states (context for AI)
    states = get_all_states()
    system_text = SYSTEM + "\nStates: " + json.dumps(states)

    if not AI_OK:
        return "AI not configured"

    try:
        # sending request (Groq API format)
        res = client.chat.completions.create(
            model=MODEL,
            max_tokens=150,
            messages=[{"role": "system", "content": system_text}] + hist[-8:]
        )

        reply = res.choices[0].message.content.strip()
        hist.append({"role": "assistant", "content": reply})

        lines = reply.split("\n", 1)

        try:
            # parse JSON output (standard Python json usage)
            data = json.loads(lines[0])
            action = data.get("action", "none")
            device = data.get("device", "")

            user_reply = lines[1].strip() if len(lines) > 1 else reply

            # execute device action (project logic)
            if action == "turn_on":
                turn_on(device)
                log_behavior(device, "on")

            elif action == "turn_off":
                turn_off(device)
                log_behavior(device, "off")

            elif action == "turn_off_all":
                turn_off_all()

        except:
            user_reply = reply

        # log command (sqlite usage)
        log_command("api", message, "groq", "", user_reply[:200])

        return user_reply

    except Exception as e:
        return "error: " + str(e)