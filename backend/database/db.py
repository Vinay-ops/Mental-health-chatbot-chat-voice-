"""
MindCare Navigator — Database Layer
All operations routed through Supabase PostgreSQL.
"""

import logging
from datetime import datetime
from urllib.parse import unquote

from psycopg2.extras import RealDictCursor

from backend.database.supabase_client import supabase_client

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_db_connection():
    return supabase_client.get_db_connection()


def check_connection():
    return supabase_client.check_connection()


def ensure_schema():
    return supabase_client.ensure_schema()


# ---------------------------------------------------------------------------
# Identifier resolution
# ---------------------------------------------------------------------------

def _normalize_identifier(identifier: str):
    if identifier is None:
        return None
    text = str(identifier).strip()
    if not text:
        return None
    try:
        return unquote(text) or text
    except Exception:
        return text


def resolve_user_identifier(identifier: str):
    """Resolve email-or-ID to canonical email."""
    normalized = _normalize_identifier(identifier)
    if not normalized:
        return normalized
    if "@" in normalized:
        return normalized.lower()

    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT email FROM users WHERE LOWER(email) = LOWER(%s) OR id::text = %s",
                (normalized, normalized),
            )
            row = cur.fetchone()
            cur.close()
            if row and row.get("email"):
                return str(row["email"]).lower()
    except Exception as e:
        log.error("Error resolving identifier: %s", e)

    return normalized.lower()


def get_user_identifier_aliases(identifier: str):
    """Return all email/id aliases for a user."""
    normalized = _normalize_identifier(identifier)
    if not normalized:
        return []

    aliases = {normalized.lower()}
    canonical = resolve_user_identifier(normalized)
    if canonical:
        aliases.add(canonical.lower())

    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT id, email FROM users WHERE LOWER(email) = LOWER(%s) OR id::text = %s",
                (canonical or normalized, normalized),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                if row.get("id") is not None:
                    aliases.add(str(row["id"]))
                if row.get("email"):
                    aliases.add(str(row["email"]).lower())
    except Exception as e:
        log.error("Error getting identifier aliases: %s", e)

    return list(aliases)


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

def get_user_by_email(email: str):
    return supabase_client.get_user_by_email(email)


def create_user(email: str, password_hash: str, name: str, user_type: str = "user"):
    return supabase_client.create_user(email, password_hash, name, user_type)


def get_all_psychologists():
    return supabase_client.get_all_psychologists()


def get_available_psychologists(exclude_user_email=None):
    exclude_email = resolve_user_identifier(exclude_user_email) if exclude_user_email else None
    psychologists = supabase_client.get_all_psychologists()

    if exclude_email:
        psychologists = [
            p for p in psychologists
            if str(p.get("email") or "").lower() != exclude_email.lower()
        ]

    return [
        {
            "id": p.get("email", ""),
            "name": p.get("name", ""),
            "email": p.get("email", ""),
            "specialization": p.get("specialization", "General Counseling"),
            "bio": p.get("bio", "Professional mental health expert"),
            "rating": "4.8",
            "experience": "5",
            "status": p.get("availability_status") or "available",
        }
        for p in psychologists
    ]


def update_psychologist_status(psychologist_id: str, status: str):
    psychologist_id = resolve_user_identifier(psychologist_id)
    if status not in {"available", "busy", "offline"}:
        log.error("Invalid psychologist status: %s", status)
        return False

    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE users SET availability_status = %s, updated_at = %s
                   WHERE LOWER(email) = LOWER(%s) AND user_type = 'psychologist'""",
                (status, datetime.utcnow(), psychologist_id),
            )
            updated = cur.rowcount > 0
            conn.commit()
            cur.close()
            return updated
    except Exception as e:
        log.error("Error updating psychologist status: %s", e)
        return False


# ---------------------------------------------------------------------------
# Chat logs
# ---------------------------------------------------------------------------

def save_log(role: str, content: str, user_id: str = None, session_id: str = None):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO chat_logs (role, content, user_id, session_id, ts) VALUES (%s, %s, %s, %s, %s)",
                (role, content, str(user_id) if user_id else None, session_id, datetime.utcnow()),
            )
            conn.commit()
            cur.close()
    except Exception as e:
        log.error("Error saving log: %s", e)


def get_chat_history(user_id: str, session_id: str):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            if user_id:
                cur.execute(
                    "SELECT role, content, user_id, session_id, ts FROM chat_logs "
                    "WHERE user_id = %s AND session_id = %s ORDER BY ts ASC",
                    (str(user_id), session_id),
                )
            else:
                cur.execute(
                    "SELECT role, content, user_id, session_id, ts FROM chat_logs "
                    "WHERE user_id IS NULL AND session_id = %s ORDER BY ts ASC",
                    (session_id,),
                )
            history = cur.fetchall()
            cur.close()
            return history
    except Exception as e:
        log.error("Error getting history: %s", e)
        return []


def get_user_sessions(user_id: str):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor()
            if user_id:
                cur.execute(
                    "SELECT session_id FROM chat_logs WHERE user_id = %s AND session_id IS NOT NULL GROUP BY session_id",
                    (str(user_id),),
                )
            else:
                cur.execute(
                    "SELECT session_id FROM chat_logs WHERE user_id IS NULL AND session_id IS NOT NULL GROUP BY session_id",
                    (),
                )
            sessions = sorted([row[0] for row in cur.fetchall()], reverse=True)
            cur.close()
            return sessions
    except Exception as e:
        log.error("Error getting sessions: %s", e)
        return []


# ---------------------------------------------------------------------------
# Community posts
# ---------------------------------------------------------------------------

def add_community_post(user_id: str, name: str, content: str):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO community_posts (user_id, name, content, created_at, likes) VALUES (%s, %s, %s, %s, %s)",
                (str(user_id) if user_id else None, name, content, datetime.utcnow(), 0),
            )
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        log.error("Error adding post: %s", e)
        return False


def get_community_posts(limit: int = 30):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT id, user_id, name, content, created_at, likes "
                "FROM community_posts ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            posts = cur.fetchall()
            cur.close()
            return posts
    except Exception as e:
        log.error("Error getting posts: %s", e)
        return []


def like_community_post(post_id: int):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE community_posts SET likes = COALESCE(likes, 0) + 1 WHERE id = %s",
                (post_id,),
            )
            conn.commit()
            cur.execute("SELECT likes FROM community_posts WHERE id = %s", (post_id,))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
    except Exception as e:
        log.error("Error liking post: %s", e)
        return None


# ---------------------------------------------------------------------------
# Psychologist-user connections
# ---------------------------------------------------------------------------

def connect_psychologist_to_user(psychologist_id: str, user_id: str):
    psychologist_id = resolve_user_identifier(psychologist_id)
    user_id = resolve_user_identifier(user_id)

    if not psychologist_id or not user_id:
        log.error("Cannot connect: missing psychologist_id or user_id")
        return False

    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO psychologist_users (psychologist_id, user_id, status, created_at) "
                "VALUES (%s, %s, 'active', %s) ON CONFLICT DO NOTHING",
                (psychologist_id, user_id, datetime.utcnow()),
            )
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        log.error("Error connecting: %s", e)
        return False


def get_psychologist_users(psychologist_id: str):
    psychologist_id = resolve_user_identifier(psychologist_id)
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """SELECT pu.user_id, u.name, u.email, pu.created_at as connected_at
                   FROM psychologist_users pu
                   LEFT JOIN users u ON pu.user_id = u.email
                   WHERE pu.psychologist_id = %s AND pu.status = 'active'
                   ORDER BY pu.created_at DESC""",
                (psychologist_id,),
            )
            users = cur.fetchall()
            cur.close()
            return users
    except Exception as e:
        log.error("Error getting users: %s", e)
        return []


def get_accepted_chat_users(psychologist_id: str):
    """Get users who have accepted chat requests with this psychologist."""
    psychologist_id = resolve_user_identifier(psychologist_id)
    psychologist_aliases = get_user_identifier_aliases(psychologist_id)

    users = []
    user_ids_seen = set()

    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 1) Explicit psychologist-user links
            cur.execute(
                """SELECT DISTINCT pu.user_id, u.name, COALESCE(u.email, pu.user_id) AS email,
                          pu.created_at as connected_at
                   FROM psychologist_users pu
                   LEFT JOIN users u ON pu.user_id = u.email OR pu.user_id = u.id::text
                   WHERE pu.psychologist_id = ANY(%s) AND pu.status = 'active'
                   ORDER BY pu.created_at DESC""",
                (psychologist_aliases,),
            )
            for user in cur.fetchall():
                uid = user.get("email") or user.get("user_id")
                if uid and uid not in user_ids_seen:
                    user["user_id"] = uid
                    user_ids_seen.add(uid)
                    users.append(user)

            # 2) Accepted chat requests
            cur.execute(
                """SELECT DISTINCT cr.user_id, u.name, u.email, cr.updated_at as connected_at
                   FROM chat_requests cr
                   LEFT JOIN users u ON cr.user_id = u.email OR cr.user_id = u.id::text
                   WHERE cr.psychologist_id = ANY(%s) AND cr.status = 'accepted'
                   ORDER BY cr.updated_at DESC""",
                (psychologist_aliases,),
            )
            for user in cur.fetchall():
                uid = user.get("email") or user.get("user_id")
                if uid and uid not in user_ids_seen:
                    user["user_id"] = uid
                    user_ids_seen.add(uid)
                    users.append(user)

            # 3) Direct message history
            cur.execute(
                """SELECT DISTINCT
                       CASE WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id ELSE dm.sender_id END AS user_id,
                       u.name,
                       COALESCE(u.email, CASE WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id ELSE dm.sender_id END) AS email,
                       MAX(dm.created_at) AS connected_at
                   FROM direct_messages dm
                   LEFT JOIN users u ON u.email = CASE
                       WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id ELSE dm.sender_id
                   END OR u.id::text = CASE
                       WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id ELSE dm.sender_id
                   END
                   WHERE dm.sender_id = ANY(%s) OR dm.receiver_id = ANY(%s)
                   GROUP BY user_id, u.name, email
                   ORDER BY connected_at DESC""",
                (psychologist_aliases, psychologist_aliases,
                 psychologist_aliases, psychologist_aliases,
                 psychologist_aliases, psychologist_aliases),
            )
            for user in cur.fetchall():
                uid = user.get("email") or user.get("user_id")
                if uid and uid not in user_ids_seen:
                    user["user_id"] = uid
                    user_ids_seen.add(uid)
                    users.append(user)

            cur.close()
    except Exception as e:
        log.error("Error getting accepted users: %s", e)

    return users


# ---------------------------------------------------------------------------
# Direct messages
# ---------------------------------------------------------------------------

def save_direct_message(sender_id: str, receiver_id: str, message: str):
    sender_id = resolve_user_identifier(sender_id)
    receiver_id = resolve_user_identifier(receiver_id)
    return supabase_client.save_direct_message(sender_id, receiver_id, message)


def get_direct_messages(user1_id: str, user2_id: str, limit: int = 100):
    user1_aliases = get_user_identifier_aliases(user1_id)
    user2_aliases = get_user_identifier_aliases(user2_id)

    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """SELECT id, sender_id, receiver_id, message, is_read, created_at
                   FROM direct_messages
                   WHERE (sender_id = ANY(%s) AND receiver_id = ANY(%s))
                      OR (sender_id = ANY(%s) AND receiver_id = ANY(%s))
                   ORDER BY created_at ASC LIMIT %s""",
                (user1_aliases, user2_aliases, user2_aliases, user1_aliases, limit),
            )
            messages = cur.fetchall()
            cur.close()
            return messages
    except Exception as e:
        log.error("Error getting messages: %s", e)
        return []


def get_direct_messages_for_viewer(viewer_id: str, other_user_id: str, limit: int = 100):
    viewer_canonical = resolve_user_identifier(viewer_id)
    other_canonical = resolve_user_identifier(other_user_id)
    return get_direct_messages(viewer_canonical, other_canonical, limit)


# ---------------------------------------------------------------------------
# Chat requests
# ---------------------------------------------------------------------------

def create_chat_request(request_id: str, user_id: str, psychologist_id: str, message: str = None):
    user_id = resolve_user_identifier(user_id)
    psychologist_id = resolve_user_identifier(psychologist_id)
    return supabase_client.save_chat_request(request_id, user_id, psychologist_id, message or "", "pending")


def get_chat_request(request_id: str):
    try:
        with supabase_client.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM chat_requests WHERE request_id = %s", (request_id,))
            req = cur.fetchone()
            cur.close()
            return dict(req) if req else None
    except Exception as e:
        log.error("Error getting chat request: %s", e)
        return None


def get_pending_requests(psychologist_id: str):
    psychologist_id = resolve_user_identifier(psychologist_id)
    return supabase_client.get_pending_chat_requests(psychologist_id)


def update_chat_request_status(request_id: str, status: str):
    return supabase_client.save_chat_request(request_id, "", "", "", status)


# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------

def _load_json_db():
    """Legacy debug helper — returns empty structure (Supabase is the source of truth)."""
    return {"users": []}
