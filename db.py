import os
import sys
import json
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime

# MySQL Connection Setup
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "vinay")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "rm")

# Fallback JSON File
JSON_DB_FILE = "local_db.json"

_use_json_fallback = False

def _load_json_db():
    if not os.path.exists(JSON_DB_FILE):
        return {"users": [], "chat_logs": []}
    try:
        with open(JSON_DB_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"users": [], "chat_logs": []}

def _save_json_db(data):
    try:
        with open(JSON_DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"DEBUG: Error saving JSON DB: {e}")

def get_db_connection():
    global _use_json_fallback
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            connect_timeout=5
        )
        return conn
    except mysql.connector.Error as err:
        print(f"DEBUG: MySQL Connection Error: {err}")
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            # Try connecting without database to create it
            try:
                temp_conn = mysql.connector.connect(
                    host=MYSQL_HOST,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD
                )
                cursor = temp_conn.cursor()
                cursor.execute(f"CREATE DATABASE {MYSQL_DATABASE}")
                temp_conn.close()
                return mysql.connector.connect(
                    host=MYSQL_HOST,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DATABASE
                )
            except Exception as e:
                print(f"DEBUG: Failed to create database: {e}")
                _use_json_fallback = True
                return None
        else:
            # For other errors, we might want to fallback but let's see
            # If it's a transient error, we shouldn't permanently switch to fallback
            # But for now, let's keep it as is but with better logging
            print(f"DEBUG: Switching to Local JSON Fallback for this session.")
            _use_json_fallback = True
            return None

_connection_checked = False

def check_connection():
    global _connection_checked, _use_json_fallback
    if _connection_checked:
        return True
    
    conn = get_db_connection()
    if conn:
        conn.close()
        _connection_checked = True
        _use_json_fallback = False
        return True
    
    # If get_db_connection failed, _use_json_fallback is already True
    return _use_json_fallback

def ensure_schema():
    conn = get_db_connection()
    if not conn: 
        print("DEBUG: Cannot ensure schema - no connection.")
        return
    try:
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Chat logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                user_id VARCHAR(255),
                session_id VARCHAR(255),
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_session (user_id, session_id)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("DEBUG: Database schema ensured.")
    except Exception as e:
        print(f"DEBUG: Schema error: {e}")

def save_log(role: str, content: str, user_id: str = None, session_id: str = None):
    if _use_json_fallback:
        try:
            data = _load_json_db()
            data["chat_logs"].append({
                "role": role,
                "content": content,
                "user_id": str(user_id) if user_id else None,
                "session_id": session_id,
                "ts": datetime.utcnow().isoformat()
            })
            _save_json_db(data)
            return
        except Exception as e:
            print(f"DEBUG: Error saving to JSON: {e}")
            return

    conn = get_db_connection()
    if not conn: 
        # If MySQL failed, try saving to JSON as fallback
        _use_json_fallback = True
        save_log(role, content, user_id, session_id)
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_logs (role, content, user_id, session_id, ts) VALUES (%s, %s, %s, %s, %s)",
            (role, content, str(user_id) if user_id else None, session_id, datetime.utcnow())
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DEBUG: Error saving log to MySQL: {e}")
        # Try JSON as last resort
        _use_json_fallback = True
        save_log(role, content, user_id, session_id)

def get_chat_history(user_id: str, session_id: str):
    if _use_json_fallback:
        data = _load_json_db()
        return [log for log in data["chat_logs"] 
                if log.get("user_id") == (str(user_id) if user_id else None) and log.get("session_id") == session_id]

    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        if user_id:
            cursor.execute(
                "SELECT role, content, user_id, session_id, ts FROM chat_logs WHERE user_id = %s AND session_id = %s ORDER BY ts ASC",
                (str(user_id), session_id)
            )
        else:
            cursor.execute(
                "SELECT role, content, user_id, session_id, ts FROM chat_logs WHERE user_id IS NULL AND session_id = %s ORDER BY ts ASC",
                (session_id,)
            )
        history = cursor.fetchall()
        cursor.close()
        conn.close()
        return history
    except Exception as e:
        print(f"DEBUG: Error getting history: {e}")
        return []

def get_user_sessions(user_id: str):
    if _use_json_fallback:
        data = _load_json_db()
        sessions = set()
        for log in data["chat_logs"]:
            if log.get("user_id") == (str(user_id) if user_id else None) and log.get("session_id"):
                sessions.add(log["session_id"])
        return sorted(list(sessions), reverse=True)

    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT session_id FROM chat_logs WHERE user_id = %s AND session_id IS NOT NULL GROUP BY session_id ORDER BY MAX(ts) DESC",
                (str(user_id),)
            )
        else:
            cursor.execute(
                "SELECT session_id FROM chat_logs WHERE user_id IS NULL AND session_id IS NOT NULL GROUP BY session_id ORDER BY MAX(ts) DESC",
                (session_id,)
            )
        sessions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return sessions
    except Exception as e:
        print(f"DEBUG: Error getting sessions: {e}")
        return []

def get_user_by_email(email: str):
    if _use_json_fallback:
        data = _load_json_db()
        for user in data["users"]:
            if user["email"] == email:
                user["_id"] = user.get("email") # Mock ID for JWT
                return user
        return None

    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id as _id, email, password_hash, name FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        print(f"DEBUG: Error getting user: {e}")
        return None

def create_user(email: str, password_hash: str, name: str):
    if _use_json_fallback:
        data = _load_json_db()
        if any(u["email"] == email for u in data["users"]):
            return None
        new_user = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.utcnow().isoformat()
        }
        data["users"].append(new_user)
        _save_json_db(data)
        return email

    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, created_at) VALUES (%s, %s, %s, %s)",
            (email, password_hash, name, datetime.utcnow())
        )
        new_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return str(new_id)
    except Exception as e:
        print(f"DEBUG: Error creating user: {e}")
        return None
