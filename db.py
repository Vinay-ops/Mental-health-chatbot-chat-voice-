import os
import sys
import json
from pymongo import MongoClient
from datetime import datetime

# MongoDB Connection Setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
MONGO_DB = os.getenv("MONGO_DB", "mindcare_db")

# Fallback JSON File
JSON_DB_FILE = "local_db.json"

_client = None
_use_json_fallback = False

def _load_json_db():
    if not os.path.exists(JSON_DB_FILE):
        return {"users": [], "chat_logs": []}
    try:
        with open(JSON_DB_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"users": [], "chat_logs": []}

def _save_json_db(data):
    try:
        with open(JSON_DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"DEBUG: Error saving JSON DB: {e}")

def get_client():
    global _client, _use_json_fallback
    if _client is None and not _use_json_fallback:
        try:
            _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
            # Test connection immediately
            _client.admin.command('ping')
            print("DEBUG: Connected to MongoDB successfully.")
        except Exception:
            print("DEBUG: MongoDB not found. Switching to Local JSON Fallback.")
            _use_json_fallback = True
            _client = None
    return _client

def check_connection():
    # If we are using JSON fallback, we are "connected" to our local file
    if _use_json_fallback:
        return True
    client = get_client()
    if not client:
        return _use_json_fallback # True if fallback is active
    try:
        client.admin.command('ping')
        return True
    except Exception:
        return False

def ensure_schema():
    if _use_json_fallback:
        return
    client = get_client()
    if not client: return
    try:
        db = client[MONGO_DB]
        db.users.create_index("email", unique=True)
        db.chat_logs.create_index([("user_id", 1), ("session_id", 1), ("ts", 1)])
    except Exception:
        pass

def save_log(role: str, content: str, user_id: str = None, session_id: str = None):
    if _use_json_fallback:
        data = _load_json_db()
        data["chat_logs"].append({
            "role": role,
            "content": content,
            "user_id": user_id,
            "session_id": session_id,
            "ts": datetime.utcnow().isoformat()
        })
        _save_json_db(data)
        return

    client = get_client()
    if not client: return
    try:
        db = client[MONGO_DB]
        log_entry = {
            "role": role, 
            "content": content, 
            "user_id": user_id,
            "session_id": session_id,
            "ts": datetime.utcnow()
        }
        db.chat_logs.insert_one(log_entry)
    except Exception:
        pass

def get_chat_history(user_id: str, session_id: str):
    if _use_json_fallback:
        data = _load_json_db()
        return [log for log in data["chat_logs"] 
                if log.get("user_id") == user_id and log.get("session_id") == session_id]

    client = get_client()
    if not client: return []
    try:
        db = client[MONGO_DB]
        return list(db.chat_logs.find({"user_id": user_id, "session_id": session_id}).sort("ts", 1))
    except Exception:
        return []

def get_user_sessions(user_id: str):
    if _use_json_fallback:
        data = _load_json_db()
        sessions = set()
        for log in data["chat_logs"]:
            if log.get("user_id") == user_id and log.get("session_id"):
                sessions.add(log["session_id"])
        return sorted(list(sessions), reverse=True)

    client = get_client()
    if not client: return []
    try:
        db = client[MONGO_DB]
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$session_id", "last_ts": {"$max": "$ts"}}},
            {"$sort": {"last_ts": -1}}
        ]
        results = list(db.chat_logs.aggregate(pipeline))
        return [res["_id"] for res in results if res["_id"]]
    except Exception:
        return []

def get_user_by_email(email: str):
    if _use_json_fallback:
        data = _load_json_db()
        for user in data["users"]:
            if user["email"] == email:
                # Add mock _id for JWT consistency
                user["_id"] = user.get("email")
                return user
        return None

    client = get_client()
    if not client: return None
    try:
        db = client[MONGO_DB]
        return db.users.find_one({"email": email})
    except Exception:
        return None

def create_user(email: str, password_hash: str, name: str):
    if _use_json_fallback:
        data = _load_json_db()
        if any(u["email"] == email for u in data["users"]):
            return None
        new_user = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.utcnow().isoformat()
        }
        data["users"].append(new_user)
        _save_json_db(data)
        return email

    client = get_client()
    if not client: return None
    try:
        db = client[MONGO_DB]
        user_data = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.utcnow()
        }
        result = db.users.insert_one(user_data)
        return str(result.inserted_id)
    except Exception:
        return None
