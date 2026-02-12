import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "libs"))
from typing import Optional, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import requests
import google.generativeai as genai
import db


class ChatInput(BaseModel):
    message: str
    provider: Optional[Literal["gemini", "grok", "ollama"]] = None


class ChatOutput(BaseModel):
    reply: str

class RegisterInput(BaseModel):
    email: str
    password: str
    name: str

class LoginInput(BaseModel):
    email: str
    password: str

class TokenOutput(BaseModel):
    token: str


app = FastAPI(title="MindCare Navigator API")

# Allow local HTML files and common dev origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        "exp": int((datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN)).timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
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


def _gemini_reply(message: str) -> Optional[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(
            [{"role": "user", "parts": [SAFE_SYSTEM_PROMPT]}, {"role": "user", "parts": [message]}]
        )
        return (getattr(resp, "text", None) or "").strip() or None
    except Exception:
        return None


def _grok_reply(message: str) -> Optional[str]:
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

def _ollama_reply(message: str) -> Optional[str]:
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

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/api/register", response_model=TokenOutput)
def register(input: RegisterInput) -> TokenOutput:
    db.ensure_schema()
    existing = db.get_user_by_email(input.email)
    if existing:
        raise ValueError("Email already registered")
    uid = db.create_user(input.email, _hash_password(input.password), input.name)
    if not uid:
        raise ValueError("Registration failed")
    token = _make_token(uid, input.email)
    return TokenOutput(token=token)

@app.post("/api/login", response_model=TokenOutput)
def login(input: LoginInput) -> TokenOutput:
    db.ensure_schema()
    user = db.get_user_by_email(input.email)
    if not user or not _verify_password(input.password, user["password_hash"]):
        raise ValueError("Invalid credentials")
    token = _make_token(user["id"], user["email"])
    return TokenOutput(token=token)


@app.post("/api/chat", response_model=ChatOutput)
def chat(input: ChatInput) -> ChatOutput:
    provider = input.provider or ("gemini" if os.getenv("GEMINI_API_KEY") else ("grok" if os.getenv("XAI_API_KEY") else "ollama"))
    try:
        db.ensure_schema()
        db.save_log("user", input.message)
    except Exception:
        pass
    reply: Optional[str] = None
    if provider == "gemini":
        reply = _gemini_reply(input.message)
    elif provider == "grok":
        reply = _grok_reply(input.message)
    elif provider == "ollama":
        reply = _ollama_reply(input.message)
    if not reply:
        reply = _fallback_response(input.message)
    try:
        db.save_log("assistant", reply)
    except Exception:
        pass
    return ChatOutput(reply=reply)
