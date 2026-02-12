import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import requests
import google.generativeai as genai
from passlib.context import CryptContext
import jwt
import db

app = Flask(__name__)

# --- Configuration ---
SAFE_SYSTEM_PROMPT = (
    "You are MindCare Navigator, a supportive, non-diagnostic assistant. "
    "Provide empathetic, grounded guidance for emotional support, stress relief, and resource navigation. "
    "Do not provide medical diagnoses or therapy. Encourage professional help when needed and share "
    "region-agnostic, general resources. Keep responses short, kind, and actionable."
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")
JWT_ALGO = "HS256"
JWT_EXP_MIN = int(os.getenv("JWT_EXP_MIN", "120"))

# --- Helper Functions ---

def _hash_password(p: str) -> str:
    return pwd_context.hash(p)

def _verify_password(p: str, h: str) -> bool:
    try:
        return pwd_context.verify(p, h)
    except Exception:
        return False

def _make_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def _fallback_response(message: str) -> str:
    m = message.lower()
    if any(word in m for word in ["hello", "hi", "hey"]):
        return "Hello! I’m here to support you. How are you feeling today?"
    if any(word in m for word in ["stress", "stressed", "overwhelmed"]):
        return "I’m sorry you’re feeling stressed. Want to try a simple 4-7-8 breathing exercise together?"
    if "resources" in m or "help" in m or "support" in m:
        return "I can help explore support options. Are you looking for local helplines, clinics, or online groups?"
    if "breathing" in m:
        return "Let’s try the 4-7-8 technique: inhale 4s, hold 7s, exhale 8s. Shall we start?"
    return "I hear you. Could you share a bit more? I’m here to listen and help you navigate options."

def _gemini_reply(message: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            [{"role": "user", "parts": [SAFE_SYSTEM_PROMPT]}, {"role": "user", "parts": [message]}]
        )
        return (getattr(resp, "text", None) or "").strip() or None
    except Exception:
        return None

def _grok_reply(message: str) -> str:
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        return None
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-2",
            "messages": [
                {"role": "system", "content": SAFE_SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "temperature": 0.4,
        }
        r = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers, timeout=30)
        j = r.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content", None)
    except Exception:
        return None

def _ollama_reply(message: str) -> str:
    try:
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        payload = {
            "model": model,
            "prompt": f"{SAFE_SYSTEM_PROMPT}\nUser: {message}\nAssistant:",
            "stream": False,
        }
        r = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=30)
        j = r.json()
        resp = j.get("response", "")
        return resp.strip() or None
    except Exception:
        return None

# --- Routes ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/chat')
def chat_page():
    return render_template('chat.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- API Endpoints ---

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    message = data.get('message', '')
    provider = data.get('provider')
    
    if not provider:
        provider = "gemini" if os.getenv("GEMINI_API_KEY") else ("grok" if os.getenv("XAI_API_KEY") else "ollama")
    
    try:
        db.ensure_schema()
        db.save_log("user", message)
    except Exception:
        pass
        
    reply = None
    if provider == "gemini":
        reply = _gemini_reply(message)
    elif provider == "grok":
        reply = _grok_reply(message)
    elif provider == "ollama":
        reply = _ollama_reply(message)
        
    if not reply:
        reply = _fallback_response(message)
        
    try:
        db.save_log("assistant", reply)
    except Exception:
        pass
        
    return jsonify({"reply": reply})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password or not name:
        return jsonify({"error": "Missing fields"}), 400
        
    db.ensure_schema()
    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered"}), 400
        
    uid = db.create_user(email, _hash_password(password), name)
    if not uid:
        return jsonify({"error": "Registration failed"}), 500
        
    token = _make_token(uid, email)
    return jsonify({"token": token})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing fields"}), 400
        
    db.ensure_schema()
    user = db.get_user_by_email(email)
    if not user or not _verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401
        
    token = _make_token(user["id"], user["email"])
    return jsonify({"token": token})

if __name__ == '__main__':
    app.run(debug=True, port=8002)
