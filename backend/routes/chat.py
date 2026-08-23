"""
Chat routes: AI chat, TTS synthesis, chat history.
"""

import random
import re
import uuid
import base64
from difflib import SequenceMatcher

from flask import Blueprint, request, jsonify
import jwt

import backend.database.db as db
from backend.config import JWT_SECRET, JWT_ALGORITHM, MAX_HISTORY_MESSAGES, MAX_SESSION_MEMORY
from backend.helpers import token_required, enforce_short_reply
from backend.ai.providers import (
    SAFE_SYSTEM_PROMPT, generate_reply,
)

chat_bp = Blueprint("chat", __name__)

# In-memory session stores (swap for Redis in production)
_session_memory: dict[str, list[tuple[str, str]]] = {}
_session_sentiment: dict[str, str] = {}

# TTS service (lazy init)
_tts_service = None


def _get_tts_service():
    global _tts_service
    if _tts_service is None:
        try:
            from backend.services.tts import EmotionalTTSService
            _tts_service = EmotionalTTSService(method="fish")
        except Exception as e:
            print(f"Warning: TTS Service init failed: {e}")

            class _DummyTTS:
                def synthesize(self, *a, **kw):
                    return False, str(e), None

            _tts_service = _DummyTTS()
    return _tts_service


# ---------------------------------------------------------------------------
# Helper: anti-repeat
# ---------------------------------------------------------------------------

def _recent_assistant_snippets(session_id: str, max_items: int = 3) -> list[str]:
    msgs = _session_memory.get(session_id, [])
    snippets = []
    for role, content in reversed(msgs):
        if role == "Assistant" and content:
            snippets.append(str(content).strip())
        if len(snippets) >= max_items:
            break
    return list(reversed(snippets))


def _is_similar_to_recent(session_id: str, reply: str) -> bool:
    if not reply or session_id not in _session_memory:
        return False
    reply_key = " ".join(reply.lower().split())
    recent = []
    for role, content in reversed(_session_memory[session_id]):
        if role == "Assistant":
            recent.append(" ".join(str(content).lower().split()))
        if len(recent) >= 3:
            break
    for prev in recent:
        if reply_key == prev:
            return True
        if SequenceMatcher(None, reply_key, prev).ratio() >= 0.86:
            return True
    return False


def _build_quality_prompt_addon(session_id: str) -> str:
    recent = _recent_assistant_snippets(session_id)
    base = (
        "\nREPLY QUALITY FORMAT:\n"
        "- Use 3 short parts: (1) validate emotion, (2) one practical next step, (3) one gentle follow-up question.\n"
        "- Keep reply under 5 lines and avoid filler.\n"
    )
    if not recent:
        return base
    joined = "\n".join(f"- {r}" for r in recent)
    return (
        + base
        + "- Do NOT reuse the same wording, openings, or sentence patterns from these recent assistant replies:\n"
        + joined + "\n"
        + "- Write a fresh, meaningfully different response.\n"
    )


def _randomize_system_prompt(prompt: str) -> str:
    instructions = [
        "Vary your response structure from your previous responses. ",
        "Use a slightly different tone—be more conversational. ",
        "Add a relevant question or follow-up suggestion. ",
        "Keep your response concise but warm. ",
        "Be more curious and ask about context. ",
    ]
    if random.random() > 0.3:
        prompt += f"\n{random.choice(instructions)}"
    return prompt


def _parse_mood_and_reply(raw: str) -> tuple[str, str]:
    """Extract [MOOD: x] tag and return (sentiment, clean_reply)."""
    sentiment = "neutral"
    reply = raw
    if "[MOOD:" in raw:
        try:
            parts = raw.split("]", 1)
            mood = parts[0].replace("[MOOD:", "").strip().lower()
            if mood in ("happy", "sad", "anxious", "angry", "calm", "neutral"):
                sentiment = mood
            reply = parts[1].strip()
        except Exception:
            pass
    return sentiment, reply


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@chat_bp.route("/api/chat", methods=["POST"])
def chat_api():
    data = request.json
    message = data.get("message", "")
    provider = data.get("provider")
    lang = data.get("lang", "en")
    session_id = data.get("session_id") or request.remote_addr

    # Optionally extract user from token
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            decoded = jwt.decode(auth_header.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = decoded["sub"]
        except Exception:
            pass

    # Load session memory from DB on first message
    if session_id not in _session_memory:
        _session_memory[session_id] = []
        for h in db.get_chat_history(user_id, session_id):
            role_name = "User" if h["role"] == "user" else "Assistant"
            _session_memory[session_id].append((role_name, h["content"]))

    history = _session_memory[session_id][-MAX_HISTORY_MESSAGES:]
    history_context = "\n".join(f"{role}: {content}" for role, content in history)

    # Language instruction
    lang_map = {
        "hi": " Respond strictly in HINDI (हिन्दी) language.",
        "mr": " Respond strictly in MARATHI (मराठी) language.",
    }
    lang_instruction = lang_map.get(lang, f" Respond in {lang.upper()} language.")

    system_prompt = (
        SAFE_SYSTEM_PROMPT + lang_instruction
        + "\nIMPORTANT: Your response MUST start with the detected sentiment of the user's message in this exact format: "
        "[MOOD: sentiment_name] followed by your actual response. "
        "Choose sentiment_name from: [happy, sad, anxious, angry, calm, neutral]. "
        "Example: '[MOOD: calm] I am glad you are feeling peaceful...'"
    )
    system_prompt += _build_quality_prompt_addon(session_id)
    system_prompt = _randomize_system_prompt(system_prompt)

    full_prompt = (
        f"Recent History:\n{history_context}\n\nUser: {message}"
        if history_context
        else message
    )

    if not provider:
        from backend.config import get_default_provider
        provider = get_default_provider()

    # Save user message
    try:
        db.save_log("user", message, user_id=user_id, session_id=session_id)
    except Exception:
        pass

    raw_reply = generate_reply(provider, full_prompt, system_prompt)
    sentiment, reply = _parse_mood_and_reply(raw_reply)
    reply = enforce_short_reply(reply)

    # Anti-repeat retry
    if _is_similar_to_recent(session_id, reply):
        retry_prompt = (
            system_prompt
            + "\nRETRY INSTRUCTION: Your previous candidate was too similar to recent replies. "
              "Use a new structure, new phrasing, and different coping suggestion."
        )
        retry_raw = generate_reply(provider, full_prompt, retry_prompt)
        retry_sentiment, retry_reply = _parse_mood_and_reply(retry_raw)
        retry_reply = enforce_short_reply(retry_reply)
        if not _is_similar_to_recent(session_id, retry_reply):
            reply = retry_reply
            sentiment = retry_sentiment
        else:
            reply = enforce_short_reply(_local_fallback(message))

    _session_sentiment[session_id] = sentiment

    # Update memory
    _session_memory[session_id].append(("User", message))
    _session_memory[session_id].append(("Assistant", reply))
    if len(_session_memory[session_id]) > MAX_SESSION_MEMORY:
        _session_memory[session_id] = _session_memory[session_id][-MAX_SESSION_MEMORY:]

    # Save assistant reply
    try:
        db.save_log("assistant", reply, user_id=user_id, session_id=session_id)
    except Exception:
        pass

    return jsonify({"reply": reply, "sentiment": sentiment, "session_id": session_id})


@chat_bp.route("/api/synthesize", methods=["POST"])
@token_required
def synthesize_audio(user_id, email):
    tts = _get_tts_service()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "").strip()
        emotion = data.get("emotion", "empathetic").lower()

        if not text:
            return jsonify({"error": "Text is required"}), 400

        valid_emotions = ("empathetic", "calm", "encouraging", "supportive", "neutral")
        if emotion not in valid_emotions:
            emotion = "empathetic"

        success, message, audio_bytes = tts.synthesize(text=text, emotion=emotion, output_path=None)

        if not success:
            return jsonify({"error": f"Voice synthesis failed. {message}", "success": False}), 500

        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            return jsonify({
                "success": True,
                "audio": audio_b64,
                "audio_format": "audio/mpeg",
                "emotion": emotion,
            })

        return jsonify({"error": "No audio data received", "success": False}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}", "success": False}), 500


@chat_bp.route("/api/history/<session_id>", methods=["GET"])
@token_required
def get_history(user_id, email, session_id):
    history = db.get_chat_history(user_id, session_id)
    from datetime import datetime
    for h in history:
        if isinstance(h.get("ts"), datetime):
            h["ts"] = h["ts"].isoformat()
        if "_id" in h:
            h["_id"] = str(h["_id"])
    return jsonify(history)


@chat_bp.route("/api/sessions", methods=["GET"])
@token_required
def get_sessions(user_id, email):
    return jsonify(db.get_user_sessions(user_id))


@chat_bp.route("/api/new_chat", methods=["POST"])
def new_chat():
    return jsonify({"session_id": str(uuid.uuid4())})


# Local fallback helper (kept here as it's chat-specific)
def _local_fallback(message: str) -> str:
    return (
        "I hear you. Could you share a bit more about what you're experiencing? "
        "I'm here to listen."
    )
