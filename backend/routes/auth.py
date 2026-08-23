"""
Authentication routes: register, login.
"""

import backend.database.db as db
from flask import Blueprint, request, jsonify
from backend.helpers import hash_password, verify_password, create_token

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password")
    name = data.get("name")
    user_type = data.get("user_type", "user")

    if not email or not password or not name:
        return jsonify({"error": "Missing fields"}), 400

    if user_type not in ("user", "psychologist"):
        return jsonify({"error": "Invalid user type"}), 400

    db.check_connection()

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered"}), 400

    uid = db.create_user(email, hash_password(password), name, user_type)
    if not uid:
        return jsonify({"error": "Registration failed"}), 500

    token = create_token(uid, email, user_type)
    return jsonify({"token": token, "name": name, "user_type": user_type})


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    db.check_connection()

    user = db.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401

    user_type = user.get("user_type", "user")
    token = create_token(user["email"], user["email"], user_type)
    return jsonify({"token": token, "name": user.get("name", "User"), "user_type": user_type})
