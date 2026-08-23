"""
Database package — re-exports all public functions from db.py
so callers can do: from backend.database import db
"""

from backend.database.db import (
    get_db_connection,
    check_connection,
    ensure_schema,
    resolve_user_identifier,
    get_user_identifier_aliases,
    get_user_by_email,
    create_user,
    get_all_psychologists,
    get_available_psychologists,
    update_psychologist_status,
    save_log,
    get_chat_history,
    get_user_sessions,
    add_community_post,
    get_community_posts,
    like_community_post,
    connect_psychologist_to_user,
    get_psychologist_users,
    get_accepted_chat_users,
    save_direct_message,
    get_direct_messages,
    get_direct_messages_for_viewer,
    create_chat_request,
    get_chat_request,
    get_pending_requests,
    update_chat_request_status,
)
