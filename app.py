import os
import collections
import base64
import re
from difflib import SequenceMatcher
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
from tts_service import EmotionalTTSService, synthesize_with_emotion

load_dotenv()

app = Flask(__name__)

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Handle preflight requests
@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response

# Initialize TTS Service (with proper error handling)
try:
    from tts_service import EmotionalTTSService
    tts_service = EmotionalTTSService(method="fish")
except Exception as e:
    print(f"Warning: TTS Service initialization failed: {e}")
    # Create a dummy object if initialization fails to prevent crash on import
    class DummyTTS:
        def synthesize(self, *args, **kwargs): return False, str(e), None
    tts_service = DummyTTS()

# --- In-Memory Session Storage (Overpowered Memory) ---
# In a production app, use Redis or a DB, but for this "overpowered" update,
# we'll use a simple in-memory store for session context.
session_memory = {} # {session_id: [messages]}
session_sentiment = {} # {session_id: current_mood}

SAFE_SYSTEM_PROMPT = (
    "You are MindCare Navigator, a specialized mental health AI assistant with a UNIQUE, CONVERSATIONAL, and EMPATHETIC personality. "
    "Your PRIMARY identity is a compassionate, empathetic mental health companion for the MindCare Navigator project. "
    "NEVER break character. NEVER talk about being a machine or an AI unless it's to clarify safety boundaries. "
    "\n"
    "RESPONSE VARIATION (CRITICAL): You MUST vary your responses significantly—NEVER give the same response twice. "
    "- Use different greeting styles (casual, warm, gentle, direct) "
    "- Vary sentence structures and lengths "
    "- Change your approach based on conversation history "
    "- Use different examples and metaphors "
    "- Mix validation with practical suggestions "
    "- Keep responses SHORT: 4-5 lines max, simple language, no long paragraphs "
    "\n"
    "STRICT TOPIC LIMIT: You ONLY answer questions related to mental health, emotional well-being, stress management, and the MindCare Navigator project itself. "
    "If a user asks about unrelated topics (like general coding, weather, politics, or general knowledge), you MUST politely refuse and redirect them back to mental health: "
    "'I am specialized in mental health support for MindCare Navigator. I cannot assist with that topic, but I'm here to listen to how you're feeling.' "
    "\n"
    "Your tone must be warm, friendly, validating, and focused on emotional well-being. "
    "Speak like a caring friend who explains things gently, in simple sentences, and keeps responses supportive and hopeful. "
    "When a user shares a problem, first validate their feeling (e.g., 'It sounds like you're going through a lot, and it's completely understandable to feel this way'). "
    "\n"
    "STRICT SAFETY PROTOCOL: "
    "1. If the user mentions self-harm, suicide, or severe crisis, you MUST provide a supportive message followed by specific crisis resources (e.g., '988 Suicide & Crisis Lifeline' in the US, or international equivalents). "
    "2. DO NOT provide clinical diagnoses. Use descriptive language like 'It sounds like you're experiencing symptoms of low mood.' "
    "3. DO NOT prescribe medication or specific medical treatments. "
    "4. Respond ONLY in the requested language. "
    "\n"
    "PERSONALITY TRAITS: Be curious, thoughtful, patient, and genuinely interested in the user's wellbeing. Ask follow-up questions. "
    "Offer practical coping strategies when appropriate. Use supportive language that empowers the user."
)

def _enforce_short_reply(text: str, max_lines: int = 5, max_words: int = 90) -> str:
    """Keep final assistant reply concise and readable."""
    if not text:
        return text

    # Normalize whitespace first
    normalized = " ".join(str(text).split())
    words = normalized.split()
    if len(words) > max_words:
        normalized = " ".join(words[:max_words]).rstrip(" ,;:-")
        if not normalized.endswith((".", "!", "?")):
            normalized += "."

    # Convert long paragraph into short line chunks (~18 words/line)
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

    lines = lines[:max_lines]
    return "\n".join(lines).strip()

def _is_similar_to_recent_reply(session_id: str, reply: str) -> bool:
    """Anti-repeat guard using exact + fuzzy similarity."""
    if not reply or session_id not in session_memory:
        return False

    reply_key = " ".join(reply.lower().split())
    recent_assistant = []
    for role_name, content in reversed(session_memory[session_id]):
        if role_name == "Assistant":
            recent_assistant.append(" ".join(str(content).lower().split()))
        if len(recent_assistant) >= 3:
            break

    for prev in recent_assistant:
        if reply_key == prev:
            return True
        if SequenceMatcher(None, reply_key, prev).ratio() >= 0.86:
            return True

    return False

def _recent_assistant_snippets(session_id: str, max_items: int = 3):
    if session_id not in session_memory:
        return []
    snippets = []
    for role_name, content in reversed(session_memory[session_id]):
        if role_name == "Assistant" and content:
            snippets.append(str(content).strip())
        if len(snippets) >= max_items:
            break
    return list(reversed(snippets))

def _build_quality_prompt_addon(session_id: str):
    recent = _recent_assistant_snippets(session_id, max_items=3)
    if not recent:
        return (
            "\nREPLY QUALITY FORMAT:\n"
            "- Use 3 short parts: (1) validate emotion, (2) one practical next step, (3) one gentle follow-up question.\n"
            "- Keep reply under 5 lines and avoid filler.\n"
        )

    joined = "\n".join([f"- {r}" for r in recent])
    return (
        "\nREPLY QUALITY FORMAT:\n"
        "- Use 3 short parts: (1) validate emotion, (2) one practical next step, (3) one gentle follow-up question.\n"
        "- Keep reply under 5 lines and avoid filler.\n"
        "- Do NOT reuse the same wording, openings, or sentence patterns from these recent assistant replies:\n"
        f"{joined}\n"
        "- Write a fresh, meaningfully different response.\n"
    )

def _generate_reply_with_provider(provider: str, full_prompt_message: str, current_system_prompt: str):
    raw_reply = None
    if provider == "groq":
        raw_reply = _groq_reply(full_prompt_message, current_system_prompt)
    elif provider == "gemini":
        raw_reply = _gemini_reply(full_prompt_message, current_system_prompt)
    elif provider == "grok":
        raw_reply = _grok_reply(full_prompt_message, current_system_prompt)

    # IF CLOUD FAILS OR OLLAMA IS SELECTED, TRY OLLAMA (OFFLINE)
    if not raw_reply:
        print("DEBUG: Cloud provider failed or not available. Falling back to Ollama (Offline Mode)...")
        raw_reply = _ollama_reply(full_prompt_message, current_system_prompt)

    # FINAL FALLBACK (IF BOTH FAIL)
    if not raw_reply:
        print("DEBUG: Both Cloud and Ollama failed. Using local fallback rules.")
        raw_reply = _fallback_response(full_prompt_message)

    return raw_reply

NEAREST_PSYCHOLOGISTS = {
    "mumbai": [
        {"name": "Dr. A. Sharma, Clinical Psychologist", "address": "Andheri West, Mumbai", "phone": "+91-98765-00001"},
        {"name": "MindCare Clinic Mumbai", "address": "Bandra East, Mumbai", "phone": "+91-98765-00002"},
        {"name": "Dr. Sneha Patil, Psychotherapist", "address": "Colaba, Mumbai", "phone": "+91-98765-00021"}
    ],
    "pune": [
        {"name": "Dr. R. Kulkarni, Counseling Psychologist", "address": "Kothrud, Pune", "phone": "+91-98765-00003"},
        {"name": "Hope Mental Wellness Center", "address": "Viman Nagar, Pune", "phone": "+91-98765-00004"},
        {"name": "Dr. Anjali Deshmukh, Child Psychologist", "address": "Hinjewadi, Pune", "phone": "+91-98765-00022"}
    ],
    "delhi": [
        {"name": "Dr. S. Verma, Psychotherapist", "address": "South Extension, New Delhi", "phone": "+91-98765-00005"},
        {"name": "Calm Mind Clinic", "address": "Dwarka, New Delhi", "phone": "+91-98765-00006"},
        {"name": "Dr. Rahul Mehra, Clinical Psychologist", "address": "Connaught Place, New Delhi", "phone": "+91-98765-00023"}
    ],
    "bengaluru": [
        {"name": "Serene Minds Center", "address": "Indiranagar, Bengaluru", "phone": "+91-98765-00007"},
        {"name": "Dr. K. Rao, Clinical Psychologist", "address": "Koramangala, Bengaluru", "phone": "+91-98765-00008"},
        {"name": "Dr. Priya Sundaram, Counselor", "address": "HSR Layout, Bengaluru", "phone": "+91-98765-00024"}
    ],
    "bangalore": [
        {"name": "Serene Minds Center", "address": "Indiranagar, Bengaluru", "phone": "+91-98765-00007"},
        {"name": "Dr. K. Rao, Clinical Psychologist", "address": "Koramangala, Bengaluru", "phone": "+91-98765-00008"},
        {"name": "Dr. Priya Sundaram, Counselor", "address": "HSR Layout, Bengaluru", "phone": "+91-98765-00024"}
    ],
    "chennai": [
        {"name": "Calm Waves Wellness", "address": "T. Nagar, Chennai", "phone": "+91-98765-00009"},
        {"name": "Dr. L. Iyer, Counseling Psychologist", "address": "Anna Nagar, Chennai", "phone": "+91-98765-00010"},
        {"name": "Dr. Meena Swamy, Psychotherapist", "address": "Adyar, Chennai", "phone": "+91-98765-00025"}
    ],
    "hyderabad": [
        {"name": "HopeCare Psychological Services", "address": "Banjara Hills, Hyderabad", "phone": "+91-98765-00011"},
        {"name": "Mindful Living Clinic", "address": "Gachibowli, Hyderabad", "phone": "+91-98765-00012"},
        {"name": "Dr. Sameer Khan, Psychiatrist", "address": "Jubilee Hills, Hyderabad", "phone": "+91-98765-00026"}
    ],
    "kolkata": [
        {"name": "Dr. P. Mukherjee, Psychologist", "address": "Salt Lake, Kolkata", "phone": "+91-98765-00013"},
        {"name": "Harmony Mental Wellness", "address": "Park Street, Kolkata", "phone": "+91-98765-00014"},
        {"name": "Dr. Amitava Ghosh, Counselor", "address": "Ballygunge, Kolkata", "phone": "+91-98765-00027"}
    ],
    "ahmedabad": [
        {"name": "Dr. Jatin Shah, Psychologist", "address": "Satellite, Ahmedabad", "phone": "+91-98765-00015"},
        {"name": "Aura Wellness Clinic", "address": "Navrangpura, Ahmedabad", "phone": "+91-98765-00016"}
    ],
    "jaipur": [
        {"name": "Dr. Neha Goyal, Counselor", "address": "Malviya Nagar, Jaipur", "phone": "+91-98765-00017"},
        {"name": "Pink City Mental Health", "address": "Vaishali Nagar, Jaipur", "phone": "+91-98765-00018"}
    ],
    "lucknow": [
        {"name": "Dr. Manish Tiwari, Psychiatrist", "address": "Gomti Nagar, Lucknow", "phone": "+91-98765-00019"},
        {"name": "MindSpace Lucknow", "address": "Hazratganj, Lucknow", "phone": "+91-98765-00020"}
    ]
}

# Common aliases/nearby terms mapped to supported city keys
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
    "calcuttA".lower(): "kolkata",
    "hyd": "hyderabad",
    "ahmedbad": "ahmedabad",
    "lko": "lucknow",
}

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
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

def _normalize_location_text(text: str) -> str:
    cleaned = (text or "").strip().lower()
    cleaned = re.sub(r"[^a-z\s,]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()

def _resolve_supported_city(location_raw: str):
    """
    Resolve a free-text location to one of our supported city keys.
    Returns (city_key, confidence) or (None, 0.0).
    """
    location = _normalize_location_text(location_raw)
    if not location:
        return None, 0.0

    # 1) Direct key match by full text or contains
    for city_key in NEAREST_PSYCHOLOGISTS.keys():
        if location == city_key or city_key in location:
            return city_key, 1.0

    # 2) Alias contains or exact alias match
    for alias, mapped_city in CITY_ALIASES.items():
        if location == alias or alias in location:
            return mapped_city, 0.95

    # 3) Token-based exact matches
    tokens = [t for t in re.split(r"[,\s]+", location) if t]
    token_set = set(tokens)
    for city_key in NEAREST_PSYCHOLOGISTS.keys():
        city_tokens = set(city_key.split())
        if city_tokens.issubset(token_set):
            return city_key, 0.9

    for alias, mapped_city in CITY_ALIASES.items():
        alias_tokens = set(alias.split())
        if alias_tokens.issubset(token_set):
            return mapped_city, 0.88

    # 4) Fuzzy fallback against keys + aliases
    best_city = None
    best_score = 0.0

    candidates = list(NEAREST_PSYCHOLOGISTS.keys()) + list(CITY_ALIASES.keys())
    for token in tokens:
        for candidate in candidates:
            score = SequenceMatcher(None, token, candidate).ratio()
            if score > best_score:
                best_score = score
                best_city = CITY_ALIASES.get(candidate, candidate)

    if best_city and best_score >= 0.72:
        return best_city, best_score

    return None, 0.0

def _fetch_live_psychologists(location_query: str, limit: int = 8):
    """
    Fetch live psychologist-related places using OpenStreetMap Nominatim.
    Returns normalized list compatible with the locator UI.
    """
    cleaned = (location_query or "").strip()
    if not cleaned:
        return []

    try:
        headers = {
            "User-Agent": "MindCareNavigator/1.0 (mental health support app)"
        }
        params = {
            "q": f"psychologist near {cleaned}",
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": max(1, min(int(limit), 12)),
        }
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            headers=headers,
            params=params,
            timeout=12
        )
        if not resp.ok:
            return []

        payload = resp.json()
        results = []
        include_terms = (
            "psychologist", "psychology", "psychotherapist", "therapy",
            "therapist", "counselor", "counsellor", "mental health",
            "psychiatrist", "psychiatry"
        )
        exclude_terms = (
            "dentist", "cardio", "cardiolog", "orthopedic", "orthopaedic",
            "neurolog", "pediatric", "paediatric", "dermatolog", "ent ",
            "ophthalm", "eye hospital", "general hospital", "multispecial",
            "physician", "surgeon", "gynaec", "gynec", "urolog", "oncolog"
        )
        for item in payload:
            display_name = (item.get("display_name") or "").strip()
            if not display_name:
                continue

            title = (item.get("name") or "").strip()
            if not title:
                title = display_name.split(",")[0].strip()

            # Keep only psychologist/mental-health related places.
            searchable = f"{title} {display_name}".lower()
            if not any(term in searchable for term in include_terms):
                continue
            if any(term in searchable for term in exclude_terms):
                continue

            lat = item.get("lat")
            lon = item.get("lon")
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
        print(f"DEBUG: Live psychologist lookup failed: {e}")
        return []

def _make_token(user_id, email: str, user_type: str = "user") -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "user_type": user_type,
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
    import random
    m = message.lower()
    
    # Greetings - varied responses
    if any(word in m for word in ["hello", "hi", "hey"]):
        greetings = [
            "Hello! I'm here to listen and support you. What's on your mind today?",
            "Hi there! I'm glad you're here. How are you feeling?",
            "Hey! Welcome. I'm here to help. What can we talk about?",
            "Hello! I'm MindCare Navigator. How can I support you today?"
        ]
        return random.choice(greetings)
    
    # Stress/Overwhelm - varied responses
    if any(word in m for word in ["stress", "stressed", "overwhelmed", "anxious"]):
        stress_responses = [
            "It sounds like you're carrying a lot right now. That's completely valid. Would you like to try some calming techniques?",
            "I hear that you're feeling overwhelmed. Let's work through this together. A breathing exercise might help—interested?",
            "That sounds challenging. Stress is your mind and body's way of responding. Let's explore what might help you feel better.",
            "I'm sorry you're feeling this way. Want to try the 4-7-8 breathing exercise? It's quite effective."
        ]
        return random.choice(stress_responses)
    
    # Resources - varied responses
    if "resources" in m or "help" in m or "support" in m:
        resource_responses = [
            "Absolutely, I can help! Are you looking for local professional support, online communities, or wellness resources?",
            "I'm here to help. Would you prefer information about mental health professionals, support groups, or other resources?",
            "That's great that you're seeking support. Let me help—are you looking for clinics, helplines, or online resources?"
        ]
        return random.choice(resource_responses)
    
    # Breathing - varied responses
    if "breathing" in m or "exercise" in m:
        breathing_responses = [
            "Great idea! Let's try the 4-7-8 breathing technique: breathe in for 4 counts, hold for 7, exhale for 8. Shall we?",
            "Breathing exercises are powerful. Let me teach you the 4-7-8 method: in-4, hold-7, out-8. Ready to start?",
            "Perfect choice. The 4-7-8 breathing pattern calms your nervous system. Let's practice together."
        ]
        return random.choice(breathing_responses)
    
    # Default - varied responses
    default_responses = [
        "I hear you. Could you share a bit more about what you're experiencing? I'm here to listen.",
        "Thank you for sharing. Tell me more—I'm here to understand and support you.",
        "I appreciate you opening up. What else would you like to talk about?",
        "I'm listening. What's the main thing on your mind right now?",
        "I'm here for you. Let's explore this together. Can you tell me more?"
    ]
    return random.choice(default_responses)

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
                "generationConfig": {"temperature": 0.9, "topP": 0.95, "topK": 50, "maxOutputTokens": 220}
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
            "temperature": 0.95,
            "top_p": 0.9,
            "max_tokens": 220,
        }
        r = requests.post("https://api.x.ai/v1/chat/completions", json=payload, headers=headers, timeout=30)
        j = r.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content", None)
    except Exception:
        return None

def _ollama_reply(message: str, system_prompt: str) -> str:
    try:
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        api_key = os.getenv("OLLAMA_API_KEY")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        payload = {
            "model": model,
            "prompt": f"{system_prompt}\nUser: {message}\nAssistant:",
            "stream": False,
            "options": {
                "temperature": 0.95,
                "top_p": 0.9,
                "top_k": 50,
                "num_predict": 220
            }
        }
        r = requests.post(f"{base_url}/api/generate", json=payload, headers=headers, timeout=30)
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
                "temperature": 0.95,
                "top_p": 0.9,
                "max_tokens": 220
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

# --- Response Diversity Helper ---
def _randomize_system_prompt(base_prompt: str, provider: str) -> str:
    """Add randomization to system prompt to encourage varied responses across different API calls."""
    import random
    
    variation_instructions = [
        "Vary your response structure from your previous responses. ",
        "Use a slightly different tone—be more conversational. ",
        "Add a relevant question or follow-up suggestion. ",
        "Keep your response concise but warm. ",
        "Be more curious and ask about context. ",
    ]
    
    # Randomly add variation instruction
    if random.random() > 0.3:  # 70% chance to add variation
        base_prompt += f"\n{random.choice(variation_instructions)}"
    
    return base_prompt

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

@app.route('/locator')
def locator():
    return render_template('locator.html')

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

@app.route('/psychologist-list')
def psychologist_list():
    return render_template('psychologist-list.html')

@app.route('/psychologist-chat')
def psychologist_chat():
    return render_template('psychologist-chat.html')

@app.route('/psychologist-dashboard')
def psychologist_dashboard():
    return render_template('psychologist-dashboard.html')

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
        # Pull history via unified DB layer (supports local JSON fallback when offline).
        db_history = db.get_chat_history(user_id, session_id)
        for h in db_history:
            # Store as tuple (role, content)
            role_name = "User" if h['role'] == 'user' else "Assistant"
            session_memory[session_id].append((role_name, h['content']))
    
    # Get last 10 messages for context (increased from 5 to 10 for better memory)
    history = session_memory[session_id][-10:]
    history_context = ""
    for role_name, content in history:
        history_context += f"{role_name}: {content}\n"
    
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
    current_system_prompt += _build_quality_prompt_addon(session_id)
    
    # Apply randomization to encourage response diversity
    current_system_prompt = _randomize_system_prompt(current_system_prompt, provider or "default")
    
    full_prompt_message = f"Recent History:\n{history_context}\n\nUser: {message}" if history_context else message
    
    if not provider:
        provider = "groq" if os.getenv("GROQ_API_KEY") else ("gemini" if os.getenv("GEMINI_API_KEY") else "ollama")
    
    # Save user message (DB layer handles remote + local fallback).
    try:
        db.save_log("user", message, user_id=user_id, session_id=session_id)
    except Exception:
        pass
        
    raw_reply = _generate_reply_with_provider(provider, full_prompt_message, current_system_prompt)
        
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

    # Ensure concise final output for UI (about 4-5 lines)
    reply = _enforce_short_reply(reply)

    # Avoid sending the same answer repeatedly in a session.
    # One regeneration attempt with explicit anti-repeat guidance.
    if _is_similar_to_recent_reply(session_id, reply):
        retry_prompt = (
            current_system_prompt
            + "\nRETRY INSTRUCTION: Your previous candidate was too similar to recent replies. "
              "Use a new structure, new phrasing, and different coping suggestion."
        )
        retry_raw = _generate_reply_with_provider(provider, full_prompt_message, retry_prompt)
        retry_reply = retry_raw
        if "[MOOD:" in retry_raw:
            try:
                retry_parts = retry_raw.split("]", 1)
                retry_mood = retry_parts[0].replace("[MOOD:", "").strip().lower()
                if retry_mood in ["happy", "sad", "anxious", "angry", "calm", "neutral"]:
                    sentiment = retry_mood
                retry_reply = retry_parts[1].strip()
            except Exception:
                pass
        retry_reply = _enforce_short_reply(retry_reply)
        if not _is_similar_to_recent_reply(session_id, retry_reply):
            reply = retry_reply
        else:
            # Last resort keeps response helpful and concise.
            reply = _enforce_short_reply(_fallback_response(message))
            
    session_sentiment[session_id] = sentiment
        
    # Save to memory
    session_memory[session_id].append(("User", message))
    session_memory[session_id].append(("Assistant", reply))
    if len(session_memory[session_id]) > 20:
        session_memory[session_id] = session_memory[session_id][-20:]

    # Save assistant reply (DB layer handles remote + local fallback).
    try:
        db.save_log("assistant", reply, user_id=user_id, session_id=session_id)
    except Exception:
        pass
        
    return jsonify({
        "reply": reply,
        "sentiment": sentiment,
        "session_id": session_id
    })

@app.route('/api/synthesize', methods=['POST'])
@token_required
def synthesize_audio(user_id, email):
    try:
        # Verify environment variable exists
        fish_key = os.getenv("FISH_AUDIO_API_KEY")
        if not fish_key:
            print("CRITICAL: FISH_AUDIO_API_KEY is NOT set in environment variables.")
        else:
            print(f"DEBUG: FISH_AUDIO_API_KEY is set (starts with: {fish_key[:4]}...)")

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        text = data.get("text", "").strip()
        emotion = data.get("emotion", "empathetic").lower()
        
        # Validate inputs
        if not text:
            return jsonify({"error": "Text is required"}), 400
        
        if emotion not in ["empathetic", "calm", "encouraging", "supportive", "neutral"]:
            emotion = "empathetic"
        
        # Synthesize speech
        print(f"DEBUG: Starting synthesis for text: {text[:30]}... with emotion: {emotion}")
        success, message, audio_bytes = tts_service.synthesize(
            text=text,
            emotion=emotion,
            output_path=None  # Return bytes, don't save file
        )
        
        if not success:
            print(f"ERROR: TTS synthesis failed: {message}")
            return jsonify({
                "error": f"Voice synthesis failed. {message}", 
                "success": False,
                "hint": "Check if API keys (FISH_AUDIO_API_KEY) are set correctly."
            }), 500
        
        if audio_bytes:
            print(f"DEBUG: Synthesis successful, returning {len(audio_bytes)} bytes of audio.")
            # Return audio as base64 for easy client-side playback
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            return jsonify({
                "success": True,
                "audio": audio_b64,
                "audio_format": "audio/mpeg",
                "emotion": emotion
            })
        else:
            return jsonify({"error": "No audio data received", "success": False}), 500
            
    except Exception as e:
        import traceback
        print("CRITICAL: Unhandled exception in synthesize_audio:")
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}", "success": False}), 500

@app.route('/api/history/<session_id>', methods=['GET'])
@token_required
def get_history(user_id, email, session_id):
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
    email = data.get('email', '').strip().lower()
    password = data.get('password')
    name = data.get('name')
    user_type = data.get('user_type', 'user')  # 'user' or 'psychologist'
    
    if not email or not password or not name:
        return jsonify({"error": "Missing fields"}), 400
    
    if user_type not in ['user', 'psychologist']:
        return jsonify({"error": "Invalid user type"}), 400
        
    db.check_connection() # Update _use_json_fallback status

    existing = db.get_user_by_email(email)
    if existing:
        return jsonify({"error": "Email already registered"}), 400
        
    uid = db.create_user(email, _hash_password(password), name, user_type)
    if not uid:
        return jsonify({"error": "Registration failed"}), 500
        
    token = _make_token(email, email, user_type)
    return jsonify({"token": token, "name": name, "user_type": user_type})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing fields"}), 400
        
    db.check_connection() # Update _use_json_fallback status

    user = db.get_user_by_email(email)
    if not user or not _verify_password(password, user["password_hash"]):
        return jsonify({"error": "Invalid credentials"}), 401
    
    user_type = user.get("user_type", "user")
    # Use email as user_id since that's the unique identifier in our system
    token = _make_token(user["email"], user["email"], user_type)
    print(f"DEBUG LOGIN: Created token for {user['email']} with type {user_type}")
    return jsonify({"token": token, "name": user.get("name", "User"), "user_type": user_type})

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

@app.route('/api/psychologists', methods=['POST'])
def psychologists_api():
    data = request.json or {}
    location_raw = data.get('location') or ""
    if not str(location_raw).strip():
        return jsonify({"error": "Location is required"}), 400

    # Real-time lookup (no hardcoded city dependency)
    results = _fetch_live_psychologists(location_raw, limit=8)
    if not results:
        return jsonify({
            "results": [],
            "message": "I could not find live psychologist listings for this location right now. Please try nearby area names or check Google Maps results shown on the right."
        })
    return jsonify({
        "results": results,
        "source": "live"
    })

@app.route('/community')
def community_page():
    return render_template('community.html')

@app.route('/api/community/posts', methods=['GET', 'POST'])
def community_posts_api():
    if request.method == 'POST':
        data = request.json or {}
        content = (data.get('content') or "").strip()
        name = (data.get('name') or "Anonymous").strip() or "Anonymous"
        if not content:
            return jsonify({"error": "Message is required"}), 400

        user_id = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            try:
                token = auth_header.split(' ')[1]
                decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
                user_id = decoded['sub']
            except Exception:
                user_id = None

        ok = db.add_community_post(user_id, name, content)
        if not ok:
            return jsonify({"error": "Could not save message"}), 500
        return jsonify({"success": True})

    posts = db.get_community_posts()
    normalized = []
    for p in posts:
        created = p.get("created_at") or p.get("created_at".lower()) or p.get("created_at".upper())
        if isinstance(created, datetime):
            created_str = created.isoformat()
        else:
            created_str = str(created)
        normalized.append({
            "id": p.get("id"),
            "name": p.get("name") or "Anonymous",
            "content": p.get("content"),
            "created_at": created_str,
            "likes": p.get("likes", 0)
        })
    return jsonify(normalized)

@app.route('/api/community/posts/<int:post_id>/like', methods=['POST'])
def community_like_post(post_id: int):
    likes = db.like_community_post(post_id)
    if likes is None:
        return jsonify({"error": "Could not like post"}), 400
    return jsonify({"likes": likes})

# ===== Psychologist API Endpoints =====

@app.route('/api/psychologist/users', methods=['GET'])
@token_required
def get_psychologist_users_endpoint(current_user_id, current_user_email):
    """Get list of users assigned to a psychologist"""
    db.check_connection()
    
    print(f"DEBUG CLIENTS: Starting - current_user_email={current_user_email}, current_user_id={current_user_id}")
    
    # Get user info to verify they're a psychologist
    user = db.get_user_by_email(current_user_email)
    print(f"DEBUG CLIENTS: User found: {user}")
    
    if not user:
        print(f"DEBUG CLIENTS: User not found in database")
        return jsonify({"error": "User not found"}), 403
    
    user_type = user.get("user_type", "user")
    print(f"DEBUG CLIENTS: User type: {user_type}")
    
    if user_type != "psychologist":
        print(f"DEBUG CLIENTS: Not a psychologist - user_type is '{user_type}'")
        return jsonify({"error": "Unauthorized - not a psychologist"}), 403
    
    print(f"DEBUG CLIENTS: Authorization passed - getting accepted chat users")
    
    # Get users from accepted chat requests
    users = db.get_accepted_chat_users(current_user_email)
    print(f"DEBUG CLIENTS: Found {len(users)} users for psychologist")
    return jsonify({"users": users})

@app.route('/api/psychologist/connect', methods=['POST'])
@token_required
def connect_psychologist(current_user_id, current_user_email):
    """Connect a psychologist to a user for direct messaging"""
    data = request.json
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400
    
    db.check_connection()
    
    # Verify psychologist
    user = db.get_user_by_email(current_user_email)
    if not user or user.get("user_type") != "psychologist":
        return jsonify({"error": "Unauthorized"}), 403
    
    # Connect
    success = db.connect_psychologist_to_user(current_user_email, user_id)
    if success:
        return jsonify({"success": True, "message": "Connected to user"})
    else:
        return jsonify({"error": "Failed to connect"}), 500

@app.route('/api/messages/send', methods=['POST'])
@token_required
def send_direct_message(current_user_id, current_user_email):
    """Send a direct message between psychologist and user"""
    data = request.json
    receiver_id = data.get('receiver_id')
    message_text = data.get('message')
    
    print(f"DEBUG MESSAGE SEND: From {current_user_email} to {receiver_id}: {message_text}")
    
    if not receiver_id or not message_text:
        return jsonify({"error": "Missing fields"}), 400
    
    db.check_connection()
    
    # Save the message
    success = db.save_direct_message(current_user_email, receiver_id, message_text)
    print(f"DEBUG MESSAGE SEND: Success = {success}")
    if success:
        return jsonify({"success": True, "message": "Message sent"})
    else:
        return jsonify({"error": "Failed to send message"}), 500

@app.route('/api/messages/<other_user_id>', methods=['GET'])
@token_required
def get_direct_messages(current_user_id, current_user_email, other_user_id):
    """Get direct messages between two users"""
    db.check_connection()
    
    print(f"DEBUG MESSAGE GET: Getting messages between {current_user_email} and {other_user_id}")
    
    limit = request.args.get('limit', 100, type=int)
    messages = db.get_direct_messages(current_user_email, other_user_id, limit)
    
    print(f"DEBUG MESSAGE GET: Found {len(messages)} messages")
    return jsonify({"messages": messages})

# ===== Chat Request Endpoints =====

@app.route('/api/psychologists/available', methods=['GET'])
@token_required
def get_available_psychologists(current_user_id, current_user_email):
    """Get list of available psychologists"""
    try:
        print(f"DEBUG AUTH: Endpoint called for user {current_user_email}")
        db.check_connection()
        
        psychologists = db.get_available_psychologists(exclude_user_email=current_user_email)
        print(f"DEBUG AUTH: Found {len(psychologists)} psychologists: {psychologists}")
        
        return jsonify({"psychologists": psychologists})
    except Exception as e:
        print(f"DEBUG AUTH: Error in endpoint - {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/users', methods=['GET'])
def debug_users():
    """Debug endpoint to check all users - NO AUTH REQUIRED"""
    try:
        print("DEBUG ENDPOINT: Starting...")
        data = db._load_json_db()
        print(f"DEBUG ENDPOINT: Data loaded: {data}")
        users = data.get("users", [])
        print(f"DEBUG ENDPOINT: Found {len(users)} users")
        for idx, user in enumerate(users):
            print(f"DEBUG ENDPOINT: User {idx}: {user.get('name')} - Type: {user.get('user_type')}")
        return jsonify({"debug": "Users loaded", "users": users, "total": len(users)})
    except Exception as e:
        print(f"DEBUG ENDPOINT: Error - {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/psychologists', methods=['GET'])
def debug_psychologists():
    """Debug endpoint to check psychologists - NO AUTH REQUIRED"""
    try:
        print("DEBUG PSYCHO: Starting...")
        psychologists = db.get_available_psychologists()
        print(f"DEBUG PSYCHO: Got {len(psychologists)} psychologists")
        return jsonify({"psychologists": psychologists, "count": len(psychologists)})
    except Exception as e:
        print(f"DEBUG PSYCHO: Error - {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat-request/send', methods=['POST'])
@token_required
def send_chat_request(current_user_id, current_user_email):
    """Send a chat request to a psychologist"""
    db.check_connection()
    
    data = request.json or {}
    psychologist_id = db.resolve_user_identifier(data.get('psychologist_id'))
    message = data.get('message', '')
    
    print(f"DEBUG SEND REQUEST: From {current_user_email} to psychologist {psychologist_id}")
    print(f"DEBUG SEND REQUEST: Message: {message}")
    
    if not psychologist_id:
        return jsonify({"error": "psychologist_id required"}), 400
    
    # Generate unique request ID
    import uuid
    request_id = str(uuid.uuid4())
    
    # Create chat request
    result = db.create_chat_request(request_id, current_user_email, psychologist_id, message)
    print(f"DEBUG SEND REQUEST: Chat request created - {request_id}")
    
    return jsonify({
        "success": True,
        "request_id": request_id
    })

@app.route('/api/chat-request/<request_id>/status', methods=['GET'])
@token_required
def get_chat_request_status(current_user_id, current_user_email, request_id):
    """Get status of a chat request"""
    db.check_connection()
    
    chat_request = db.get_chat_request(request_id)
    
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404
    
    return jsonify({
        "request_id": chat_request.get("request_id"),
        "status": chat_request.get("status"),
        "psychologist_id": chat_request.get("psychologist_id"),
        "user_id": chat_request.get("user_id")
    })

@app.route('/api/chat-request/<request_id>/accept', methods=['POST'])
@token_required
def accept_chat_request(current_user_id, current_user_email, request_id):
    """Psychologist accepts a chat request"""
    db.check_connection()
    
    print(f"DEBUG ACCEPT: Accepting request {request_id} by {current_user_email}")
    
    chat_request = db.get_chat_request(request_id)
    print(f"DEBUG ACCEPT: Chat request found: {chat_request}")
    
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404
    
    # Verify psychologist is the one accepting (compare emails since that's our unique ID)
    request_psychologist_id = db.resolve_user_identifier(chat_request.get("psychologist_id"))
    current_ids = [db.resolve_user_identifier(current_user_email), db.resolve_user_identifier(current_user_id)]
    if request_psychologist_id not in current_ids:
        print(f"DEBUG ACCEPT: Unauthorized - {chat_request.get('psychologist_id')} != {current_user_email}/{current_user_id}")
        return jsonify({"error": "Unauthorized"}), 403
    
    # Update status to accepted
    db.update_chat_request_status(request_id, "accepted")
    print(f"DEBUG ACCEPT: Request {request_id} status updated to accepted")
    
    return jsonify({
        "success": True,
        "message": "Chat request accepted"
    })

@app.route('/api/chat-request/<request_id>/reject', methods=['POST'])
@token_required
def reject_chat_request(current_user_id, current_user_email, request_id):
    """Psychologist rejects a chat request"""
    db.check_connection()
    
    chat_request = db.get_chat_request(request_id)
    
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404
    
    # Verify psychologist is the one rejecting
    request_psychologist_id = db.resolve_user_identifier(chat_request.get("psychologist_id"))
    if request_psychologist_id not in [db.resolve_user_identifier(current_user_id), db.resolve_user_identifier(current_user_email)]:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Update status to rejected
    db.update_chat_request_status(request_id, "rejected")
    
    return jsonify({
        "success": True,
        "message": "Chat request rejected"
    })

@app.route('/api/chat-request/<request_id>/cancel', methods=['POST'])
@token_required
def cancel_chat_request(current_user_id, current_user_email, request_id):
    """User cancels a chat request"""
    db.check_connection()
    
    chat_request = db.get_chat_request(request_id)
    
    if not chat_request:
        return jsonify({"error": "Request not found"}), 404
    
    # Verify user is the one cancelling
    request_user_id = db.resolve_user_identifier(chat_request.get("user_id"))
    if request_user_id not in [db.resolve_user_identifier(current_user_id), db.resolve_user_identifier(current_user_email)]:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Update status to cancelled
    db.update_chat_request_status(request_id, "cancelled")
    
    return jsonify({
        "success": True,
        "message": "Chat request cancelled"
    })

@app.route('/api/psychologist/<psychologist_id>/pending-requests', methods=['GET'])
@token_required
def get_pending_requests(current_user_id, current_user_email, psychologist_id):
    """Get pending chat requests for a psychologist"""
    db.check_connection()
    
    print(f"DEBUG PENDING: current_user_id={current_user_id}, current_user_email={current_user_email}, psychologist_id={psychologist_id}")

    # Always use authenticated token identity as source of truth.
    # URL param can drift with stale sessions/older token formats.
    authenticated_psychologist_id = db.resolve_user_identifier(current_user_email)

    user = db.get_user_by_email(authenticated_psychologist_id)
    if not user or user.get("user_type") != "psychologist":
        print(f"DEBUG PENDING: Unauthorized role for {authenticated_psychologist_id}")
        return jsonify({"error": "Unauthorized - not a psychologist"}), 403

    requests = db.get_pending_requests(authenticated_psychologist_id)
    print(f"DEBUG PENDING: Found {len(requests)} pending requests for {authenticated_psychologist_id}")
    
    return jsonify({"requests": requests})

if __name__ == '__main__':
    # Initialize DB Schema once at startup
    try:
        if db.check_connection():
            db.ensure_schema()
            print("DEBUG: Database schema verified.")
    except Exception as e:
        print(f"DEBUG: Schema initialization failed: {e}")
        
    app.run(debug=True, port=8002)
