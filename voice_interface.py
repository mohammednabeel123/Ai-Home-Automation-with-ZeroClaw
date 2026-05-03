"""
ZeroClaw Smart Home v2 — Voice Interface
Wake-word activated assistant with Groq LLM, gTTS speech synthesis,
multi-device Tuya control, and ZeroClaw backend integration.
"""

import os
import time
import logging
import tempfile
import requests
import pygame
import speech_recognition as sr
from gtts import gTTS
from dotenv import load_dotenv
import tinytuya
from groq import Groq

# ── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("zeroclaw.voice")

# ── Config ────────────────────────────────────────────────────────────────────
WAKE_WORD        = os.getenv("WAKE_WORD", "hey claw")
TUYA_DEVICE_ID   = os.getenv("DEVICE_ID")
TUYA_IP          = os.getenv("IP_ADDRESS")
TUYA_LOCAL_KEY   = os.getenv("LOCAL_KEY")
TUYA_VERSION     = float(os.getenv("TUYA_VERSION", "3.3"))
GROQ_API_KEY     = os.getenv("GROQ_API_KEY")
GROQ_MODEL       = os.getenv("GROQ_MODEL", "llama3-8b-8192")
BACKEND_URL      = os.getenv("BACKEND_URL", "http://localhost:8000")
VOICE_LANG       = os.getenv("VOICE_LANG", "en")
SAMPLE_RATE      = int(os.getenv("MIC_SAMPLE_RATE", "44100"))
SILENCE_TIMEOUT  = int(os.getenv("SILENCE_TIMEOUT", "8"))   # seconds before sleep
SESSION_LIMIT    = int(os.getenv("SESSION_LIMIT", "10"))     # max turns per session

# ── Tuya device init ──────────────────────────────────────────────────────────
tuya_device = None
if TUYA_DEVICE_ID and TUYA_IP and TUYA_LOCAL_KEY:
    tuya_device = tinytuya.Device(
        TUYA_DEVICE_ID, TUYA_IP, TUYA_LOCAL_KEY, version=TUYA_VERSION
    )
    log.info("Tuya device initialised: %s @ %s", TUYA_DEVICE_ID, TUYA_IP)
else:
    log.warning("Tuya credentials not set — device control disabled.")

# ── Groq client ───────────────────────────────────────────────────────────────
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
if not ai_client:
    log.warning("GROQ_API_KEY not set — AI responses disabled.")

# ── Conversation history (multi-turn) ─────────────────────────────────────────
_conversation: list[dict] = []

SYSTEM_PROMPT = (
    "You are ZeroClaw, a concise voice-controlled smart home assistant. "
    "Keep every reply under 40 words. "
    "When asked about smart home devices say what you are doing, then do it. "
    "Never use markdown, bullet points, or lists — plain speech only."
)

# ── Speech synthesis ──────────────────────────────────────────────────────────
def speak(text: str) -> None:
    """Convert text to speech and play it through the default audio output."""
    log.info("Speaking: %s", text)
    try:
        tts = gTTS(text=text, lang=VOICE_LANG)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        tts.save(tmp_path)
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        os.remove(tmp_path)
    except Exception as exc:
        log.error("TTS error: %s", exc)

# ── Speech recognition ────────────────────────────────────────────────────────
def capture_speech(recognizer: sr.Recognizer, mic: sr.Microphone,
                   timeout: int = SILENCE_TIMEOUT) -> str | None:
    """Capture one utterance and return the recognised text, or None."""
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
        text = recognizer.recognize_google(audio)
        log.info("Heard: %s", text)
        return text.strip()
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except sr.RequestError as exc:
        log.error("Speech API error: %s", exc)
        return None

# ── Device control helpers ────────────────────────────────────────────────────
def _tuya_on() -> str:
    if tuya_device:
        tuya_device.turn_on()
        return "Socket is on."
    return "No Tuya device configured."

def _tuya_off() -> str:
    if tuya_device:
        tuya_device.turn_off()
        return "Socket is off."
    return "No Tuya device configured."

def _backend_command(message: str) -> str | None:
    """Forward a command to the ZeroClaw FastAPI backend and return its response."""
    try:
        resp = requests.post(
            f"{BACKEND_URL}/command",
            json={"user_id": "voice", "message": message},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("response")
    except requests.RequestException as exc:
        log.warning("Backend unreachable: %s", exc)
        return None

# ── AI response ───────────────────────────────────────────────────────────────
def ask_groq(user_text: str) -> str:
    """Send a message to Groq with full conversation history."""
    global _conversation
    if not ai_client:
        return "AI is not configured."

    _conversation.append({"role": "user", "content": user_text})

    try:
        result = ai_client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=256,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + _conversation,
        )
        reply = result.choices[0].message.content.strip()
        _conversation.append({"role": "assistant", "content": reply})
        # Keep history bounded
        if len(_conversation) > SESSION_LIMIT * 2:
            _conversation = _conversation[-(SESSION_LIMIT * 2):]
        return reply
    except Exception as exc:
        log.error("Groq API error: %s", exc)
        return "Sorry, I couldn't reach the AI right now."

# ── Intent routing ────────────────────────────────────────────────────────────
DIRECT_COMMANDS: dict[tuple[str, ...], callable] = {
    ("socket on",  "plug on",  "turn on socket"):  _tuya_on,
    ("socket off", "plug off", "turn off socket"): _tuya_off,
}

def route(command: str) -> str:
    """Route a recognised command to the right handler."""
    lower = command.lower()

    # 1. Hard-wired device commands (instant, no API call)
    for keywords, handler in DIRECT_COMMANDS.items():
        if any(kw in lower for kw in keywords):
            return handler()

    # 2. Try the ZeroClaw backend first (handles lights, rules, etc.)
    backend_reply = _backend_command(command)
    if backend_reply:
        return backend_reply

    # 3. Fall back to Groq for general conversation
    return ask_groq(command)

# ── Session loop ──────────────────────────────────────────────────────────────
def run_session(recognizer: sr.Recognizer, mic: sr.Microphone) -> None:
    """Run one activated session until timeout or user says goodbye."""
    global _conversation
    _conversation = []          # fresh context per session
    speak("Hello! How can I help?")
    turns = 0

    while turns < SESSION_LIMIT:
        command = capture_speech(recognizer, mic, timeout=SILENCE_TIMEOUT)

        if command is None:
            speak("Going to sleep. Say the wake word to activate me again.")
            return

        if any(bye in command.lower() for bye in ("goodbye", "bye", "stop", "sleep")):
            speak("Goodbye!")
            return

        response = route(command)
        speak(response)
        turns += 1
        time.sleep(0.3)   # brief pause before listening again

    speak("Session limit reached. Say the wake word to start again.")

# ── Main loop ─────────────────────────────────────────────────────────────────
def main() -> None:
    recognizer = sr.Recognizer()
    mic = sr.Microphone(sample_rate=SAMPLE_RATE)

    log.info("ZeroClaw Voice Interface ready. Wake word: '%s'", WAKE_WORD)
    print(f"\n🎤  Say '{WAKE_WORD}' to activate.\n")

    while True:
        utterance = capture_speech(recognizer, mic, timeout=None)  # wait forever
        if utterance and WAKE_WORD.lower() in utterance.lower():
            log.info("Wake word detected — starting session.")
            run_session(recognizer, mic)
        elif utterance:
            log.debug("Ignored (no wake word): %s", utterance)

if __name__ == "__main__":
    main()
