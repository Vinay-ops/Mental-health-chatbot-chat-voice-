"""
Supabase Client Integration for Mental Health Chatbot
Handles all database operations with real-time support
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import wraps
import time

# Fallback JSON File
JSON_DB_FILE = "local_db.json"

class SupabaseClient:
    """Main Supabase Client for database operations"""
    
    def __init__(self):
        self._use_json_fallback = False
        self._connection_cache = None
        self._last_connection_check = 0
        self._connection_check_interval = 30  # Check connection every 30 seconds
        
    def _ensure_connection(self):
        """Ensure database connection is valid"""
        current_time = time.time()
        if current_time - self._last_connection_check > self._connection_check_interval:
            self._last_connection_check = current_time
            self.check_connection()
    
    def _load_json_db(self) -> Dict[str, Any]:
        """Load local JSON database"""
        if not os.path.exists(JSON_DB_FILE):
            return {
                "users": [], 
                "chat_logs": [], 
                "community_posts": [],
                "psychologist_users": [],
                "direct_messages": [],
                "chat_requests": []
            }
        try:
            with open(JSON_DB_FILE, 'r') as f:
                data = json.load(f)
                # Ensure all required keys exist
                for key in ["users", "chat_logs", "community_posts", "psychologist_users", 
                           "direct_messages", "chat_requests"]:
                    if key not in data:
                        data[key] = []
                return data
        except Exception as e:
            print(f"DEBUG: Error loading JSON DB: {e}")
            return {"users": [], "chat_logs": [], "community_posts": [], 
                   "psychologist_users": [], "direct_messages": [], "chat_requests": []}

    def _save_json_db(self, data: Dict[str, Any]) -> bool:
        """Save local JSON database"""
        try:
            with open(JSON_DB_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"DEBUG: Error saving JSON DB: {e}")
            return False

    def get_db_connection(self):
        """Get PostgreSQL/Supabase connection"""
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                conn = psycopg2.connect(database_url, connect_timeout=10)
                return conn
            else:
                host = os.getenv("PG_HOST", "localhost")
                port = int(os.getenv("PG_PORT", "5432"))
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
            print(f"DEBUG: Database Connection Error: {err}")
            self._use_json_fallback = True
            return None

    def check_connection(self) -> bool:
        """Check if database connection is available"""
        try:
            conn = self.get_db_connection()
            if conn:
                conn.close()
                self._use_json_fallback = False
                return True
            else:
                self._use_json_fallback = True
                return False
        except Exception as e:
            print(f"DEBUG: Connection check failed: {e}")
            self._use_json_fallback = True
            return False

    def ensure_schema(self) -> bool:
        """Ensure database schema exists"""
        conn = self.get_db_connection()
        if not conn:
            print("DEBUG: Cannot ensure schema - no connection")
            return False
        
        try:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    name VARCHAR(255),
                    user_type VARCHAR(50) DEFAULT 'user',
                    specialization VARCHAR(255),
                    license_number VARCHAR(255),
                    bio TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create chat_logs table
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
            
            # Create community_posts table
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
            
            # Create psychologist_users table
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
            
            # Create direct_messages table
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
            
            # Create chat_requests table
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
            
            # Add columns if they don't exist (for migrations)
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN specialization VARCHAR(255)")
            except:
                pass
            
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN license_number VARCHAR(255)")
            except:
                pass
            
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
            except:
                pass
            
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
            except:
                pass
            
            conn.commit()
            cursor.close()
            conn.close()
            print("DEBUG: Database schema ensured successfully")
            return True
        except Exception as e:
            print(f"DEBUG: Schema error: {e}")
            return False

    def create_user(self, email: str, password_hash: str, name: str, 
                   user_type: str = "user", **kwargs) -> Optional[str]:
        """Create a new user"""
        email = email.lower().strip()
        
        # Try Supabase first
        if not self._use_json_fallback:
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        """INSERT INTO users (email, password_hash, name, user_type, created_at, updated_at) 
                           VALUES (%s, %s, %s, %s, %s, %s) 
                           RETURNING id, email""",
                        (email, password_hash, name, user_type, datetime.utcnow(), datetime.utcnow())
                    )
                    row = cursor.fetchone()
                    conn.commit()
                    cursor.close()
                    conn.close()
                    if row:
                        user_id = str(row[0])
                        print(f"DEBUG: Created user in Supabase: {email} (ID: {user_id}, Type: {user_type})")
                        # Also save to local JSON for consistency
                        self._create_user_json(email, password_hash, name, user_type, **kwargs)
                        return user_id
                except Exception as e:
                    print(f"DEBUG: Error creating user in Supabase: {e}")
                    self._use_json_fallback = True

        # Fallback to JSON
        return self._create_user_json(email, password_hash, name, user_type, **kwargs)

    def _create_user_json(self, email: str, password_hash: str, name: str, 
                         user_type: str = "user", **kwargs) -> str:
        """Create user in local JSON database"""
        try:
            data = self._load_json_db()
            # Check if user already exists
            if any(u["email"] == email for u in data["users"]):
                print(f"DEBUG: User already exists: {email}")
                return email
            
            new_user = {
                "email": email,
                "password_hash": password_hash,
                "name": name,
                "user_type": user_type,
                "created_at": datetime.utcnow().isoformat()
            }
            # Add any extra fields like specialization, license_number, bio
            new_user.update(kwargs)
            
            data["users"].append(new_user)
            self._save_json_db(data)
            print(f"DEBUG: Created user in JSON: {email} (Type: {user_type})")
            return email
        except Exception as e:
            print(f"DEBUG: Error creating user in JSON: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        email = email.lower().strip()
        
        # Try Supabase first (Primary source)
        if not self._use_json_fallback:
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT id as _id, email, password_hash, name, user_type, 
                               specialization, license_number, bio, created_at
                        FROM users 
                        WHERE LOWER(email) = LOWER(%s)
                    """, (email,))
                    user = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if user:
                        print(f"DEBUG: Found user in Supabase: {email} (Type: {user.get('user_type')})")
                        return user
                except Exception as e:
                    print(f"DEBUG: Error getting user from Supabase: {e}")

        # Fallback to JSON
        try:
            data = self._load_json_db()
            for user in data["users"]:
                if user.get("email", "").lower() == email.lower():
                    user["_id"] = user.get("email")
                    print(f"DEBUG: Found user in JSON: {email} (Type: {user.get('user_type')})")
                    return user
        except Exception as e:
            print(f"DEBUG: Error getting user from JSON: {e}")
        
        return None

    def get_all_psychologists(self) -> List[Dict[str, Any]]:
        """Get all psychologists"""
        psychologists = []
        
        # Try Supabase first
        if not self._use_json_fallback:
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT id, email, name, specialization, license_number, bio, created_at
                        FROM users 
                        WHERE user_type = 'psychologist'
                        ORDER BY created_at DESC
                    """)
                    psychologists = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    print(f"DEBUG: Retrieved {len(psychologists)} psychologists from Supabase")
                except Exception as e:
                    print(f"DEBUG: Error getting psychologists from Supabase: {e}")

        # If Supabase fails or no results, try JSON
        if not psychologists:
            try:
                data = self._load_json_db()
                psychologists = [
                    {
                        "_id": u.get("email"),
                        "email": u.get("email"),
                        "name": u.get("name"),
                        "specialization": u.get("specialization", ""),
                        "license_number": u.get("license_number", ""),
                        "bio": u.get("bio", ""),
                        "created_at": u.get("created_at")
                    }
                    for u in data.get("users", []) 
                    if u.get("user_type") == "psychologist"
                ]
                print(f"DEBUG: Retrieved {len(psychologists)} psychologists from JSON")
            except Exception as e:
                print(f"DEBUG: Error getting psychologists from JSON: {e}")
        
        return psychologists

    def save_direct_message(self, sender_id: str, receiver_id: str, message: str) -> bool:
        """Save a direct message between users"""
        try:
            # Try Supabase first
            if not self._use_json_fallback:
                conn = self.get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO direct_messages (sender_id, receiver_id, message, is_read, created_at)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (sender_id, receiver_id, message, False, datetime.utcnow()))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        print(f"DEBUG: Saved message to Supabase from {sender_id} to {receiver_id}")
                    except Exception as e:
                        print(f"DEBUG: Error saving message to Supabase: {e}")
                        self._use_json_fallback = True
            
            # Always save to JSON for local redundancy
            data = self._load_json_db()
            data["direct_messages"].append({
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "message": message,
                "is_read": False,
                "created_at": datetime.utcnow().isoformat()
            })
            self._save_json_db(data)
            return True
        except Exception as e:
            print(f"DEBUG: Error saving direct message: {e}")
            return False

    def get_direct_messages(self, user_id_1: str, user_id_2: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get direct messages between two users"""
        messages = []
        
        # Try Supabase
        if not self._use_json_fallback:
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT id, sender_id, receiver_id, message, is_read, created_at
                        FROM direct_messages
                        WHERE (sender_id = %s AND receiver_id = %s)
                           OR (sender_id = %s AND receiver_id = %s)
                        ORDER BY created_at ASC
                        LIMIT %s
                    """, (user_id_1, user_id_2, user_id_2, user_id_1, limit))
                    messages = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    print(f"DEBUG: Retrieved {len(messages)} messages from Supabase")
                except Exception as e:
                    print(f"DEBUG: Error getting messages from Supabase: {e}")

        # Fallback to JSON
        if not messages:
            try:
                data = self._load_json_db()
                for msg in data.get("direct_messages", []):
                    if ((msg["sender_id"] == user_id_1 and msg["receiver_id"] == user_id_2) or
                        (msg["sender_id"] == user_id_2 and msg["receiver_id"] == user_id_1)):
                        messages.append(msg)
                messages.sort(key=lambda m: m.get("created_at", ""))
                messages = messages[-limit:]
                print(f"DEBUG: Retrieved {len(messages)} messages from JSON")
            except Exception as e:
                print(f"DEBUG: Error getting messages from JSON: {e}")
        
        return messages

    def save_chat_request(self, request_id: str, user_id: str, psychologist_id: str, 
                         message: str = "", status: str = "pending") -> bool:
        """Save a chat request"""
        try:
            now = datetime.utcnow()
            
            # Try Supabase
            if not self._use_json_fallback:
                conn = self.get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO chat_requests (request_id, user_id, psychologist_id, message, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (request_id) DO UPDATE 
                            SET status = %s, updated_at = %s
                        """, (request_id, user_id, psychologist_id, message, status, now, now, status, now))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        print(f"DEBUG: Saved chat request to Supabase: {request_id}")
                    except Exception as e:
                        print(f"DEBUG: Error saving chat request to Supabase: {e}")
                        self._use_json_fallback = True
            
            # Always save to JSON
            data = self._load_json_db()
            # Remove if exists
            data["chat_requests"] = [r for r in data.get("chat_requests", []) if r["request_id"] != request_id]
            # Add new
            data["chat_requests"].append({
                "request_id": request_id,
                "user_id": user_id,
                "psychologist_id": psychologist_id,
                "message": message,
                "status": status,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            })
            self._save_json_db(data)
            return True
        except Exception as e:
            print(f"DEBUG: Error saving chat request: {e}")
            return False

    def get_pending_chat_requests(self, psychologist_id: str) -> List[Dict[str, Any]]:
        """Get pending chat requests for a psychologist"""
        requests = []
        
        # Try Supabase
        if not self._use_json_fallback:
            conn = self.get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT request_id, user_id, psychologist_id, message, status, created_at
                        FROM chat_requests
                        WHERE psychologist_id = %s AND status = 'pending'
                        ORDER BY created_at DESC
                    """, (psychologist_id,))
                    requests = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    print(f"DEBUG: Retrieved {len(requests)} pending requests from Supabase")
                except Exception as e:
                    print(f"DEBUG: Error getting pending requests from Supabase: {e}")

        # Fallback to JSON
        if not requests:
            try:
                data = self._load_json_db()
                requests = [
                    r for r in data.get("chat_requests", [])
                    if r.get("psychologist_id") == psychologist_id and r.get("status") == "pending"
                ]
                requests.sort(key=lambda r: r.get("created_at", ""), reverse=True)
                print(f"DEBUG: Retrieved {len(requests)} pending requests from JSON")
            except Exception as e:
                print(f"DEBUG: Error getting pending requests from JSON: {e}")
        
        return requests

    def accept_chat_request(self, request_id: str) -> bool:
        """Accept a chat request"""
        return self.save_chat_request(request_id, "", "", "", status="accepted")

    def reject_chat_request(self, request_id: str) -> bool:
        """Reject a chat request"""
        return self.save_chat_request(request_id, "", "", "", status="rejected")


# Initialize global client
supabase_client = SupabaseClient()
