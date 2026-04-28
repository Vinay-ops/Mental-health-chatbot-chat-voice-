# Environment Variables Setup Guide

## Overview
This document explains all environment variables needed for the Mental Health Chatbot with Psychologist Feature.

## Files
- **`.env`** - Your local configuration (NOT committed to GitHub, contains secrets)
- **`.env.example`** - Template for other developers (committed to GitHub, no secrets)
- **`.gitignore`** - Includes `.env` to prevent accidental commits

## Getting Started

### 1. Copy the Template
```bash
cp .env.example .env
```

### 2. Fill in Your Values
Edit `.env` with your actual configuration values (DO NOT commit this file).

---

## Environment Variables Reference

### Flask Configuration
```env
FLASK_ENV=development      # Options: development, production
FLASK_DEBUG=True           # Enable debug mode (set to False in production)
SERVER_PORT=8002           # Port to run the server on
```

### Database (Supabase)

**Option A: Using Connection String (Recommended)**
```env
DATABASE_URL=postgresql://postgres:PASSWORD@PROJECT.supabase.co:5432/postgres
```

To get this from Supabase:
1. Go to Project Settings → Database
2. Connection String → Copy the URI with password
3. Replace `[PASSWORD]` and `[PROJECT]` with your values

**Option B: Using Individual Parameters**
```env
PG_HOST=localhost          # Database host
PG_PORT=6543              # Database port
PG_DATABASE=postgres      # Database name
PG_USER=postgres          # Database username
PG_PASSWORD=              # Database password
```

### JWT Authentication
```env
JWT_SECRET=your-secret-key-here    # Change this in production!
JWT_EXP_MIN=120                    # Token expiration time in minutes
```

**Generate a strong JWT secret:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### AI Models & APIs

**Google Gemini (for AI responses)**
```env
GEMINI_API_KEY=your-api-key-here
```
Get from: https://ai.google.dev

**XAI Grok (alternative AI model)**
```env
XAI_API_KEY=your-api-key-here
```
Get from: https://console.x.ai

**Ollama (local LLM)**
```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
OLLAMA_API_KEY=                    # Leave empty for local
```

### Text-to-Speech (TTS)

**Fish Audio API**
```env
FISH_AUDIO_API_KEY=your-api-key-here
FISH_AUDIO_VOICE_ID=0              # Voice ID (0-9)
```

### Psychologist Feature
```env
ENABLE_PSYCHOLOGIST_FEATURE=True   # Enable/disable psychologist functionality
MAX_MESSAGE_HISTORY=100            # Max messages to load
MESSAGE_REFRESH_INTERVAL=3000      # Refresh interval in ms
AUTO_ASSIGN_PSYCHOLOGIST=False     # Auto-assign users to psychologists
```

### CORS Configuration
```env
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:8002,http://localhost:8002
```
Add URLs separated by commas for frontend origins that can make requests to API.

### Logging
```env
LOG_LEVEL=INFO                     # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE=app.log                   # Log file name
```

### Security
```env
SESSION_SECRET=your-session-secret-key
SESSION_TIMEOUT=3600               # Session timeout in seconds
FORCE_OFFLINE=False                # Force offline mode (uses JSON fallback)
```

### Features
```env
ENABLE_COMMUNITY_FEATURES=True     # Enable community features
ENABLE_TTS=True                    # Enable text-to-speech
ENABLE_VOICE_INPUT=True            # Enable voice input
```

---

## Supabase Setup Instructions

### 1. Create Supabase Project
1. Go to https://supabase.com
2. Click "New Project"
3. Enter project name and password
4. Copy the connection string

### 2. Get Your Database URL
1. Project Settings → Database
2. Connection String → Copy URI
3. Format: `postgresql://postgres:PASSWORD@HOST:PORT/postgres`

### 3. Run SQL Setup Queries
See `SUPABASE_SETUP.sql` for the schema queries to execute.

### 4. Update .env
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_PROJECT.supabase.co:5432/postgres
```

---

## Local Development Setup

### Quick Start
```bash
# 1. Create .env from template
cp .env.example .env

# 2. Edit .env with your values
nano .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

### For Local Database (without Supabase)
```env
FORCE_OFFLINE=True                 # Use JSON fallback
# Leave DATABASE_URL empty or commented out
```

---

## Production Deployment

### Security Checklist
```env
FLASK_ENV=production
FLASK_DEBUG=False
JWT_SECRET=<generate-strong-secret>
CORS_ORIGINS=https://yourdomain.com
```

### Vercel Deployment
1. Add environment variables in Vercel dashboard
2. Link your GitHub repository
3. Variables are automatically loaded from `.env`

### Render/Heroku Deployment
1. Add environment variables in dashboard
2. Or use CLI: `heroku config:set KEY=VALUE`

---

## Troubleshooting

### "Database Connection Error"
- Check `DATABASE_URL` format
- Verify Supabase project is running
- Check network connectivity

### "Token Invalid"
- Regenerate `JWT_SECRET`
- Check token expiration time

### "API Key Errors"
- Verify API key is correct
- Check API quota/limits
- Ensure API is enabled

### ".env not loading"
- Ensure `python-dotenv` is installed: `pip install python-dotenv`
- Restart the application
- Check `.env` file format (no spaces around `=`)

---

## Important Notes

⚠️ **Never commit `.env` to GitHub!**
- It contains sensitive credentials
- Always use `.env.example` as template
- Use `.gitignore` to prevent accidental commits

✅ **Security Best Practices**
- Rotate API keys regularly
- Use strong JWT secrets
- Keep dependencies updated
- Use HTTPS in production

---

## Next Steps

1. Copy `.env.example` to `.env`
2. Fill in your values (especially `DATABASE_URL` and API keys)
3. Run the database setup queries on Supabase
4. Test the application locally
5. Deploy to production with proper environment variables
