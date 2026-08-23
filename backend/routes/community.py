"""
Community routes: posts, likes.
"""

from datetime import datetime

from flask import Blueprint, request, jsonify

import backend.database.db as db
from backend.helpers import extract_user_from_request

community_bp = Blueprint("community", __name__)


@community_bp.route("/api/community/posts", methods=["GET", "POST"])
def community_posts_api():
    if request.method == "POST":
        data = request.json or {}
        content = (data.get("content") or "").strip()
        name = (data.get("name") or "Anonymous").strip() or "Anonymous"

        if not content:
            return jsonify({"error": "Message is required"}), 400

        user_id, _ = extract_user_from_request(request)
        ok = db.add_community_post(user_id, name, content)
        if not ok:
            return jsonify({"error": "Could not save message"}), 500
        return jsonify({"success": True})

    # GET
    posts = db.get_community_posts()
    normalized = []
    for p in posts:
        created = p.get("created_at")
        created_str = created.isoformat() if isinstance(created, datetime) else str(created or "")
        normalized.append({
            "id": p.get("id"),
            "name": p.get("name") or "Anonymous",
            "content": p.get("content"),
            "created_at": created_str,
            "likes": p.get("likes", 0),
        })
    return jsonify(normalized)


@community_bp.route("/api/community/posts/<int:post_id>/like", methods=["POST"])
def community_like_post(post_id: int):
    likes = db.like_community_post(post_id)
    if likes is None:
        return jsonify({"error": "Could not like post"}), 400
    return jsonify({"likes": likes})
