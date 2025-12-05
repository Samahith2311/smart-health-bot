import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "health.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_db():
    conn = get_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT NOT NULL
    )
    """)

    # Reminders table (linked to user) with type
    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,                -- 'water', 'meal', 'sleep', 'custom'
        message TEXT,
        interval_min INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


# ---------- User helpers ----------

def create_user(username, email, password):
    conn = get_connection()
    c = conn.cursor()
    password_hash = generate_password_hash(password)

    try:
        c.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # username already exists
        return False
    finally:
        conn.close()


def get_user_by_username(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, username, email, password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = c.fetchone()
    conn.close()
    return row  # (id, username, email, password_hash) or None


def verify_user(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    user_id, _, _, password_hash = user
    if check_password_hash(password_hash, password):
        return user_id
    return None


# ---------- Reminder helpers ----------

def add_reminder(user_id, reminder_type, msg, interval_min):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO reminders (user_id, type, message, interval_min) VALUES (?, ?, ?, ?)",
        (user_id, reminder_type, msg, interval_min),
    )
    conn.commit()
    conn.close()


def get_reminders_for_user(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, type, message, interval_min FROM reminders WHERE user_id = ?",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows
