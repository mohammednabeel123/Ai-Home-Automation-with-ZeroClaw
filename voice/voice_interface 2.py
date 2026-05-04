"""
ZeroClaw Smart Home v2 — Voice Interface

This project is partially inspired by the following Udemy course:

Course: Raspberry Pi | Build AI Voice Assistant Powered by ChatGPT
Platform: Udemy
Link: https://www.udemy.com/course/raspberry-pi-build-ai-voice-assistant-powered-by-chatgpt/

The course provided foundational ideas for:
- Speech recognition using speech_recognition
- Text-to-speech using gTTS
- ChatGPT API interaction
- Smart device control using tinytuya

This implementation extends those ideas by adding:
- Wake-word activation (session-based interaction)
- Backend API integration
- Conversation memory
- Improved structure and modular design
- Logging and error handling
"""

# ─────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────
# Load environment variables (same approach used in Udemy)
# ─────────────────────────────────────────────────────────────
load_dotenv()

# Logging added for better debugging (not in Udemy)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("zeroclaw.voice")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
WAKE_WORD = os.getenv("WAKE_WORD", "hey claw")  # similar to KEY_PHRASE in Udemy

TUYA_DEVICE_ID = os.getenv("DEVICE_ID")
TUYA_IP = os.getenv("IP_ADDRESS")
TUYA_LOCAL_KEY = os.getenv("LOCAL_KEY")
TUYA_VERSION = float(os.getenv("TUYA_VERSION", "3.3"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

VOICE_LANG = os.getenv("VOICE_LANG", "en")
SAMPLE_RATE = int(os.getenv("MIC_SAMPLE_RATE", "44100"))
SILENCE_TIMEOUT = int(os.getenv("SILENCE_TIMEOUT", "8"))
SESSION_LIMIT = int(os.getenv("SESSION_LIMIT", "10"))

# ─────────────────────────────────────────────────────────────
# Tuya device initialization (same logic as Udemy assistant.py)
# ─────────────────────────────────────────────────────────────
tuya_device = None
if TUYA_DEVICE_ID and TUYA_IP and TUYA_LOCAL_KEY:
    tuya_device = tinytuya.Device(
        TUYA_DEVICE_ID, TUYA_IP, TUYA_LOCAL_KEY, version=TUYA_VERSION
    )
    log.info("Tuya device initialized")
else:
    log.warning("Tuya credentials not set")

# ─────────────────────────────────────────────────────────────
# AI Client (Udemy used OpenAI → replaced with Groq)
# ─────────────────────────────────────────────────────────────
ai_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Conversation memory (added feature, not in Udemy)
conversation = []

SYSTEM_PROMPT = (
    "You are a smart home voice assistant. Keep responses short and clear."
)

# ─────────────────────────────────────────────────────────────
# Text-to-Speech (based on Udemy speak() function)
# ─────────────────────────────────────────────────────────────
def speak(text):
    """Convert text to speech and play it."""

    log.info(f"Speaking: {text}")

    try:
        # Inspired by Udemy: gTTS usage
        tts = gTTS(text=text, lang=VOICE_LANG)

        # Improvement over Udemy: use temporary file instead of fixed filename
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            filename = tmp.name

        tts.save(filename)

        # Same playback logic as Udemy using pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

        # Same waiting loop pattern as Udemy
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        # Cleanup (added improvement)
        pygame.mixer.music.unload()
        os.remove(filename)

    except Exception as e:
        log.error(f"TTS error: {e}")

# ─────────────────────────────────────────────────────────────
# Speech Recognition (based on Udemy function)
# ─────────────────────────────────────────────────────────────
def capture_speech(recognizer, mic, timeout=SILENCE_TIMEOUT):
    """Capture speech and return text."""

    try:
        with mic as source:
            # Same as Udemy: adjust noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            # Extended version of Udemy listen()
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)

        # Same Google speech API used in Udemy
        text = recognizer.recognize_google(audio)

        log.info(f"Heard: {text}")
        return text.strip()

    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        log.error(f"Speech API error: {e}")
        return None

# ─────────────────────────────────────────────────────────────
# Tuya Control (directly inspired by Udemy)
# ─────────────────────────────────────────────────────────────
def turn_on_socket():
    if tuya_device:
        tuya_device.turn_on()  # same as Udemy
        return "Socket is on"
    return "Device not available"

def turn_off_socket():
    if tuya_device:
        tuya_device.turn_off()  # same as Udemy
        return "Socket is off"
    return "Device not available"

# ─────────────────────────────────────────────────────────────
# AI Communication (based on Udemy send_to_chatgpt)
# ─────────────────────────────────────────────────────────────
def ask_ai(prompt):
    if not ai_client:
        return "AI not configured"

    # Add user message (new feature)
    conversation.append({"role": "user", "content": prompt})

    try:
        # Same concept as Udemy: send prompt to AI
        response = ai_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation
        )

        reply = response.choices[0].message.content.strip()

        # Store assistant reply (added feature)
        conversation.append({"role": "assistant", "content": reply})

        return reply

    except Exception as e:
        log.error(f"AI error: {e}")
        return "Error contacting AI"

# ─────────────────────────────────────────────────────────────
# Command Handling (improved version of Udemy if/else)
# ─────────────────────────────────────────────────────────────
def handle_command(command):
    command = command.lower()

    # Same idea as Udemy command handling
    if "socket on" in command:
        return turn_on_socket()

    elif "socket off" in command:
        return turn_off_socket()

    # Otherwise → AI fallback (same concept as Udemy)
    return ask_ai(command)

# ─────────────────────────────────────────────────────────────
# Session Loop (extended from Udemy main loop)
# ─────────────────────────────────────────────────────────────
def run_session(recognizer, mic):
    speak("Hello, how can I help?")

    turns = 0

    while turns < SESSION_LIMIT:
        command = capture_speech(recognizer, mic)

        if command is None:
            speak("Going to sleep")
            return

        if "bye" in command.lower():
            speak("Goodbye")
            return

        response = handle_command(command)
        speak(response)

        turns += 1
        time.sleep(0.3)

# ─────────────────────────────────────────────────────────────
# Main Loop (based on Udemy main_loop())
# ─────────────────────────────────────────────────────────────
def main():
    recognizer = sr.Recognizer()

    # Same microphone setup as Udemy
    mic = sr.Microphone(sample_rate=SAMPLE_RATE)

    print(f"Say '{WAKE_WORD}' to activate")

    while True:
        # Continuous listening (same idea as Udemy)
        text = capture_speech(recognizer, mic, timeout=None)

        # Wake word detection (same as KEY_PHRASE concept)
        if text and WAKE_WORD.lower() in text.lower():
            run_session(recognizer, mic)

# Entry point (same structure as Udemy)
if __name__ == "__main__":
    main()