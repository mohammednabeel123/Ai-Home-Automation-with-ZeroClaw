import sqlite3
from datetime import datetime

DB_NAME = "smart_home.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        state TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def update_device(name: str, state: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO devices (name, state, updated_at) VALUES (?, ?, ?)",
        (name, state, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

def log_event(event: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO logs (event, timestamp) VALUES (?, ?)",
        (event, datetime.now().isoformat())
    )

    conn.commit()
    conn.close()

def get_devices():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT name, state, updated_at
    FROM devices
    ORDER BY updated_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [
        {"name": row[0], "state": row[1], "updated_at": row[2]}
        for row in rows
    ]