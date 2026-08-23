"""
Psychologist feature routes: chat requests, messaging, user listing, status.
"""

import logging
import uuid
import re
import requests as http_requests
from difflib import SequenceMatcher

from flask import Blueprint, request, jsonify

import backend.database.db as db
from backend.helpers import token_required, normalize_location_text

log = logging.getLogger(__name__)
psychologist_bp = Blueprint("psychologist", __name__)


# ---------------------------------------------------------------------------
# Psychologist data for the locator
# ---------------------------------------------------------------------------

NEAREST_PSYCHOLOGISTS = {
    "mumbai": [
        {"name": "Dr. A. Sharma, Clinical Psychologist", "address": "Andheri West, Mumbai", "phone": "+91-98765-00001"},
        {"name": "MindCare Clinic Mumbai", "address": "Bandra East, Mumbai", "phone": "+91-98765-00002"},
        {"name": "Dr. Sneha Patil, Psychotherapist", "address": "Colaba, Mumbai", "phone": "+91-98765-00021"},
    ],
    "pune": [
        {"name": "Dr. R. Kulkarni, Counseling Psychologist", "address": "Kothrud, Pune", "phone": "+91-98765-00003"},
        {"name": "Hope Mental Wellness Center", "address": "Viman Nagar, Pune", "phone": "+91-98765-00004"},
        {"name": "Dr. Anjali Deshmukh, Child Psychologist", "address": "Hinjewadi, Pune", "phone": "+91-98765-00022"},
    ],
    "delhi": [
        {"name": "Dr. S. Verma, Psychotherapist", "address": "South Extension, New Delhi", "phone": "+91-98765-00005"},
        {"name": "Calm Mind Clinic", "address": "Dwarka, New Delhi", "phone": "+91-98765-00006"},
        {"name": "Dr. Rahul Mehra, Clinical Psychologist", "address": "Connaught Place, New Delhi", "phone": "+91-98765-00023"},
    ],
    "bengaluru": [
        {"name": "Serene Minds Center", "address": "Indiranagar, Bengaluru", "phone": "+91-98765-00007"},
        {"name": "Dr. K. Rao, Clinical Psychologist", "address": "Koramangala, Bengaluru", "phone": "+91-98765-00008"},
        {"name": "Dr. Priya Sundaram, Counselor", "address": "HSR Layout, Bengaluru", "phone": "+91-98765-00024"},
    ],
    "bangalore": [
        {"name": "Serene Minds Center", "address": "Indiranagar, Bengaluru", "phone": "+91-98765-00007"},
        {"name": "Dr. K. Rao, Clinical Psychologist", "address": "Koramangala, Bengaluru", "phone": "+91-98765-00008"},
        {"name": "Dr. Priya Sundaram, Counselor", "address": "HSR Layout, Bengaluru", "phone": "+91-98765-00024"},
    ],
    "chennai": [
        {"name": "Calm Waves Wellness", "address": "T. Nagar, Chennai", "phone": "+91-98765-00009"},
        {"name": "Dr. L. Iyer, Counseling Psychologist", "address": "Anna Nagar, Chennai", "phone": "+91-98765-00010"},
        {"name": "Dr. Meena Swamy, Psychotherapist", "address": "Adyar, Chennai", "phone": "+91-98765-00025"},
    ],
    "hyderabad": [
        {"name": "HopeCare Psychological Services", "address": "Banjara Hills, Hyderabad", "phone": "+91-98765-00011"},
        {"name": "Mindful Living Clinic", "address": "Gachibowli, Hyderabad", "phone": "+91-98765-00012"},
        {"name": "Dr. Sameer Khan, Psychiatrist", "address": "Jubilee Hills, Hyderabad", "phone": "+91-98765-00026"},
    ],
    "kolkata": [
        {"name": "Dr. P. Mukherjee, Psychologist", "address": "Salt Lake, Kolkata", "phone": "+91-98765-00013"},
        {"name": "Harmony Mental Wellness", "address": "Park Street, Kolkata", "phone": "+91-98765-00014"},
        {"name": "Dr. Amitava Ghosh, Counselor", "address": "Ballygunge, Kolkata", "phone": "+91-98765-00027"},
    ],
    "ahmedabad": [
        {"name": "Dr. Jatin Shah, Psychologist", "address": "Satellite, Ahmedabad", "phone": "+91-98765-00015"},
        {"name": "Aura Wellness Clinic", "address": "Navrangpura, Ahmedabad", "phone": "+91-98765-00016"},
    ],
    "jaipur": [
        {"name": "Dr. Neha Goyal, Counselor", "address": "Malviya Nagar, Jaipur", "phone": "+91-98765-00017"},
        {"name": "Pink City Mental Health", "address": "Vaishali Nagar, Jaipur", "phone": "+91-98765-00018"},
    ],
    "lucknow": [
        {"name": "Dr. Manish Tiwari, Psychiatrist", "address": "Gomti Nagar, Lucknow", "phone": "+91-98765-00019"},
        {"name": "MindSpace Lucknow", "address": "Hazratganj, Lucknow", "phone": "+91-98765-00020"},
    ],
}

CITY_ALIASES = {
    "new delhi": "delhi",
    "ncr": "delhi",
    "delhi ncr": "delhi",
    "gurgaon": "delhi",
    "gurugram": "delhi",
    "noida": "delhi",
    "ghaziabad": "delhi",
    "thane": "mumbai",
    "navi mumbai": "mumbai",
    "bombay": "mumbai",
    "blr": "bengaluru",
    "bengalooru": "bengaluru",
    "bangaluru": "bengaluru",
    "madras": "chennai",
    "calcutta": "kolkata",
    "hyd": "hyderabad",
    "ahmedbad": "ahmedabad",
    "lko": "lucknow",
}


def _resolve_supported_city(location_raw: str):
    location = normalize_location_text(location_raw)
    if not location:
        return None, 0.0

    for city_key in NEAREST_PSYCHOLOGISTS:
        if location == city_key or city_key in location:
            return city_key, 1.0

    for alias, mapped_city in CITY_ALIASES.items():
        if location == alias or alias in location:
            return mapped_city, 0.95

    tokens = [t for t in re.split(r"[,\s]+", location) if t]
    token_set = set(tokens)
    for city_key in NEAREST_PSYCHOLOGISTS:
        if set(city_key.split()).issubset(token_set):
            return city_key, 0.9

    for alias, mapped_city in CITY_ALIASES.items():
        if set(alias.split()).issubset(token_set):
            return mapped_city, 0.88

    best_city, best_score = None, 0.0
    candidates = list(NEAREST_PSYCHOLOGISTS) + list(CITY_ALIASES)
    for token in tokens:
        for candidate in candidates:
            score = SequenceMatcher(None, token, candidate).ratio()
            if score > best_score:
                best_score = score
                best_city = CITY_ALIASES.get(candidate, candidate)

    if best_city and best_score >= 0.72:
        return best_city, best_score

    return None, 0.0


def _fetch_live_psychologists(location_query: str, limit: int = 8) -> list:
    cleaned = (location_query or "").strip()
    if not cleaned:
        return []

    try:
        headers = {"User-Agent": "MindCareNavigator/1.0 (mental health support app)"}
        params = {
            "q": f"psychologist near {cleaned}",
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": max(1, min(int(limit), 12)),
        }
        resp = http_requests.get(
            "https://nominatim.openstreetmap.org/search",
            headers=headers, params=params, timeout=12,
        )
        if not resp.ok:
            return []

        include_terms = (
            "psychologist", "psychology", "psychotherapist", "therapy",
            "therapist", "counselor", "counsellor", "mental health",
            "psychiatrist", "psychiatry",
        )
        exclude_terms = (
            "dentist", "cardio", "cardiolog", "orthopedic", "orthopaedic",
            "neurolog", "pediatric", "paediatric", "dermatolog", "ent ",
            "ophthalm", "eye hospital", "general hospital", "multispecial",
            "physician", "surgeon", "gynaec", "gynec", "urolog", "oncolog",
        )

        results = []
        for item in resp.json():
            display_name = (item.get("display_name") or "").strip()
            if not display_name:
                continue

            title = (item.get("name") or "").strip() or display_name.split(",")[0].strip()
            searchable = f"{title} {display_name}".lower()
            if not any(t in searchable for t in include_terms):
                continue
            if any(t in searchable for t in exclude_terms):
                continue

            lat, lon = item.get("lat"), item.get("lon")
            map_url = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else None
            results.append({
                "name": title,
                "address": display_name,
                "phone": "Not listed publicly",
                "source": "OpenStreetMap",
                "map_url": map_url,
            })

        return results[:limit]
    except Exception as e:
        log.debug("Live psychologist lookup failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@psychologist_bp.route("/api/psychologists", methods=["POST"])
def psychologists_api():
    data = request.json or {}
    location_raw = data.get("location") or ""
    if not str(location_raw).strip():
        return jsonify({"error": "Location is required"}), 400

    results = _fetch_live_psychologists(location_raw, limit=8)
    if not results:
        return jsonify({
            "results": [],
            "message": "I could not find live psychologist listings for this location right now. "
                       "Please try nearby area names or check Google Maps results shown on the right.",
        })
    return jsonify({"results": results, "source": "live"})


@psychologist_bp.route("/api/psychologist/users", methods=["GET"])
@token_required
def get_psychologist_users(current_user_id, current_user_email):
    db.check_connection()
    user = db.get_user_by_email(current_user_email)
    if not user:
        return jsonify({"error": "User not found"}), 403
    if user.get("user_type") != "psychologist":
        return jsonify({"error": "Unauthorized - not a psychologist"}), 403

    users = db.get_accepted_chat_users(current_user_email)
    return jsonify({"users": users})


@psychologist_bp.route("/api/psychologist/connect", methods=["POST"])
@token_required
def connect_psychologist(current_user_id, current_user_email):
    data = request.json
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    db.check_connection()
    user = db.get_user_by_email(current_user_email)
    if not user or user.get("user_type") != "psychologist":
        return jsonify({"error": "Unauthorized"}), 403

    success = db.connect_psychologist_to_user(current_user_email, user_id)
    if success:
        return jsonify({"success": True, "message": "Connected to user"})
    return jsonify({"error": "Failed to connect"}), 500


@psychologist_bp.route("/api/psychologist/status", methods=["GET", "POST"])
@token_required
def psychologist_status(current_user_id, current_user_email):
    db.check_connection()
    user = db.get_user_by_email(current_user_email)
    if not user or user.get("user_type") != "psychologist":
        return jsonify({"error": "Unauthorized"}), 403

    if request.method == "GET":
        return jsonify({"status": user.get("availability_status") or "available"})

    data = request.json or {}
    status = data.get("status")
    if status not in {"available", "busy", "offline"}:
        return jsonify({"error": "Invalid status"}), 400

    if not db.update_psychologist_status(current_user_email, status):
        return jsonify({"error": "Failed to update status"}), 500

    return jsonify({"success": True, "status": status})


@psychologist_bp.route("/api/psychologists/available", methods=["GET"])
@token_required
def get_available_psychologists(current_user_id, current_user_email):
    try:
        db.check_connection()
        psychologists = db.get_available_psychologists(exclude_user_email=current_user_email)
        return jsonify({"psychologists": psychologists})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Direct messaging
# ---------------------------------------------------------------------------

@psychologist_bp.route("/api/messages/send", methods=["POST"])
@token_required
def send_direct_message(current_user_id, current_user_email):
    data = request.json
    receiver_id = data.get("receiver_id")
    message_text = data.get("message")

    if not receiver_id or not message_text:
        return jsonify({"error": "Missing fields"}), 400

    db.check_connection()
    success = db.save_direct_message(current_user_email, receiver_id, message_text)
    if success:
        return jsonify({"success": True, "message": "Message sent"})
    return jsonify({"error": "Failed to send message"}), 500


@psychologist_bp.route("/api/messages/<other_user_id>", methods=["GET"])
@token_required
def get_direct_messages(current_user_id, current_user_email, other_user_id):
    db.check_connection()
    limit = request.args.get("limit", 100, type=int)
    messages = db.get_direct_messages_for_viewer(current_user_email, other_user_id, limit)
    return jsonify({"messages": messages})


# ---------------------------------------------------------------------------
# Chat requests
# ---------------------------------------------------------------------------

@psychologist_bp.route("/api/chat-request/send", methods=["POST"])
@token_required
def send_chat_request(current_user_id, current_user_email):
    db.check_connection()
    data = request.json or {}
    psychologist_id = db.resolve_user_identifier(data.get("psychologist_id"))
    message = data.get("message", "")

    if not psychologist_id:
        return jsonify({"error": "psychologist_id required"}), 400

    psychologist = db.get_user_by_email(psychologist_id)
    if psychologist and (psychologist.get("availability_status") or "available") == "offline":
        return jsonify({"error": "This psychologist is currently offline"}), 409

    request_id = str(uuid.uuid4())
    result = db.create_chat_request(request_id, current_user_email, psychologist_id, message)
    return jsonify({"success": True, "request_id": request_id})


@psychologist_bp.route("/api/chat-request/<request_id>/status", methods=["GET"])
@token_required
def get_chat_request_status(current_user_id, current_user_email, request_id):
    db.check_connection()
    chat_request = db.get_chat_request(request_id)
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404
    return jsonify({
        "request_id": chat_request.get("request_id"),
        "status": chat_request.get("status"),
        "psychologist_id": chat_request.get("psychologist_id"),
        "user_id": chat_request.get("user_id"),
    })


@psychologist_bp.route("/api/chat-request/<request_id>/accept", methods=["POST"])
@token_required
def accept_chat_request(current_user_id, current_user_email, request_id):
    db.check_connection()
    chat_request = db.get_chat_request(request_id)
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404

    request_psychologist_id = db.resolve_user_identifier(chat_request.get("psychologist_id"))
    current_ids = [
        db.resolve_user_identifier(current_user_email),
        db.resolve_user_identifier(current_user_id),
    ]
    if request_psychologist_id not in current_ids:
        return jsonify({"error": "Unauthorized"}), 403

    if not db.update_chat_request_status(request_id, "accepted"):
        return jsonify({"error": "Failed to accept request"}), 500

    connected = db.connect_psychologist_to_user(
        request_psychologist_id, chat_request.get("user_id"),
    )
    if not connected:
        return jsonify({"error": "Request accepted, but failed to record psychologist user"}), 500

    initial_message = (chat_request.get("message") or "").strip()
    if initial_message:
        db.save_direct_message(chat_request.get("user_id"), request_psychologist_id, initial_message)

    return jsonify({"success": True, "message": "Chat request accepted"})


@psychologist_bp.route("/api/chat-request/<request_id>/reject", methods=["POST"])
@token_required
def reject_chat_request(current_user_id, current_user_email, request_id):
    db.check_connection()
    chat_request = db.get_chat_request(request_id)
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404

    request_psychologist_id = db.resolve_user_identifier(chat_request.get("psychologist_id"))
    if request_psychologist_id not in [
        db.resolve_user_identifier(current_user_id),
        db.resolve_user_identifier(current_user_email),
    ]:
        return jsonify({"error": "Unauthorized"}), 403

    db.update_chat_request_status(request_id, "rejected")
    return jsonify({"success": True, "message": "Chat request rejected"})


@psychologist_bp.route("/api/chat-request/<request_id>/cancel", methods=["POST"])
@token_required
def cancel_chat_request(current_user_id, current_user_email, request_id):
    db.check_connection()
    chat_request = db.get_chat_request(request_id)
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404

    request_user_id = db.resolve_user_identifier(chat_request.get("user_id"))
    if request_user_id not in [
        db.resolve_user_identifier(current_user_id),
        db.resolve_user_identifier(current_user_email),
    ]:
        return jsonify({"error": "Unauthorized"}), 403

    db.update_chat_request_status(request_id, "cancelled")
    return jsonify({"success": True, "message": "Chat request cancelled"})


@psychologist_bp.route("/api/psychologist/<psychologist_id>/pending-requests", methods=["GET"])
@token_required
def get_pending_requests(current_user_id, current_user_email, psychologist_id):
    db.check_connection()
    authenticated_psychologist_id = db.resolve_user_identifier(current_user_email)

    user = db.get_user_by_email(authenticated_psychologist_id)
    if not user or user.get("user_type") != "psychologist":
        return jsonify({"error": "Unauthorized - not a psychologist"}), 403

    requests_list = db.get_pending_requests(authenticated_psychologist_id)
    return jsonify({"requests": requests_list})


# ---------------------------------------------------------------------------
# Debug endpoints (no auth required)
# ---------------------------------------------------------------------------

@psychologist_bp.route("/api/debug/users", methods=["GET"])
def debug_users():
    try:
        data = db._load_json_db() if hasattr(db, "_load_json_db") else {"users": []}
        users = data.get("users", [])
        return jsonify({"debug": "Users loaded", "users": users, "total": len(users)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@psychologist_bp.route("/api/debug/psychologists", methods=["GET"])
def debug_psychologists():
    try:
        psychologists = db.get_available_psychologists()
        return jsonify({"psychologists": psychologists, "count": len(psychologists)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
