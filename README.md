# 🌟 MindCare Navigator

> **"Your mental health is a priority. Your happiness is essential. Your self-care is a necessity."**

MindCare Navigator is a **compassionate, voice-enabled AI companion** for mental health support. Built with Flask + Supabase, powered by Groq/Gemini/Grok AI providers.

---

## ✨ Features

- 🎙️ **Voice-First Empathy** — AI responds with calming, emotional tones via Fish Audio TTS
- 🌍 **Multi-language** — English, Hindi, Marathi support
- 📍 **Psychologist Locator** — Find verified mental health professionals via OpenStreetMap
- 🤝 **Community Wall** — Share your journey anonymously
- 🤖 **Multi-AI Fallback** — Groq → Gemini → Grok → Ollama (local) → canned responses
- 🔐 **Secure Auth** — JWT + bcrypt password hashing
- 💬 **Direct Messaging** — Users ↔ Psychologists real-time chat

---

## 🛠️ Tech Stack

| Layer | Technology |
|:---|:---|
| **Backend** | Python Flask |
| **Database** | Supabase (PostgreSQL) |
| **AI** | Groq, Gemini, Grok, Ollama |
| **Auth** | JWT + bcrypt |
| **Voice** | Fish Audio TTS |
| **Frontend** | HTML5 + Bootstrap 5 + Glassmorphism CSS |

---

## 📂 Project Structure

```
.
├── app.py                  # Flask entry point (blueprint registration)
├── db.py                   # Database layer (Supabase operations)
├── supabase_client.py      # Supabase PostgreSQL client
├── tts_service.py          # Fish Audio TTS integration
├── requirements.txt        # Python dependencies
├── vercel.json             # Vercel deployment config
├── .env.example            # Environment variables template
├── quickstart_test.py      # API integration test script
├── SUPABASE_SETUP.sql      # Database schema reference
│
├── backend/                # Application logic
│   ├── config.py           #   Centralized configuration
│   ├── helpers.py          #   JWT, passwords, text processing
│   ├── ai/
│   │   └── providers.py    #   AI provider implementations
│   └── routes/
│       ├── auth.py         #   Register + login
│       ├── chat.py         #   AI chat, TTS, history
│       ├── psychologist.py #   Psych features, messaging, locator
│       ├── community.py    #   Community posts + likes
│       └── pages.py        #   HTML page routes
│
├── templates/              # Jinja2 HTML templates
├── static/
│   ├── css/style.css       #   Custom styles
│   └── js/                 #   Chat JS, translations
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Vinay-ops/Mental-health-chatbot-chat-voice-.git
cd Mental-health-chatbot-chat-voice-
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your keys (at minimum: DATABASE_URL + one AI provider key)
```

### 3. Run

```bash
python app.py
# → http://localhost:8002
```

### 4. Test

```bash
python quickstart_test.py
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|:---|:---|:---|
| `DATABASE_URL` | ✅ | Supabase PostgreSQL connection string |
| `GROQ_API_KEY` | ⭐ | Groq API key (fastest) |
| `GEMINI_API_KEY` | ⭐ | Google Gemini API key |
| `XAI_API_KEY` | ⭐ | xAI Grok API key |
| `FISH_AUDIO_API_KEY` | ❌ | Fish Audio TTS key (for voice) |
| `JWT_SECRET` | ✅ | Secret for JWT tokens (change in prod!) |

At least one AI provider key is needed for chat to work.

---

## 🚢 Deploy to Vercel

This project is pre-configured for Vercel deployment.

### Option A: Git-based (recommended)

1. Push to GitHub
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your GitHub repo
4. Vercel auto-detects the Python project via `vercel.json`
5. **Add environment variables** in the Vercel dashboard (same as `.env`)
6. Deploy

### Option B: CLI

```bash
npm i -g vercel
vercel login
vercel          # Follow prompts
vercel --prod   # Deploy to production
```

### ⚠️ Important Vercel Notes

- **No local DB on Vercel** — You must use a remote Supabase/PostgreSQL database (`DATABASE_URL`)
- **In-memory session store** resets between requests on Vercel — for persistent sessions, use Supabase tables
- **Cold starts** may take 5-10s on the free tier
- Set all API keys in the Vercel dashboard, not in `.env`

---

## 🛡️ Safety

MindCare Navigator is a **non-diagnostic** support tool. It provides grounding, emotional guidance, and professional referrals. **If you are in an immediate crisis, please call your local emergency services.**

---

*Built with ❤️ by [Vinay Bhogal](https://github.com/Vinay-ops)*
