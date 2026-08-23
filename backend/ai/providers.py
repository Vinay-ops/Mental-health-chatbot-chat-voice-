"""
AI Provider implementations for MindCare Navigator.
Supports: Groq, Gemini, Grok (xAI), Ollama (local fallback).
"""

import os
import logging
import requests
from typing import Optional

from backend.config import (
    GROQ_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_API_KEY,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe system prompt
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Provider: Groq
# ---------------------------------------------------------------------------

def groq_reply(message: str, system_prompt: str) -> Optional[str]:
    """Generate a reply using Groq API."""
    if not GROQ_API_KEY:
        log.debug("Groq API key missing")
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        for model in ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"]:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.95,
                "top_p": 0.9,
                "max_tokens": 220,
            }
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload, headers=headers, timeout=8,
                )
                j = r.json()
                if "choices" in j:
                    return j["choices"][0].get("message", {}).get("content")
                log.debug("Groq %s failed: %s", model, j.get('error', {}).get('message'))
            except requests.exceptions.Timeout:
                log.debug("Groq %s timed out.", model)
                continue
            except Exception as e:
                log.debug("Groq %s error: %s", model, e)
                continue
        return None
    except Exception as e:
        log.error("Groq exception: %s", e)
        return None


# ---------------------------------------------------------------------------
# Provider: Gemini
# ---------------------------------------------------------------------------

def gemini_reply(message: str, system_prompt: str) -> Optional[str]:
    """Generate a reply using Google Gemini API."""
    if not GEMINI_API_KEY:
        return None
    try:
        models_to_try = [
            ("v1beta", "gemini-1.5-flash"),
            ("v1beta", "gemini-1.5-pro"),
            ("v1", "gemini-1.5-flash"),
            ("v1", "gemini-pro"),
        ]
        for version, model in models_to_try:
            url = (
                f"https://generativelanguage.googleapis.com/{version}"
                f"/models/{model}:generateContent?key={GEMINI_API_KEY}"
            )
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser: {message}"}]}],
                "generationConfig": {
                    "temperature": 0.9,
                    "topP": 0.95,
                    "topK": 50,
                    "maxOutputTokens": 220,
                },
            }
            r = requests.post(url, json=payload, headers=headers, timeout=15)
            j = r.json()
            if "error" not in j:
                candidates = j.get("candidates", [{}])
                return (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text")
                )
            log.debug("Gemini %s (%s) failed: %s", model, version, j['error'].get('message'))
        return None
    except Exception as e:
        log.error("Gemini exception: %s", e)
        return None


# ---------------------------------------------------------------------------
# Provider: Grok (xAI)
# ---------------------------------------------------------------------------

def grok_reply(message: str, system_prompt: str) -> Optional[str]:
    """Generate a reply using xAI Grok API."""
    if not XAI_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        }
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
        r = requests.post(
            "https://api.x.ai/v1/chat/completions",
            json=payload, headers=headers, timeout=30,
        )
        j = r.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Provider: Ollama (local fallback)
# ---------------------------------------------------------------------------

def ollama_reply(message: str, system_prompt: str) -> Optional[str]:
    """Generate a reply using local Ollama instance."""
    try:
        headers = {}
        if OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{system_prompt}\nUser: {message}\nAssistant:",
            "stream": False,
            "options": {
                "temperature": 0.95,
                "top_p": 0.9,
                "top_k": 50,
                "num_predict": 220,
            },
        }
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload, headers=headers, timeout=30,
        )
        resp = r.json().get("response", "")
        return resp.strip() or None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

# Provider lookup map
_PROVIDERS = {
    "groq": groq_reply,
    "gemini": gemini_reply,
    "grok": grok_reply,
    "ollama": ollama_reply,
}


def generate_reply(provider: str, message: str, system_prompt: str) -> str:
    """
    Generate a reply using the specified provider.
    Falls back to Ollama then to a local canned response on failure.
    """
    fn = _PROVIDERS.get(provider)
    raw_reply = fn(message, system_prompt) if fn else None

    # Fallback chain: requested provider -> Ollama -> canned
    if not raw_reply:
        log.debug("Provider '%s' failed. Falling back to Ollama...", provider)
        raw_reply = ollama_reply(message, system_prompt)

    if not raw_reply:
        log.debug("All providers failed. Using local fallback.")
        raw_reply = _local_fallback(message)

    return raw_reply


# ---------------------------------------------------------------------------
# Local canned fallback (last resort)
# ---------------------------------------------------------------------------

def _local_fallback(message: str) -> str:
    """Very basic keyword-based fallback when all APIs are unavailable."""
    import re
    import random

    m = message.lower()
    words = set(re.findall(r'\w+', m))

    if words & {"hello", "hi", "hey"}:
        return random.choice([
            "Hello! I'm here to listen and support you. What's on your mind today?",
            "Hi there! I'm glad you're here. How are you feeling?",
            "Hey! Welcome. I'm here to help. What can we talk about?",
            "Hello! I'm MindCare Navigator. How can I support you today?",
        ])

    if words & {"stress", "stressed", "overwhelmed", "anxious"}:
        return random.choice([
            "It sounds like you're carrying a lot right now. That's completely valid. Would you like to try some calming techniques?",
            "I hear that you're feeling overwhelmed. Let's work through this together. A breathing exercise might help—interested?",
            "That sounds challenging. Stress is your mind and body's way of responding. Let's explore what might help you feel better.",
            "I'm sorry you're feeling this way. Want to try the 4-7-8 breathing exercise? It's quite effective.",
        ])

    if words & {"resources", "help", "support"}:
        return random.choice([
            "Absolutely, I can help! Are you looking for local professional support, online communities, or wellness resources?",
            "I'm here to help. Would you prefer information about mental health professionals, support groups, or other resources?",
            "That's great that you're seeking support. Let me help—are you looking for clinics, helplines, or online resources?",
        ])

    if words & {"breathing", "exercise"}:
        return random.choice([
            "Great idea! Let's try the 4-7-8 breathing technique: breathe in for 4 counts, hold for 7, exhale for 8. Shall we?",
            "Breathing exercises are powerful. Let me teach you the 4-7-8 method: in-4, hold-7, out-8. Ready to start?",
            "Perfect choice. The 4-7-8 breathing pattern calms your nervous system. Let's practice together.",
        ])

    return random.choice([
        "I hear you. Could you share a bit more about what you're experiencing? I'm here to listen.",
        "Thank you for sharing. Tell me more—I'm here to understand and support you.",
        "I appreciate you opening up. What else would you like to talk about?",
        "I'm listening. What's the main thing on your mind right now?",
        "I'm here for you. Let's explore this together. Can you tell me more?",
    ])
