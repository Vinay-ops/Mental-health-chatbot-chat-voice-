import os
import sys
import json
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

# Fallback JSON File
JSON_DB_FILE = "local_db.json"

_use_json_fallback = False

def _load_json_db():
    if not os.path.exists(JSON_DB_FILE):
        return {"users": [], "chat_logs": [], "community_posts": []}
    try:
        with open(JSON_DB_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"users": [], "chat_logs": [], "community_posts": []}

def _save_json_db(data):
    try:
        with open(JSON_DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"DEBUG: Error saving JSON DB: {e}")

def get_db_connection():
    global _use_json_fallback
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url, connect_timeout=10)
        else:
            host = os.getenv("PG_HOST", "localhost")
            port = int(os.getenv("PG_PORT", "6543"))
            dbname = os.getenv("PG_DATABASE", "postgres")
            user = os.getenv("PG_USER", "postgres")
            password = os.getenv("PG_PASSWORD", "")

            connect_kwargs = {
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
                "password": password,
                "connect_timeout": 10,
            }
            if host.endswith("supabase.co"):
                connect_kwargs["sslmode"] = "require"

            conn = psycopg2.connect(**connect_kwargs)
        return conn
    except Exception as err:
        print(f"DEBUG: Postgres Connection Error: {err}")
        _use_json_fallback = True
        return None

_connection_checked = False
_force_offline = False

def set_force_offline(value: bool):
    global _force_offline
    _force_offline = value

def check_connection():
    global _connection_checked, _use_json_fallback, _force_offline
    if _force_offline:
        _use_json_fallback = True
        return False
    try:
        conn = get_db_connection()
        if conn:
            conn.close()
            _use_json_fallback = False
            return True
        else:
            _use_json_fallback = True
            return False
    except Exception:
        _use_json_fallback = True
        return False

def ensure_schema():
    conn = get_db_connection()
    if not conn: 
        print("DEBUG: Cannot ensure schema - no connection.")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id SERIAL PRIMARY KEY,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                user_id VARCHAR(255),
                session_id VARCHAR(255),
                ts TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_session
            ON chat_logs (user_id, session_id)
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_posts (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255),
                name VARCHAR(255),
                content TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                likes INT DEFAULT 0
            )
        """)
        try:
            cursor.execute("ALTER TABLE community_posts ADD COLUMN likes INT DEFAULT 0")
        except Exception:
            pass
        conn.commit()
        cursor.close()
        conn.close()
        print("DEBUG: Database schema ensured.")
    except Exception as e:
        print(f"DEBUG: Schema error: {e}")

def save_log(role: str, content: str, user_id: str = None, session_id: str = None):
    # 1. Always save to local JSON (Local Redundancy)
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
    except Exception as e:
        print(f"DEBUG: Error saving to JSON: {e}")

    # 2. Save to Supabase (if online)
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
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
                print(f"DEBUG: Error saving log to DB: {e}")

def get_chat_history(user_id: str, session_id: str):
    history = []
    # 1. Try JSON (always check local for offline/flaky data)
    try:
        data = _load_json_db()
        local_history = [log for log in data["chat_logs"] 
                        if log.get("user_id") == (str(user_id) if user_id else None) and log.get("session_id") == session_id]
        history.extend(local_history)
    except Exception:
        pass

    # 2. Try Supabase (if online)
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
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
                db_history = cursor.fetchall()
                # Deduplicate or just append (ts sort will handle order)
                history.extend(db_history)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"DEBUG: Error getting DB history: {e}")

    # Sort by timestamp to merge local and remote correctly
    try:
        history.sort(key=lambda x: x.get('ts') if x.get('ts') else "")
    except Exception:
        pass
        
    return history

def get_user_sessions(user_id: str):
    sessions = set()
    # 1. Check local
    try:
        data = _load_json_db()
        for log in data["chat_logs"]:
            if log.get("user_id") == (str(user_id) if user_id else None) and log.get("session_id"):
                sessions.add(log["session_id"])
    except Exception:
        pass

    # 2. Check Supabase
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute(
                        "SELECT session_id FROM chat_logs WHERE user_id = %s AND session_id IS NOT NULL GROUP BY session_id",
                        (str(user_id),)
                    )
                else:
                    cursor.execute(
                        "SELECT session_id FROM chat_logs WHERE user_id IS NULL AND session_id IS NOT NULL GROUP BY session_id",
                        ()
                    )
                db_sessions = [row[0] for row in cursor.fetchall()]
                for s in db_sessions: sessions.add(s)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"DEBUG: Error getting DB sessions: {e}")

    return sorted(list(sessions), reverse=True)

def get_user_by_email(email: str):
    # 1. Try Supabase first (Primary source)
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT id as _id, email, password_hash, name FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                if user: return user
            except Exception as e:
                print(f"DEBUG: Error getting DB user: {e}")

    # 2. Fallback to local JSON if not found or offline
    try:
        data = _load_json_db()
        for user in data["users"]:
            if user["email"] == email:
                user["_id"] = user.get("email") # Mock ID for JWT
                return user
    except Exception:
        pass
        
    return None
def create_user(email: str, password_hash: str, name: str):
    # 1. Try Supabase first (Primary source)
    db_uid = None
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (email, password_hash, name, created_at) VALUES (%s, %s, %s, %s) RETURNING id",
                    (email, password_hash, name, datetime.utcnow())
                )
                row = cursor.fetchone()
                conn.commit()
                cursor.close()
                conn.close()
                if row: db_uid = str(row[0])
            except Exception as e:
                print(f"DEBUG: Error creating DB user: {e}")

    # 2. Always save to local JSON (Sync/Redundancy)
    try:
        data = _load_json_db()
        if not any(u["email"] == email for u in data["users"]):
            new_user = {
                "email": email,
                "password_hash": password_hash,
                "name": name,
                "created_at": datetime.utcnow().isoformat()
            }
            data["users"].append(new_user)
            _save_json_db(data)
    except Exception:
        pass

    # Return DB ID if we got one, otherwise return email as mock ID
    return db_uid or email

def add_community_post(user_id: str, name: str, content: str):
    # 1. Save to local JSON
    try:
        data = _load_json_db()
        posts = data.get("community_posts") or []
        posts.append({
            "user_id": str(user_id) if user_id else None,
            "name": name,
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
            "likes": 0
        })
        data["community_posts"] = posts
        _save_json_db(data)
    except Exception:
        pass

    # 2. Save to Supabase (if online)
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO community_posts (user_id, name, content, created_at, likes) VALUES (%s, %s, %s, %s, %s)",
                    (str(user_id) if user_id else None, name, content, datetime.utcnow(), 0)
                )
                conn.commit()
                cursor.close()
                conn.close()
                return True
            except Exception as e:
                print(f"DEBUG: Error adding DB post: {e}")
    
    return True # Return true because it's saved locally at least

def get_community_posts(limit: int = 30):
    posts = []
    # 1. Get from local JSON
    try:
        data = _load_json_db()
        local_posts = data.get("community_posts") or []
        posts.extend(local_posts)
    except Exception:
        pass

    # 2. Get from Supabase
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(
                    "SELECT id, user_id, name, content, created_at, likes FROM community_posts ORDER BY created_at DESC LIMIT %s",
                    (limit,)
                )
                db_posts = cursor.fetchall()
                # Append and let sort handle order
                posts.extend(db_posts)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"DEBUG: Error getting DB community posts: {e}")

    # Sort by date
    try:
        posts.sort(key=lambda p: p.get("created_at") if p.get("created_at") else "", reverse=True)
    except Exception:
        pass
        
    return posts[:limit]

def like_community_post(post_id: int):
    if _use_json_fallback:
        return None

    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE community_posts SET likes = COALESCE(likes, 0) + 1 WHERE id = %s",
            (post_id,)
        )
        conn.commit()
        cursor.execute(
            "SELECT likes FROM community_posts WHERE id = %s",
            (post_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        return row[0]
    except Exception as e:
        print(f"DEBUG: Error liking community post: {e}")
        return None
