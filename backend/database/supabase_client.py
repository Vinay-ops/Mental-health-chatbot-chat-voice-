"""
Supabase PostgreSQL client for MindCare Navigator.
Provides connection management and schema initialization.
"""

import os
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)


class SupabaseClient:
    """Manages PostgreSQL connections to Supabase."""

    def get_db_connection(self):
        """Create a new PostgreSQL connection."""
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                return psycopg2.connect(database_url, connect_timeout=10)

            host = os.getenv("PG_HOST", "localhost")
            port = int(os.getenv("PG_PORT", "5432"))
            dbname = os.getenv("PG_DATABASE", "postgres")
            user = os.getenv("PG_USER", "postgres")
            password = os.getenv("PG_PASSWORD", "")

            kwargs = {
                "host": host, "port": port, "dbname": dbname,
                "user": user, "password": password, "connect_timeout": 10,
            }
            if host.endswith("supabase.co"):
                kwargs["sslmode"] = "require"

            return psycopg2.connect(**kwargs)
        except Exception as err:
            log.error("Database connection failed: %s", err)
            return None

    @contextmanager
    def connection(self):
        """Context manager that yields a connection and ensures cleanup."""
        conn = self.get_db_connection()
        if conn is None:
            raise ConnectionError("No database connection available")
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def check_connection(self) -> bool:
        """Verify the database is reachable."""
        try:
            with self.connection():
                log.info("Supabase connection verified")
                return True
        except Exception:
            return False

    def ensure_schema(self) -> bool:
        """Create tables and indexes if they don't exist."""
        try:
            with self.connection() as conn:
                cur = conn.cursor()

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        name VARCHAR(255),
                        user_type VARCHAR(50) DEFAULT 'user',
                        availability_status VARCHAR(50) DEFAULT 'available',
                        specialization VARCHAR(255),
                        license_number VARCHAR(255),
                        bio TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chat_logs (
                        id SERIAL PRIMARY KEY,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        user_id VARCHAR(255),
                        session_id VARCHAR(255),
                        ts TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_session ON chat_logs (user_id, session_id)")

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS community_posts (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255),
                        name VARCHAR(255),
                        content TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        likes INT DEFAULT 0
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS psychologist_users (
                        id SERIAL PRIMARY KEY,
                        psychologist_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        status VARCHAR(50) DEFAULT 'active',
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(psychologist_id, user_id)
                    )
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS direct_messages (
                        id SERIAL PRIMARY KEY,
                        sender_id VARCHAR(255) NOT NULL,
                        receiver_id VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        is_read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("CREATE INDEX IF NOT EXISTS idx_direct_messages ON direct_messages (sender_id, receiver_id, created_at DESC)")

                cur.execute("""
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

                cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_requests_status ON chat_requests (psychologist_id, status)")

                # Migration: add columns that may not exist yet
                for col, definition in [
                    ("specialization", "VARCHAR(255)"),
                    ("license_number", "VARCHAR(255)"),
                    ("bio", "TEXT"),
                    ("availability_status", "VARCHAR(50) DEFAULT 'available'"),
                    ("updated_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"),
                ]:
                    try:
                        cur.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
                    except Exception:
                        pass  # Column already exists

                conn.commit()
                cur.close()
                log.info("Database schema ensured successfully")
                return True
        except Exception as e:
            log.error("Schema error: %s", e)
            return False

    def create_user(self, email: str, password_hash: str, name: str,
                    user_type: str = "user") -> Optional[str]:
        email = email.lower().strip()
        try:
            with self.connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO users (email, password_hash, name, user_type, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                    (email, password_hash, name, user_type, datetime.utcnow(), datetime.utcnow()),
                )
                row = cur.fetchone()
                conn.commit()
                cur.close()
                if row:
                    log.info("Created user: %s (id=%s, type=%s)", email, row[0], user_type)
                    return str(row[0])
        except Exception as e:
            log.error("Error creating user %s: %s", email, e)
        return None

    def get_user_by_email(self, email: str):
        email = email.lower().strip()
        try:
            with self.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cur.execute(
                        """SELECT id as _id, email, password_hash, name, user_type,
                                  availability_status, specialization, license_number, bio, created_at
                           FROM users WHERE LOWER(email) = LOWER(%s)""",
                        (email,),
                    )
                except Exception:
                    conn.rollback()
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute(
                        """SELECT id as _id, email, password_hash, name, user_type,
                                  specialization, license_number, bio, created_at
                           FROM users WHERE LOWER(email) = LOWER(%s)""",
                        (email,),
                    )
                user = cur.fetchone()
                cur.close()
                if user and "availability_status" not in user:
                    user["availability_status"] = "available"
                return user
        except Exception as e:
            log.error("Error getting user %s: %s", email, e)
            return None

    def get_all_psychologists(self):
        try:
            with self.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cur.execute(
                        """SELECT id, email, name, availability_status, specialization,
                                  license_number, bio, created_at
                           FROM users WHERE user_type = 'psychologist' ORDER BY created_at DESC"""
                    )
                except Exception:
                    conn.rollback()
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute(
                        """SELECT id, email, name, specialization, license_number, bio, created_at
                           FROM users WHERE user_type = 'psychologist' ORDER BY created_at DESC"""
                    )
                psychologists = cur.fetchall()
                cur.close()
                for p in psychologists:
                    if "availability_status" not in p:
                        p["availability_status"] = "available"
                return psychologists
        except Exception as e:
            log.error("Error getting psychologists: %s", e)
            return []

    def save_direct_message(self, sender_id: str, receiver_id: str, message: str) -> bool:
        try:
            with self.connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO direct_messages (sender_id, receiver_id, message, is_read, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (sender_id, receiver_id, message, False, datetime.utcnow()),
                )
                conn.commit()
                cur.close()
                return True
        except Exception as e:
            log.error("Error saving message: %s", e)
            return False

    def get_direct_messages(self, user_id_1: str, user_id_2: str, limit: int = 50):
        try:
            with self.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    """SELECT id, sender_id, receiver_id, message, is_read, created_at
                       FROM direct_messages
                       WHERE (sender_id = %s AND receiver_id = %s)
                          OR (sender_id = %s AND receiver_id = %s)
                       ORDER BY created_at ASC LIMIT %s""",
                    (user_id_1, user_id_2, user_id_2, user_id_1, limit),
                )
                messages = cur.fetchall()
                cur.close()
                return messages
        except Exception as e:
            log.error("Error getting messages: %s", e)
            return []

    def save_chat_request(self, request_id: str, user_id: str, psychologist_id: str,
                          message: str = "", status: str = "pending") -> bool:
        try:
            with self.connection() as conn:
                now = datetime.utcnow()
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO chat_requests
                       (request_id, user_id, psychologist_id, message, status, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (request_id) DO UPDATE SET status = %s, updated_at = %s""",
                    (request_id, user_id, psychologist_id, message, status, now, now, status, now),
                )
                conn.commit()
                cur.close()
                return True
        except Exception as e:
            log.error("Error saving chat request: %s", e)
            return False

    def get_pending_chat_requests(self, psychologist_id: str):
        try:
            with self.connection() as conn:
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    """SELECT request_id, user_id, psychologist_id, message, status, created_at
                       FROM chat_requests
                       WHERE psychologist_id = %s AND status = 'pending'
                       ORDER BY created_at DESC""",
                    (psychologist_id,),
                )
                requests = cur.fetchall()
                cur.close()
                return requests
        except Exception as e:
            log.error("Error getting pending requests: %s", e)
            return []

    def accept_chat_request(self, request_id: str) -> bool:
        return self.save_chat_request(request_id, "", "", "", status="accepted")

    def reject_chat_request(self, request_id: str) -> bool:
        return self.save_chat_request(request_id, "", "", "", status="rejected")


# Global singleton
supabase_client = SupabaseClient()
