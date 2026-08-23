"""
MindCare Navigator - Helper Utilities
Password hashing, JWT tokens, text processing.
"""

import re
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from functools import wraps

import jwt
from passlib.context import CryptContext

from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_MINUTES

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

def create_token(user_id: str, email: str, user_type: str = "user") -> str:
    """Create a signed JWT token."""
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_type": user_type,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRY_MINUTES),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def extract_user_from_request(request) -> tuple:
    """
    Extract user_id and email from the Authorization header.
    Returns (user_id, email) or (None, None) if not authenticated.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None
    try:
        token = auth_header.split(" ", 1)[1]
        data = decode_token(token)
        return data.get("sub"), data.get("email")
    except Exception:
        return None, None


def token_required(f):
    """Decorator that enforces JWT authentication on a route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request, jsonify

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token is missing"}), 401

        try:
            token = auth_header.split(" ", 1)[1]
            data = decode_token(token)
            user_id = data["sub"]
            user_email = data["email"]
        except Exception:
            return jsonify({"error": "Token is invalid"}), 401

        return f(user_id, user_email, *args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------

def enforce_short_reply(text: str, max_lines: int = 5, max_words: int = 90) -> str:
    """Keep final assistant reply concise and readable."""
    if not text:
        return text

    normalized = " ".join(str(text).split())
    words = normalized.split()
    if len(words) > max_words:
        normalized = " ".join(words[:max_words]).rstrip(" ,;:-")
        if not normalized.endswith((".", "!", "?")):
            normalized += "."

    target_words_per_line = 18
    line_words = normalized.split()
    lines = []
    current = []
    for w in line_words:
        current.append(w)
        if len(current) >= target_words_per_line:
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))

    return "\n".join(lines[:max_lines]).strip()


def normalize_location_text(text: str) -> str:
    """Normalize a location string for comparison."""
    cleaned = (text or "").strip().lower()
    cleaned = re.sub(r"[^a-z\s,]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()
