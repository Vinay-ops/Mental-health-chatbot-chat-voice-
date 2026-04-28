import os
import sys
import json
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

# Import the new Supabase client
from supabase_client import supabase_client

def _normalize_identifier(identifier: str):
    """Normalize an identifier (email or ID)"""
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

    # Try to resolve ID to email from database
    conn = supabase_client.get_db_connection()
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
            print(f"ERROR: Error resolving identifier: {e}")
    else:
        print("ERROR: Cannot resolve identifier - no Supabase connection")

    
    return normalized.lower()

def get_user_identifier_aliases(identifier: str):
    """Return email/id aliases for a user so old mixed-format rows still match."""
    normalized = _normalize_identifier(identifier)
    if not normalized:
        return []

    aliases = {normalized.lower()}
    canonical = resolve_user_identifier(normalized)
    if canonical:
        aliases.add(canonical.lower())

    conn = supabase_client.get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT id, email FROM users WHERE LOWER(email) = LOWER(%s) OR id::text = %s",
                (canonical or normalized, normalized)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if row:
                if row.get("id") is not None:
                    aliases.add(str(row.get("id")))
                if row.get("email"):
                    aliases.add(str(row.get("email")).lower())
        except Exception as e:
            print(f"ERROR: Error getting identifier aliases: {e}")
            try:
                conn.close()
            except:
                pass

    return list(aliases)

def get_db_connection():
    """Get database connection using Supabase client"""
    return supabase_client.get_db_connection()

def check_connection():
    """Check if connection is available"""
    return supabase_client.check_connection()

def ensure_schema():
    """Ensure database schema exists"""
    return supabase_client.ensure_schema()

def save_log(role: str, content: str, user_id: str = None, session_id: str = None):
    """Save chat log to Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot save log - no Supabase connection")
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
        print(f"ERROR: Error saving log: {e}")
        try:
            conn.close()
        except:
            pass

def get_chat_history(user_id: str, session_id: str):
    """Get chat history from Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get history - no Supabase connection")
        return []
        
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
        history = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: Error getting history: {e}")
        try:
            conn.close()
        except:
            pass
        return []
        
    return history

def get_user_sessions(user_id: str):
    """Get user sessions from Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get sessions - no Supabase connection")
        return []
        
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
        sessions = sorted([row[0] for row in cursor.fetchall()], reverse=True)
        cursor.close()
        conn.close()
        return sessions
    except Exception as e:
        print(f"ERROR: Error getting sessions: {e}")
        try:
            conn.close()
        except:
            pass
        return []

def get_user_by_email(email: str):
    """Get user by email using Supabase client"""
    return supabase_client.get_user_by_email(email)

def create_user(email: str, password_hash: str, name: str, user_type: str = "user"):
    """Create user using Supabase client"""
    return supabase_client.create_user(email, password_hash, name, user_type)

def get_all_psychologists():
    """Get all psychologists using Supabase client"""
    return supabase_client.get_all_psychologists()

def add_community_post(user_id: str, name: str, content: str):
    """Add community post to Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot add post - no Supabase connection")
        return False
        
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
        print(f"ERROR: Error adding post: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def get_community_posts(limit: int = 30):
    """Get community posts from Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get posts - no Supabase connection")
        return []
        
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT id, user_id, name, content, created_at, likes FROM community_posts ORDER BY created_at DESC LIMIT %s",
            (limit,)
        )
        posts = cursor.fetchall()
        cursor.close()
        conn.close()
        return posts
    except Exception as e:
        print(f"ERROR: Error getting posts: {e}")
        try:
            conn.close()
        except:
            pass
        return []

def like_community_post(post_id: int):
    """Like a community post in Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot like post - no Supabase connection")
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
        print(f"ERROR: Error liking post: {e}")
        try:
            conn.close()
        except:
            pass
        return None

# ===== Psychologist-specific functions =====

def connect_psychologist_to_user(psychologist_id: str, user_id: str):
    """Connect a psychologist to a user for direct messaging"""
    psychologist_id = resolve_user_identifier(psychologist_id)
    user_id = resolve_user_identifier(user_id)

    if not psychologist_id or not user_id:
        print("ERROR: Cannot connect - missing psychologist_id or user_id")
        return False

    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot connect - no Supabase connection")
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
        print(f"ERROR: Error connecting: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def get_psychologist_users(psychologist_id: str):
    """Get all users assigned to a psychologist"""
    psychologist_id = resolve_user_identifier(psychologist_id)
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get users - no Supabase connection")
        return []
        
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT pu.user_id, u.name, u.email, pu.created_at as connected_at
            FROM psychologist_users pu
            LEFT JOIN users u ON pu.user_id = u.email
            WHERE pu.psychologist_id = %s AND pu.status = 'active'
            ORDER BY pu.created_at DESC
        """, (psychologist_id,))
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        print(f"ERROR: Error getting users: {e}")
        try:
            conn.close()
        except:
            pass
        return []

def get_accepted_chat_users(psychologist_id: str):
    """Get users who have accepted chat requests with this psychologist"""
    psychologist_id = resolve_user_identifier(psychologist_id)
    psychologist_aliases = get_user_identifier_aliases(psychologist_id)
    """Get accepted chat users from Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get users - no Supabase connection")
        return []
        
    users = []
    user_ids_seen = set()
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Get explicit psychologist-user links.
        cursor.execute("""
            SELECT DISTINCT pu.user_id, u.name, COALESCE(u.email, pu.user_id) AS email, pu.created_at as connected_at
            FROM psychologist_users pu
            LEFT JOIN users u ON pu.user_id = u.email OR pu.user_id = u.id::text
            WHERE pu.psychologist_id = ANY(%s) AND pu.status = 'active'
            ORDER BY pu.created_at DESC
        """, (psychologist_aliases,))
        linked_users = cursor.fetchall()
        for user in linked_users:
            user_id = user.get("email") or user.get("user_id")
            if user_id and user_id not in user_ids_seen:
                user["user_id"] = user_id
                user_ids_seen.add(user_id)
                users.append(user)

        # Get from chat_requests
        cursor.execute("""
            SELECT DISTINCT cr.user_id, u.name, u.email, cr.updated_at as connected_at
            FROM chat_requests cr
            LEFT JOIN users u ON cr.user_id = u.email OR cr.user_id = u.id::text
            WHERE cr.psychologist_id = ANY(%s) AND cr.status = 'accepted'
            ORDER BY cr.updated_at DESC
        """, (psychologist_aliases,))
        chat_users = cursor.fetchall()
        for user in chat_users:
            user_id = user.get("email") or user.get("user_id")
            if user_id and user_id not in user_ids_seen:
                user["user_id"] = user_id
                user_ids_seen.add(user_id)
                users.append(user)
        
        # Get from direct_messages
        cursor.execute("""
            SELECT DISTINCT
                CASE
                    WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id
                    ELSE dm.sender_id
                END AS user_id,
                u.name,
                COALESCE(u.email, CASE
                    WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id
                    ELSE dm.sender_id
                END) AS email,
                MAX(dm.created_at) AS connected_at
            FROM direct_messages dm
            LEFT JOIN users u ON u.email = CASE
                WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id
                ELSE dm.sender_id
            END OR u.id::text = CASE
                WHEN dm.sender_id = ANY(%s) THEN dm.receiver_id
                ELSE dm.sender_id
            END
            WHERE dm.sender_id = ANY(%s) OR dm.receiver_id = ANY(%s)
            GROUP BY user_id, u.name, email
            ORDER BY connected_at DESC
        """, (
            psychologist_aliases,
            psychologist_aliases,
            psychologist_aliases,
            psychologist_aliases,
            psychologist_aliases,
            psychologist_aliases,
        ))
        direct_users = cursor.fetchall()
        for user in direct_users:
            user_id = user.get("email") or user.get("user_id")
            if user_id and user_id not in user_ids_seen:
                user["user_id"] = user_id
                user_ids_seen.add(user_id)
                users.append(user)
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: Error getting accepted users: {e}")
        try:
            cursor.close()
            conn.close()
        except:
            pass
        
    return users

def save_direct_message(sender_id: str, receiver_id: str, message: str):
    """Save a direct message between psychologist and user"""
    sender_id = resolve_user_identifier(sender_id)
    receiver_id = resolve_user_identifier(receiver_id)
    """Save direct message using Supabase client"""
    return supabase_client.save_direct_message(sender_id, receiver_id, message)

def get_direct_messages(user1_id: str, user2_id: str, limit: int = 100):
    """Get direct messages between two users"""
    user1_aliases = get_user_identifier_aliases(user1_id)
    user2_aliases = get_user_identifier_aliases(user2_id)

    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get messages - no Supabase connection")
        return []

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, sender_id, receiver_id, message, is_read, created_at
            FROM direct_messages
            WHERE (sender_id = ANY(%s) AND receiver_id = ANY(%s))
               OR (sender_id = ANY(%s) AND receiver_id = ANY(%s))
            ORDER BY created_at ASC
            LIMIT %s
        """, (user1_aliases, user2_aliases, user2_aliases, user1_aliases, limit))
        messages = cursor.fetchall()
        cursor.close()
        conn.close()

        return messages
    except Exception as e:
        print(f"ERROR: Error getting messages: {e}")
        try:
            conn.close()
        except:
            pass
        return []

def get_direct_messages_for_viewer(viewer_id: str, other_user_id: str, limit: int = 100):
    """
    Get direct messages for a viewer and another user.
    If the viewer is a psychologist, prefer the psychologist id from the accepted
    relationship/request so stale tokens or mixed ids do not hide the chat.
    """
    viewer_canonical = resolve_user_identifier(viewer_id)
    other_canonical = resolve_user_identifier(other_user_id)

    print(f"DEBUG GET_MSGS_VIEWER: viewer_id={viewer_id} -> {viewer_canonical}, other_id={other_user_id} -> {other_canonical}, limit={limit}")

    # First try the direct message table
    messages = get_direct_messages(viewer_canonical, other_canonical, limit)
    if messages:
        print(f"DEBUG GET_MSGS_VIEWER: found {len(messages)} direct messages between {viewer_canonical} and {other_canonical}")
        return messages
    print(f"DEBUG GET_MSGS_VIEWER: no direct messages found for {viewer_canonical} <-> {other_canonical}")

    # Fallback: check accepted chat_requests for an initial message
    conn = get_db_connection()
    if not conn:
        print("DEBUG GET_MSGS_VIEWER: no DB connection for fallback lookup")
        return messages

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        other_aliases = get_user_identifier_aliases(other_canonical)
        viewer_aliases = get_user_identifier_aliases(viewer_canonical)
        print(f"DEBUG GET_MSGS_VIEWER: other_aliases={other_aliases}, viewer_aliases={viewer_aliases}")
        cursor.execute("""
            SELECT request_id, user_id, psychologist_id, message, status, created_at, updated_at
            FROM chat_requests
            WHERE status = 'accepted'
              AND user_id = ANY(%s)
              AND psychologist_id = ANY(%s)
            ORDER BY updated_at DESC
            LIMIT 1
        """, (other_aliases, viewer_aliases))
        row = cursor.fetchone()
        print(f"DEBUG GET_MSGS_VIEWER: chat_request row={row}")
        cursor.close()
        conn.close()
        if row and row.get("message"):
            initial_message = str(row.get("message") or "").strip()
            if initial_message:
                print(f"DEBUG GET_MSGS_VIEWER: returning initial request message for request_id={row.get('request_id')}")
                return [{
                    "id": f"request-{row.get('request_id')}",
                    "sender_id": row.get("user_id") or other_canonical,
                    "receiver_id": row.get("psychologist_id") or viewer_canonical,
                    "message": initial_message,
                    "is_read": False,
                    "created_at": row.get("updated_at") or row.get("created_at")
                }]
    except Exception as e:
        print(f"ERROR: Error resolving chat fallback: {e}")
        try:
            conn.close()
        except:
            pass

    print(f"DEBUG GET_MSGS_VIEWER: fallback found nothing; returning empty list")
    return messages

# ===== Chat Request functions =====

def create_chat_request(request_id: str, user_id: str, psychologist_id: str, message: str = None):
    """Create a chat request from user to psychologist"""
    user_id = resolve_user_identifier(user_id)
    psychologist_id = resolve_user_identifier(psychologist_id)
    """Create chat request using Supabase client"""
    return supabase_client.save_chat_request(request_id, user_id, psychologist_id, message or "", "pending")

def get_chat_request(request_id: str):
    """Get a specific chat request"""
    """Get specific chat request from Supabase"""
    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot get chat request - no Supabase connection")
        return None
        
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM chat_requests WHERE request_id = %s", (request_id,))
        req = cursor.fetchone()
        cursor.close()
        conn.close()
        if req:
            return dict(req)
    except Exception as e:
        print(f"ERROR: Error getting chat request: {e}")
        try:
            conn.close()
        except:
            pass
    
    return None

def get_pending_requests(psychologist_id: str):
    """Get all pending chat requests for a psychologist"""
    """Get pending requests using Supabase client"""
    psychologist_id = resolve_user_identifier(psychologist_id)
    return supabase_client.get_pending_chat_requests(psychologist_id)

def update_chat_request_status(request_id: str, status: str):
    """Update chat request status (accepted, rejected, cancelled)"""
    """Update chat request status using Supabase client"""
    return supabase_client.save_chat_request(request_id, "", "", "", status)

def get_available_psychologists(exclude_user_email=None):
    """Get all psychologists with status - optionally exclude a specific user"""
    """Get available psychologists from Supabase"""
    exclude_user_email = resolve_user_identifier(exclude_user_email) if exclude_user_email else None
    
    psychologists = supabase_client.get_all_psychologists()
    
    # Filter out the excluded user if specified
    if exclude_user_email:
        psychologists = [
            p for p in psychologists 
            if str(p.get("email") or "").lower() != exclude_user_email.lower()
        ]
    
    # Format response
    result = []
    for psych in psychologists:
        result.append({
            "id": psych.get("email", ""),
            "name": psych.get("name", ""),
            "email": psych.get("email", ""),
            "specialization": psych.get("specialization", "General Counseling"),
            "bio": psych.get("bio", "Professional mental health expert"),
            "rating": "4.8",
            "experience": "5",
            "status": psych.get("availability_status") or "available"
        })
    
    return result

def update_psychologist_status(psychologist_id: str, status: str):
    """Update a psychologist's availability status."""
    psychologist_id = resolve_user_identifier(psychologist_id)
    if status not in {"available", "busy", "offline"}:
        print(f"ERROR: Invalid psychologist status: {status}")
        return False

    conn = get_db_connection()
    if not conn:
        print("ERROR: Cannot update psychologist status - no Supabase connection")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET availability_status = %s, updated_at = %s
            WHERE LOWER(email) = LOWER(%s) AND user_type = 'psychologist'
        """, (status, datetime.utcnow(), psychologist_id))
        updated = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        conn.close()
        return updated
    except Exception as e:
        print(f"ERROR: Error updating psychologist status: {e}")
        try:
            conn.close()
        except:
            pass
        return False
