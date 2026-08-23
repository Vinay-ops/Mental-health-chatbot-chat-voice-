"""
MindCare Navigator - Application Configuration
Centralizes all configuration values loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Flask
FLASK_ENV = os.getenv("FLASK_ENV", "development")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
SERVER_PORT = int(os.getenv("SERVER_PORT", "8002"))

# JWT Authentication
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXP_MIN", "120"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# AI Providers
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")  # Grok
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# TTS
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")

# Features
ENABLE_PSYCHOLOGIST_FEATURE = os.getenv("ENABLE_PSYCHOLOGIST_FEATURE", "True").lower() == "true"

# Chat defaults
MAX_HISTORY_MESSAGES = 10
MAX_SESSION_MEMORY = 20
DEFAULT_PROVIDER = None  # Set dynamically based on available API keys


def get_default_provider() -> str:
    """Return the best available AI provider based on configured API keys."""
    if GROQ_API_KEY:
        return "groq"
    if GEMINI_API_KEY:
        return "gemini"
    return "ollama"
