"""
multi_user_module.py 
Roles: admin (full), family (devices+logs), guest (read only)

References:
[1] FastAPI Security Docs:
https://fastapi.tiangolo.com/tutorial/security/

[2] PyJWT Usage:
https://pyjwt.readthedocs.io/en/stable/usage.html

[3] bcrypt Password Hashing:
https://pypi.org/project/bcrypt/

[4] SQLite Python Docs:
https://docs.python.org/3/library/sqlite3.html
"""

import os, sqlite3, bcrypt, jwt, json
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# ---------------- SETTINGS ----------------
# [2] PyJWT: token secret + algorithm
DB      = os.getenv("DB_PATH", "smart_home.db")
SECRET  = os.getenv("JWT_SECRET", "change_me")
ALGO    = "HS256"
HOURS   = 24 * 7

# Role-based access control (RBAC)
# Inspired by general RBAC models (FastAPI + Auth systems)
ROLES = {
    "admin":  {"control":True,  "logs":True,  "users":True,  "cameras":True},
    "family": {"control":True,  "logs":True,  "users":False, "cameras":True},
    "guest":  {"control":False, "logs":False, "users":False, "cameras":False},
}

# ---------------- HELPERS ----------------
# [4] SQLite: connection handling
def db():
    return sqlite3.connect(DB)

# Standard timestamp
def now():
    return datetime.now().isoformat()

# ---------------- INIT DB ----------------
def init_db():
    conn = db()

    # [4] SQLite: CREATE TABLE IF NOT EXISTS
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            pw_hash TEXT NOT NULL,
            role TEXT DEFAULT 'guest',
            tg_id TEXT,
            login_at TEXT,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            action TEXT,
            detail TEXT,
            ts TEXT
        );
    """)

    # Safe migration (prevents column errors)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN tg_id TEXT")
    except:
        pass

    try:
        conn.execute("ALTER TABLE users ADD COLUMN login_at TEXT")
    except:
        pass

    conn.commit()

    # Create default admin if DB empty
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        _add(conn, "admin", "admin123", "admin")
        print("[users] default admin created")

    conn.close()

# ---------------- INTERNAL ADD ----------------
def _add(conn, username, password, role, tg_id=None):
    # [3] bcrypt: secure password hashing
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn.execute(
        "INSERT INTO users (username,pw_hash,role,tg_id) VALUES (?,?,?,?)",
        (username, pw_hash, role, tg_id)
    )
    conn.commit()

# ---------------- USER FUNCTIONS ----------------
def create_user(username, password, role="guest", tg_id=None):
    if role not in ROLES:
        return {"ok":False, "error":"invalid role"}

    if len(password) < 6:
        return {"ok":False, "error":"password too short"}

    conn = db()
    try:
        _add(conn, username, password, role, tg_id)
        return {"ok":True}
    except sqlite3.IntegrityError:
        return {"ok":False, "error":"user exists"}
    finally:
        conn.close()

def login(username, password):
    conn = db()

    # [4] SQLite: SELECT query
    row = conn.execute(
        "SELECT id,username,pw_hash,role,active FROM users WHERE username=?",
        (username,)
    ).fetchone()

    conn.close()

    if not row or not row[4]:
        return None

    # [3] bcrypt: verify password
    if not bcrypt.checkpw(password.encode(), row[2].encode()):
        return None

    conn = db()
    conn.execute("UPDATE users SET login_at=? WHERE id=?", (now(), row[0]))
    conn.commit()
    conn.close()

    return {"id":row[0], "username":row[1], "role":row[3]}

def list_users():
    conn = db()

    rows = conn.execute(
        "SELECT id,username,role,tg_id,login_at,active FROM users"
    ).fetchall()

    conn.close()

    return [
        {
            "id": r[0],
            "username": r[1],
            "role": r[2],
            "tg_id": r[3],
            "last_login": r[4],
            "active": bool(r[5])
        }
        for r in rows
    ]

# ---------------- JWT ----------------
def make_token(user):
    # [2] PyJWT: encode token
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=HOURS)
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def check_token(token):
    try:
        # [2] PyJWT: decode token
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ---------------- TEST ----------------
if __name__ == "__main__":
    init_db()

    print("\n--- USERS ---")
    print(json.dumps(list_users(), indent=2))

    print("\n--- LOGIN TEST ---")
    user = login("admin", "admin123")
    print("Login:", user)

    if user:
        token = make_token(user)
        print("Token:", token)