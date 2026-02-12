import os
import collections
# Fix for Python 3.10+ where MutableMapping moved to collections.abc
if not hasattr(collections, 'MutableMapping'):
    import collections.abc
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Mapping = collections.abc.Mapping
    collections.Sequence = collections.abc.Sequence
    collections.Iterable = collections.abc.Iterable
    collections.Callable = collections.abc.Callable

from flask import Flask, render_template, request, jsonify
from functools import wraps
from datetime import datetime, timedelta
import requests
# from google import genai
from passlib.context import CryptContext
import jwt
import db
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)

# --- In-Memory Session Storage (Overpowered Memory) ---
# In a production app, use Redis or a DB, but for this "overpowered" update,
# we'll use a simple in-memory store for session context.
session_memory = {} # {session_id: [messages]}
session_sentiment = {} # {session_id: current_mood}

# --- Configuration ---
SAFE_SYSTEM_PROMPT = (
    "You are MindCare Navigator, a specialized mental health AI assistant. "
    "Your PRIMARY identity is a compassionate, empathetic mental health companion for the MindCare Navigator project. "
    "NEVER break character. NEVER talk about being a machine or an AI unless it's to clarify safety boundaries. "
    "STRICT TOPIC LIMIT: You ONLY answer questions related to mental health, emotional well-being, stress management, and the MindCare Navigator project itself. "
    "If a user asks about unrelated topics (like general coding, weather, politics, or general knowledge), you MUST politely refuse and redirect them back to mental health: "
    "'I am specialized in mental health support for MindCare Navigator. I cannot assist with that topic, but I'm here to listen to how you're feeling.' "
    "Your tone must be warm, validating, and focused on emotional well-being. "
    "When a user shares a problem, first validate their feeling (e.g., 'It sounds like you're going through a lot, and it's completely understandable to feel this way'). "
    "STRICT SAFETY PROTOCOL: "
    "1. If the user mentions self-harm, suicide, or severe crisis, you MUST provide a supportive message followed by specific crisis resources (e.g., '988 Suicide & Crisis Lifeline' in the US, or international equivalents). "
    "2. DO NOT provide clinical diagnoses. Use descriptive language like 'It sounds like you're experiencing symptoms of low mood.' "
    "3. DO NOT prescribe medication or specific medical treatments. "
    "4. Respond ONLY in the requested language."
)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
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

def _make_token(user_id, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
            current_user_id = data['sub']
            current_user_email = data['email']
        except Exception:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user_id, current_user_email, *args, **kwargs)
    
    return decorated

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

def _gemini_reply(message: str, system_prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        # Try different models and versions
        models_to_try = [
            ("v1beta", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-pro"),
            ("v1", "gemini-1.5-flash"),
            ("v1", "gemini-pro")
        ]
        
        for version, model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser: {message}"}]}],
                "generationConfig": {"temperature": 0.4, "topP": 0.8, "topK": 40}
            }
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            j = r.json()
            if "error" not in j:
                return j.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", None)
            else:
                print(f"DEBUG: Gemini {model} ({version}) failed: {j['error'].get('message')}")
        
        return None
    except Exception as e:
        print(f"Gemini Exception: {e}")
        return None

def _grok_reply(message: str, system_prompt: str) -> str:
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        return None
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-2",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.4,
        }
        r = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers, timeout=30)
        j = r.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content", None)
    except Exception:
        return None

def _ollama_reply(message: str, system_prompt: str) -> str:
    try:
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        payload = {
            "model": model,
            "prompt": f"{system_prompt}\nUser: {message}\nAssistant:",
            "stream": False,
        }
        r = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=30)
        j = r.json()
        resp = j.get("response", "")
        return resp.strip() or None
    except Exception:
        return None

def _groq_reply(message: str, system_prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("DEBUG: Groq API key missing")
        return None
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Try a few different models just in case
        for model in ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.5,
                "max_tokens": 1024
            }
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=8)
                j = r.json()
                if "choices" in j:
                    return j.get("choices", [{}])[0].get("message", {}).get("content", None)
                else:
                    print(f"DEBUG: Groq {model} failed: {j.get('error', {}).get('message')}")
            except requests.exceptions.Timeout:
                print(f"DEBUG: Groq {model} timed out. Trying next...")
                continue
            except Exception as e:
                print(f"DEBUG: Groq {model} error: {e}")
                continue
        return None
    except Exception as e:
        print(f"Groq Exception: {e}")
        return None

# --- Removed standalone _analyze_sentiment to favor combined prompt optimization ---

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
def chat():
    return render_template('chat.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

# --- API Endpoints ---

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.json
    message = data.get('message', '')
    provider = data.get('provider')
    lang = data.get('lang', 'en')
    session_id = data.get('session_id')
    
    # Try to get user_id from token if available
    user_id = None
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        try:
            token = auth_header.split(' ')[1]
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
            user_id = decoded['sub']
        except Exception:
            pass

    if not session_id:
        session_id = request.remote_addr # Fallback

    print(f"DEBUG: Chat request - provider: {provider}, lang: {lang}, session: {session_id}, user: {user_id}")
    
    # 1. Sentiment Analysis (Optimization: We derive sentiment in the same call)
    # sentiment = "neutral" # Default
    # if len(message) < 500: 
    #     sentiment = _analyze_sentiment(message)
    # session_sentiment[session_id] = sentiment
    
    # 2. Memory Management
    if session_id not in session_memory:
        session_memory[session_id] = []
        # ALWAYS try to pull history from DB if session exists but memory is empty (e.g. server restart)
        if db.check_connection():
            # If user_id is missing, we still try to get history by session_id if possible
            # But the DB query requires user_id. For now, let's optimize user-linked sessions.
            if user_id:
                db_history = db.get_chat_history(user_id, session_id)
                for h in db_history:
                    # Append in order: user -> assistant -> user...
                    session_memory[session_id].append(h['content'])
            else:
                # If guest, we don't have user_id to query DB safely yet
                # In a future update, we could allow querying guest sessions by ID alone
                pass
    
    # Get last 10 messages for context (increased from 5 to 10 for better memory)
    history = session_memory[session_id][-10:]
    history_context = ""
    for i, m in enumerate(history):
        # Determine role based on position in history (assuming alternating User/Assistant)
        # However, to be safer, we should store roles in session_memory too.
        # For now, we'll use a simpler heuristic or just send the text blocks.
        role = "User" if (len(history) - i) % 2 != 0 else "Assistant"
        history_context += f"{role}: {m}\n"
    
    # Combined Prompt for Reply and Sentiment
    lang_instruction = f" Respond in {lang.upper()} language."
    if lang == 'hi': lang_instruction = " Respond strictly in HINDI (हिन्दी) language."
    elif lang == 'mr': lang_instruction = " Respond strictly in MARATHI (मराठी) language."
        
    current_system_prompt = (
        SAFE_SYSTEM_PROMPT + lang_instruction + 
        "\nIMPORTANT: Your response MUST start with the detected sentiment of the user's message in this exact format: "
        "[MOOD: sentiment_name] followed by your actual response. "
        "Choose sentiment_name from: [happy, sad, anxious, angry, calm, neutral]. "
        "Example: '[MOOD: calm] I am glad you are feeling peaceful...'"
    )
    
    full_prompt_message = f"Recent History:\n{history_context}\n\nUser: {message}" if history_context else message
    
    if not provider:
        provider = "groq" if os.getenv("GROQ_API_KEY") else ("gemini" if os.getenv("GEMINI_API_KEY") else "ollama")
    
    # Save user message to DB
    try:
        if db.check_connection():
            db.save_log("user", message, user_id=user_id, session_id=session_id)
    except Exception:
        pass
        
    raw_reply = None
    if provider == "groq":
        raw_reply = _groq_reply(full_prompt_message, current_system_prompt)
    elif provider == "gemini":
        raw_reply = _gemini_reply(full_prompt_message, current_system_prompt)
    elif provider == "grok":
        raw_reply = _grok_reply(full_prompt_message, current_system_prompt)
    elif provider == "ollama":
        raw_reply = _ollama_reply(full_prompt_message, current_system_prompt)
    
    if not raw_reply:
        raw_reply = _fallback_response(message)
        
    # Parse sentiment and reply
    sentiment = "neutral"
    reply = raw_reply
    if "[MOOD:" in raw_reply:
        try:
            parts = raw_reply.split("]", 1)
            mood_tag = parts[0].replace("[MOOD:", "").strip().lower()
            if mood_tag in ["happy", "sad", "anxious", "angry", "calm", "neutral"]:
                sentiment = mood_tag
            reply = parts[1].strip()
        except Exception:
            pass
            
    session_sentiment[session_id] = sentiment
        
    # Save to memory
    session_memory[session_id].append(message)
    session_memory[session_id].append(reply)
    if len(session_memory[session_id]) > 20:
        session_memory[session_id] = session_memory[session_id][-20:]

    # Save assistant reply to DB
    try:
        if db.check_connection():
            db.save_log("assistant", reply, user_id=user_id, session_id=session_id)
    except Exception:
        pass
        
    return jsonify({
        "reply": reply,
        "sentiment": sentiment,
        "session_id": session_id
    })

@app.route('/api/history/<session_id>', methods=['GET'])
@token_required
def get_history(user_id, email, session_id):
    if not db.check_connection():
        return jsonify({"error": "Database error"}), 503
    history = db.get_chat_history(user_id, session_id)
    # Convert datetime to string for JSON
    for h in history:
        if isinstance(h.get('ts'), datetime):
            h['ts'] = h['ts'].isoformat()
        if '_id' in h:
            h['_id'] = str(h['_id'])
    return jsonify(history)

@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions(user_id, email):
    if not db.check_connection():
        return jsonify({"error": "Database error"}), 503
    sessions = db.get_user_sessions(user_id)
    return jsonify(sessions)

@app.route('/api/new_chat', methods=['POST'])
def new_chat():
    import uuid
    new_id = str(uuid.uuid4())
    return jsonify({"session_id": new_id})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')
    
    if not email or not password or not name:
        return jsonify({"error": "Missing fields"}), 400
        
    if not db.check_connection():
        return jsonify({"error": "Database error. Please try again later."}), 503

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
        
    if not db.check_connection():
        return jsonify({"error": "Database error. Please try again later."}), 503

    user = db.get_user_by_email(email)
    if not user or not _verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401
        
    token = _make_token(user["_id"], user["email"])
    return jsonify({"token": token})

@app.route('/api/contact', methods=['POST'])
def contact_api():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    message = data.get('message')
    
    if not name or not email or not message:
        return jsonify({"error": "Missing fields"}), 400
        
    # In a real app, you might send an email or save to DB
    # For now, we'll just log it
    print(f"Contact Form Submission: {name} ({email}) - {message}")
    
    return jsonify({"success": "Message sent successfully"})

if __name__ == '__main__':
    # Initialize DB Schema once at startup
    try:
        if db.check_connection():
            db.ensure_schema()
            print("DEBUG: Database schema verified.")
    except Exception as e:
        print(f"DEBUG: Schema initialization failed: {e}")
        
    app.run(debug=True, port=8002)
