"""
Supabase Client Integration for Mental Health Chatbot
Supabase-only database operations (no local fallback)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional, List, Dict, Any
import time


class SupabaseClient:
    """Main Supabase Client for database operations"""
    
    def __init__(self):
        self._connection_cache = None
        self._last_connection_check = 0
        self._connection_check_interval = 30  # Check connection every 30 seconds
        
    def _ensure_connection(self):
        """Ensure database connection is valid"""
        current_time = time.time()
        if current_time - self._last_connection_check > self._connection_check_interval:
            self._last_connection_check = current_time
            self.check_connection()

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
            print(f"ERROR: Database Connection Error: {err}")
            return None

    def check_connection(self) -> bool:
        """Check if database connection is available"""
        try:
            conn = self.get_db_connection()
            if conn:
                conn.close()
                print("DEBUG: Supabase connection verified")
                return True
            else:
                print("ERROR: Failed to connect to Supabase")
                return False
        except Exception as e:
            print(f"ERROR: Connection check failed: {e}")
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
        
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot create user - no Supabase connection")
            return None

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
                return user_id
            return None
        except Exception as e:
            print(f"ERROR: Error creating user in Supabase: {e}")
            return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        email = email.lower().strip()
        
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot get user - no Supabase connection")
            return None
            
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
            print(f"ERROR: Error getting user: {e}")
            try:
                conn.close()
            except:
                pass
        
        return None

    def get_all_psychologists(self) -> List[Dict[str, Any]]:
        """Get all psychologists"""
        psychologists = []
        
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot get psychologists - no Supabase connection")
            return []
            
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
            print(f"ERROR: Error getting psychologists: {e}")
            try:
                conn.close()
            except:
                pass
        
        return psychologists

    def save_direct_message(self, sender_id: str, receiver_id: str, message: str) -> bool:
        """Save a direct message between users"""
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot save message - no Supabase connection")
            return False
            
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
            return True
        except Exception as e:
            print(f"ERROR: Error saving message: {e}")
            try:
                conn.close()
            except:
                pass
            return False

    def get_direct_messages(self, user_id_1: str, user_id_2: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get direct messages between two users"""
        messages = []
        
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot get messages - no Supabase connection")
            return []
            
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
            print(f"ERROR: Error getting messages: {e}")
            try:
                conn.close()
            except:
                pass
        
        return messages

    def save_chat_request(self, request_id: str, user_id: str, psychologist_id: str, 
                         message: str = "", status: str = "pending") -> bool:
        """Save a chat request"""
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot save chat request - no Supabase connection")
            return False
            
        try:
            now = datetime.utcnow()
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
            return True
        except Exception as e:
            print(f"ERROR: Error saving chat request: {e}")
            try:
                conn.close()
            except:
                pass
            return False

    def get_pending_chat_requests(self, psychologist_id: str) -> List[Dict[str, Any]]:
        """Get pending chat requests for a psychologist"""
        requests = []
        
        conn = self.get_db_connection()
        if not conn:
            print("ERROR: Cannot get chat requests - no Supabase connection")
            return []
            
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
            print(f"ERROR: Error getting pending requests: {e}")
            try:
                conn.close()
            except:
                pass
        
        return requests

    def accept_chat_request(self, request_id: str) -> bool:
        """Accept a chat request"""
        return self.save_chat_request(request_id, "", "", "", status="accepted")

    def reject_chat_request(self, request_id: str) -> bool:
        """Reject a chat request"""
        return self.save_chat_request(request_id, "", "", "", status="rejected")


# Initialize global client
supabase_client = SupabaseClient()
