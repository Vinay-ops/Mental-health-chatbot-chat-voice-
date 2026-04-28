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

def _normalize_identifier(identifier: str):
    if identifier is None:
        return None
    text = str(identifier).strip()
    return text if text else None

def resolve_user_identifier(identifier: str):
    """
    Resolve a user identifier (email or numeric id) to canonical email.
    Falls back to original identifier when user cannot be resolved.
    """
    normalized = _normalize_identifier(identifier)
    if not normalized:
        return normalized
    if "@" in normalized:
        return normalized.lower()

    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT email FROM users WHERE id = %s", (normalized,))
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                if row and row.get("email"):
                    return str(row.get("email")).lower()
            except Exception as e:
                print(f"DEBUG: Error resolving identifier from DB: {e}")

    try:
        data = _load_json_db()
        for user in data.get("users", []):
            if str(user.get("email", "")).lower() == normalized.lower():
                return str(user.get("email")).lower()
    except Exception:
        pass
    return normalized.lower()

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
                user_type VARCHAR(50) DEFAULT 'user',
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
        
        # Add user_type column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN user_type VARCHAR(50) DEFAULT 'user'")
        except Exception:
            pass
        
        # Create psychologist-user connections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS psychologist_users (
                id SERIAL PRIMARY KEY,
                psychologist_id VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(psychologist_id, user_id)
            )
        """)
        
        # Create direct message table for psychologist-user chats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS direct_messages (
                id SERIAL PRIMARY KEY,
                sender_id VARCHAR(255) NOT NULL,
                receiver_id VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_direct_messages
            ON direct_messages (sender_id, receiver_id, created_at DESC)
        """)
        
        # Create chat requests table for user-psychologist chat requests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_requests (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(255) UNIQUE NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                psychologist_id VARCHAR(255) NOT NULL,
                message TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_requests_status
            ON chat_requests (psychologist_id, status)
        """)
        
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
                cursor.execute("SELECT id as _id, email, password_hash, name, user_type FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
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
                user["user_type"] = user.get("user_type", "user")
                return user
    except Exception:
        pass
        
    return None
def create_user(email: str, password_hash: str, name: str, user_type: str = "user"):
    # 1. Try Supabase first (Primary source)
    db_uid = None
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (email, password_hash, name, user_type, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (email, password_hash, name, user_type, datetime.utcnow())
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
                "user_type": user_type,
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

# ===== Psychologist-specific functions =====

def connect_psychologist_to_user(psychologist_id: str, user_id: str):
    """Connect a psychologist to a user for direct messaging"""
    if _use_json_fallback:
        # Store in JSON fallback
        try:
            data = _load_json_db()
            if "psychologist_users" not in data:
                data["psychologist_users"] = []
            # Check if already connected
            if not any(p["psychologist_id"] == psychologist_id and p["user_id"] == user_id 
                      for p in data["psychologist_users"]):
                data["psychologist_users"].append({
                    "psychologist_id": psychologist_id,
                    "user_id": user_id,
                    "status": "active",
                    "created_at": datetime.utcnow().isoformat()
                })
                _save_json_db(data)
            return True
        except Exception:
            return False
    
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO psychologist_users (psychologist_id, user_id, status, created_at) VALUES (%s, %s, 'active', %s) ON CONFLICT DO NOTHING",
            (psychologist_id, user_id, datetime.utcnow())
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"DEBUG: Error connecting psychologist to user: {e}")
        return False

def get_psychologist_users(psychologist_id: str):
    """Get all users assigned to a psychologist"""
    users = []
    
    # Try JSON fallback first
    try:
        data = _load_json_db()
        psych_users = data.get("psychologist_users", [])
        for pu in psych_users:
            if pu["psychologist_id"] == psychologist_id and pu["status"] == "active":
                # Find user details
                for user in data.get("users", []):
                    if user["email"] == pu["user_id"]:
                        users.append({
                            "user_id": pu["user_id"],
                            "name": user.get("name", "Unknown"),
                            "email": user.get("email"),
                            "connected_at": pu.get("created_at")
                        })
    except Exception:
        pass
    
    # Try database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT pu.user_id, u.name, u.email, pu.created_at as connected_at
                    FROM psychologist_users pu
                    LEFT JOIN users u ON pu.user_id = u.id
                    WHERE pu.psychologist_id = %s AND pu.status = 'active'
                    ORDER BY pu.created_at DESC
                """, (psychologist_id,))
                db_users = cursor.fetchall()
                cursor.close()
                conn.close()
                users.extend(db_users)
            except Exception as e:
                print(f"DEBUG: Error getting psychologist users: {e}")
    
    return users

def get_accepted_chat_users(psychologist_id: str):
    """Get users who have accepted chat requests with this psychologist"""
    psychologist_id = resolve_user_identifier(psychologist_id)
    users = []
    user_ids_seen = set()
    
    print(f"DEBUG DB: Getting accepted chat users for psychologist: {psychologist_id}")
    
    # Get from JSON
    try:
        data = _load_json_db()
        chat_requests = data.get("chat_requests", [])
        all_users = {u["email"]: u for u in data.get("users", [])}
        
        print(f"DEBUG DB: Total chat requests: {len(chat_requests)}")
        
        for req in chat_requests:
            if resolve_user_identifier(req.get("psychologist_id")) == psychologist_id and req["status"] == "accepted":
                user_id = resolve_user_identifier(req["user_id"])
                if user_id not in user_ids_seen:
                    user_ids_seen.add(user_id)
                    user_info = all_users.get(user_id, {})
                    users.append({
                        "user_id": user_id,
                        "name": user_info.get("name", "Unknown User"),
                        "email": user_id,
                        "connected_at": req.get("updated_at")
                    })
                    print(f"DEBUG DB: Added user {user_id}")

        for msg in data.get("direct_messages", []):
            sender_id = resolve_user_identifier(msg.get("sender_id"))
            receiver_id = resolve_user_identifier(msg.get("receiver_id"))
            if sender_id == psychologist_id:
                user_id = receiver_id
            elif receiver_id == psychologist_id:
                user_id = sender_id
            else:
                continue

            if user_id and user_id not in user_ids_seen:
                user_ids_seen.add(user_id)
                user_info = all_users.get(user_id, {})
                users.append({
                    "user_id": user_id,
                    "name": user_info.get("name", "Unknown User"),
                    "email": user_id,
                    "connected_at": msg.get("created_at")
                })
                print(f"DEBUG DB: Added direct-message user {user_id}")
        
        print(f"DEBUG DB: Found {len(users)} accepted chat users from JSON")
    except Exception as e:
        print(f"DEBUG DB: Error getting accepted users from JSON: {e}")
    
    # Try database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT DISTINCT cr.user_id, u.name, u.email, cr.updated_at as connected_at
                    FROM chat_requests cr
                    LEFT JOIN users u ON cr.user_id = u.email
                    WHERE cr.psychologist_id = %s AND cr.status = 'accepted'
                    ORDER BY cr.updated_at DESC
                """, (psychologist_id,))
                db_users = cursor.fetchall()
                cursor.close()
                conn.close()
                users.extend(db_users)
                print(f"DEBUG DB: Found {len(db_users)} users from database")
            except Exception as e:
                print(f"DEBUG DB: Error getting accepted users from DB: {e}")
            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT DISTINCT
                        CASE
                            WHEN dm.sender_id = %s THEN dm.receiver_id
                            ELSE dm.sender_id
                        END AS user_id,
                        u.name,
                        CASE
                            WHEN dm.sender_id = %s THEN dm.receiver_id
                            ELSE dm.sender_id
                        END AS email,
                        MAX(dm.created_at) AS connected_at
                    FROM direct_messages dm
                    LEFT JOIN users u ON u.email = CASE
                        WHEN dm.sender_id = %s THEN dm.receiver_id
                        ELSE dm.sender_id
                    END
                    WHERE dm.sender_id = %s OR dm.receiver_id = %s
                    GROUP BY user_id, u.name, email
                    ORDER BY connected_at DESC
                """, (psychologist_id, psychologist_id, psychologist_id, psychologist_id, psychologist_id))
                db_direct_users = cursor.fetchall()
                for user in db_direct_users:
                    user_id = user.get("user_id")
                    if user_id and user_id not in user_ids_seen:
                        user_ids_seen.add(user_id)
                        users.append(user)
                print(f"DEBUG DB: Found {len(db_direct_users)} direct-message users from database")
            except Exception as e:
                print(f"DEBUG DB: Error getting direct-message users from DB: {e}")
            finally:
                try:
                    cursor.close()
                    conn.close()
                except Exception:
                    pass
    
    return users

def save_direct_message(sender_id: str, receiver_id: str, message: str):
    """Save a direct message between psychologist and user"""
    sender_id = resolve_user_identifier(sender_id)
    receiver_id = resolve_user_identifier(receiver_id)

    # Save to JSON
    try:
        data = _load_json_db()
        if "direct_messages" not in data:
            data["direct_messages"] = []
        data["direct_messages"].append({
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message": message,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat()
        })
        _save_json_db(data)
    except Exception as e:
        print(f"DEBUG: Error saving message to JSON: {e}")
    
    # Save to database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO direct_messages (sender_id, receiver_id, message, is_read, created_at) VALUES (%s, %s, %s, FALSE, %s)",
                    (sender_id, receiver_id, message, datetime.utcnow())
                )
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"DEBUG: Error saving message to DB: {e}")
    
    return True

def get_direct_messages(user1_id: str, user2_id: str, limit: int = 100):
    """Get direct messages between two users"""
    user1_id = resolve_user_identifier(user1_id)
    user2_id = resolve_user_identifier(user2_id)
    messages = []
    
    # Get from JSON
    try:
        data = _load_json_db()
        direct_msgs = data.get("direct_messages", [])
        for msg in direct_msgs:
            if (msg["sender_id"] == user1_id and msg["receiver_id"] == user2_id) or \
               (msg["sender_id"] == user2_id and msg["receiver_id"] == user1_id):
                messages.append(msg)
    except Exception:
        pass
    
    # Get from database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT sender_id, receiver_id, message, is_read, created_at
                    FROM direct_messages
                    WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
                    ORDER BY created_at ASC
                    LIMIT %s
                """, (user1_id, user2_id, user2_id, user1_id, limit))
                db_messages = cursor.fetchall()
                cursor.close()
                conn.close()
                messages.extend(db_messages)
            except Exception as e:
                print(f"DEBUG: Error getting direct messages: {e}")
    
    # Sort by timestamp
    try:
        messages.sort(key=lambda m: m.get("created_at", ""))
    except Exception:
        pass
    
    return messages[-limit:]  # Return latest messages

# ===== Chat Request functions =====

def create_chat_request(request_id: str, user_id: str, psychologist_id: str, message: str = None):
    """Create a chat request from user to psychologist"""
    user_id = resolve_user_identifier(user_id)
    psychologist_id = resolve_user_identifier(psychologist_id)

    # Save to JSON
    try:
        data = _load_json_db()
        if "chat_requests" not in data:
            data["chat_requests"] = []
        data["chat_requests"].append({
            "request_id": request_id,
            "user_id": user_id,
            "psychologist_id": psychologist_id,
            "message": message,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
        _save_json_db(data)
    except Exception as e:
        print(f"DEBUG: Error saving chat request to JSON: {e}")
    
    # Save to database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_requests (request_id, user_id, psychologist_id, message, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'pending', %s, %s)
                """, (request_id, user_id, psychologist_id, message, datetime.utcnow(), datetime.utcnow()))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"DEBUG: Error saving chat request to DB: {e}")
    
    return True

def get_chat_request(request_id: str):
    """Get a specific chat request"""
    # Try JSON first
    try:
        data = _load_json_db()
        for req in data.get("chat_requests", []):
            if req["request_id"] == request_id:
                return req
    except Exception:
        pass
    
    # Try database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM chat_requests WHERE request_id = %s", (request_id,))
                req = cursor.fetchone()
                cursor.close()
                conn.close()
                if req:
                    return dict(req)
            except Exception as e:
                print(f"DEBUG: Error getting chat request: {e}")
    
    return None

def get_pending_requests(psychologist_id: str):
    """Get all pending chat requests for a psychologist"""
    psychologist_id = resolve_user_identifier(psychologist_id)
    requests = []
    
    print(f"DEBUG DB: Getting pending requests for psychologist: {psychologist_id}")
    
    # Try JSON first
    try:
        data = _load_json_db()
        all_requests = data.get("chat_requests", [])
        print(f"DEBUG DB: Total chat requests in JSON: {len(all_requests)}")
        for req in all_requests:
            print(f"DEBUG DB: Checking request - psychologist_id: {req.get('psychologist_id')}, status: {req.get('status')}")
            if req["psychologist_id"] == psychologist_id and req["status"] == "pending":
                requests.append(req)
                print(f"DEBUG DB: MATCHED! Added request: {req}")
        print(f"DEBUG DB: Found {len(requests)} pending requests from JSON")
    except Exception as e:
        print(f"DEBUG DB: Error loading from JSON: {e}")
        pass
    
    # Try database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT * FROM chat_requests 
                    WHERE psychologist_id = %s AND status = 'pending'
                    ORDER BY created_at DESC
                """, (psychologist_id,))
                db_requests = cursor.fetchall()
                cursor.close()
                conn.close()
                requests.extend(db_requests)
            except Exception as e:
                print(f"DEBUG DB: Error getting pending requests from DB: {e}")
    
    print(f"DEBUG DB: Returning {len(requests)} total pending requests")
    return requests

def update_chat_request_status(request_id: str, status: str):
    """Update chat request status (accepted, rejected, cancelled)"""
    # Update JSON
    try:
        data = _load_json_db()
        for req in data.get("chat_requests", []):
            if req["request_id"] == request_id:
                req["status"] = status
                req["updated_at"] = datetime.utcnow().isoformat()
                _save_json_db(data)
                break
    except Exception as e:
        print(f"DEBUG: Error updating chat request in JSON: {e}")
    
    # Update database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE chat_requests 
                    SET status = %s, updated_at = %s
                    WHERE request_id = %s
                """, (status, datetime.utcnow(), request_id))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"DEBUG: Error updating chat request in DB: {e}")
    
    return True

def get_available_psychologists(exclude_user_email=None):
    """Get all psychologists with status - optionally exclude a specific user"""
    psychologists = []
    exclude_user_email = resolve_user_identifier(exclude_user_email) if exclude_user_email else None
    
    # Get from JSON
    try:
        data = _load_json_db()
        print(f"DEBUG: JSON users loaded: {len(data.get('users', []))} total users")
        for user in data.get("users", []):
            email = str(user.get("email") or "").lower()
            print(f"DEBUG: Checking user {user.get('name')} with type: {user.get('user_type')}, email: {email}")
            
            # Skip if this is the excluded user
            if exclude_user_email and email == exclude_user_email:
                print(f"DEBUG: Skipping {email} (excluded user)")
                continue
                
            if user.get("user_type") == "psychologist":
                psychologists.append({
                    "id": email,
                    "name": user.get("name"),
                    "email": email,
                    "specialization": user.get("specialization", "General Counseling"),
                    "bio": user.get("bio", "Professional mental health expert"),
                    "rating": user.get("rating", "4.8"),
                    "experience": user.get("experience", "5"),
                    "status": "available"
                })
        print(f"DEBUG: Found {len(psychologists)} psychologists from JSON")
    except Exception as e:
        print(f"DEBUG: Error loading psychologists from JSON: {e}")
        pass
    
    # Get from database
    if not _use_json_fallback:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("""
                    SELECT id, email, name, user_type FROM users 
                    WHERE user_type = 'psychologist'
                """)
                db_psychologists = cursor.fetchall()
                cursor.close()
                conn.close()
                
                for psych in db_psychologists:
                    psych_email = str(psych.get("email") or "").lower()
                    if exclude_user_email and psych_email == exclude_user_email:
                        continue
                    psychologists.append({
                        "id": psych_email,
                        "name": psych.get("name"),
                        "email": psych_email,
                        "specialization": "General Counseling",
                        "bio": "Professional mental health expert",
                        "rating": "4.8",
                        "experience": "5",
                        "status": "available"
                    })
                print(f"DEBUG: Found {len(db_psychologists)} psychologists from database")
            except Exception as e:
                print(f"DEBUG: Error getting psychologists from DB: {e}")
    
    deduped = []
    seen = set()
    for psych in psychologists:
        email = str(psych.get("email") or "").lower()
        if not email or email in seen:
            continue
        seen.add(email)
        deduped.append(psych)

    return deduped
