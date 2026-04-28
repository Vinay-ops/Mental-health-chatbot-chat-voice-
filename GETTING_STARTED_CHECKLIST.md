# Mental Health Chatbot - Getting Started Checklist

## Phase 1: Installation & Setup

- [ ] **Install dependencies**
  ```bash
  pip install -r requirements.txt
  ```
  
- [ ] **Get Supabase credentials**
  - [ ] Go to https://app.supabase.com
  - [ ] Create new project or select existing
  - [ ] Go to Project Settings → Database
  - [ ] Copy the Connection String (PostgreSQL)
  
- [ ] **Create .env file**
  ```bash
  # Copy the template
  cp .env.example .env
  
  # Edit .env with your credentials
  DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@YOUR_HOST:5432/postgres
  
  # Add API keys (at least one for chat)
  GROQ_API_KEY=your_groq_key      # Recommended (free tier available)
  # OR
  GEMINI_API_KEY=your_gemini_key  # Google's API
  # OR
  OLLAMA_BASE_URL=http://127.0.0.1:11434  # Local Ollama
  ```

- [ ] **Set JWT secret**
  ```bash
  # Generate a random secret
  # On Mac/Linux:
  openssl rand -hex 32
  
  # On Windows PowerShell:
  [System.Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes(32) | ConvertTo-Hex
  
  # Add to .env:
  JWT_SECRET=<generated_secret>
  ```

## Phase 2: Database Setup

- [ ] **Initialize database schema**
  - [ ] Run the application: `python app.py`
  - [ ] Schema will auto-create on first run
  - [ ] Check if tables created in Supabase dashboard

- [ ] **Verify schema in Supabase**
  - [ ] Go to Supabase Dashboard → SQL Editor
  - [ ] Run verification query:
    ```sql
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
    ```
  - [ ] Should see: `users`, `chat_logs`, `community_posts`, `psychologist_users`, `direct_messages`, `chat_requests`

## Phase 3: Testing

- [ ] **Run quick start test**
  ```bash
  python quickstart_test.py
  ```
  - [ ] Server connectivity ✓
  - [ ] Debug endpoints ✓
  - [ ] User registration ✓
  - [ ] Psychologist registration ✓
  - [ ] Chat request workflow ✓
  - [ ] Direct messaging ✓

- [ ] **Manual API testing (Optional)**
  ```bash
  # Test debug endpoints
  curl http://localhost:8002/api/debug/users
  curl http://localhost:8002/api/debug/psychologists
  ```

## Phase 4: Frontend Integration

- [ ] **User Registration Page** ✓ (Already implemented)
  - [x] Login page works
  - [x] Register page has user/psychologist selection
  - [x] Form submits to `/api/register`
  - [x] Token stored in localStorage

- [ ] **Psychologist Dashboard** (To implement)
  - [ ] Shows pending chat requests
  - [ ] List of connected users
  - [ ] Accept/reject request buttons
  - [ ] Real-time request notifications

- [ ] **Chat Interface** (To implement)
  - [ ] Message history display
  - [ ] Send message input
  - [ ] Real-time message updates
  - [ ] User/psychologist indicators

- [ ] **Psychologist List Page** (To implement)
  - [ ] Show available psychologists
  - [ ] Send chat request button
  - [ ] Request status tracking

## Phase 5: Real-Time Features (Optional)

- [ ] **Polling (Simple)**
  ```javascript
  // Fetch messages every 2 seconds
  setInterval(async () => {
    const messages = await fetch('/api/messages/' + otherUserId);
    // Update UI with new messages
  }, 2000);
  ```

- [ ] **WebSockets (Advanced)**
  - [ ] Install: `pip install flask-socketio python-socketio`
  - [ ] Implement Socket.IO connection
  - [ ] Emit/receive messages in real-time
  - [ ] See SETUP_GUIDE.md for details

## Phase 6: Production Deployment

- [ ] **Environment Configuration**
  - [ ] Set `FLASK_ENV=production`
  - [ ] Use strong `JWT_SECRET`
  - [ ] Use HTTPS only
  - [ ] Hide .env from version control

- [ ] **Database**
  - [ ] Enable row-level security in Supabase
  - [ ] Set up database backups
  - [ ] Monitor performance with Supabase dashboard

- [ ] **Hosting Options**
  - [ ] Vercel (with `vercel.json` already configured)
  - [ ] Heroku
  - [ ] AWS EC2
  - [ ] Digital Ocean
  - [ ] Google Cloud Run

- [ ] **SSL/HTTPS**
  - [ ] Get SSL certificate
  - [ ] Configure HTTPS
  - [ ] Redirect HTTP to HTTPS

## Phase 7: Monitoring & Maintenance

- [ ] **Set up logging**
  - [ ] Monitor debug output
  - [ ] Check `local_db.json` for fallback data
  - [ ] Set up error alerts

- [ ] **Regular backups**
  - [ ] Supabase automatic backups ✓
  - [ ] Local JSON backup (in `local_db.json`)
  - [ ] Export user data periodically

- [ ] **Performance optimization**
  - [ ] Monitor database queries
  - [ ] Add caching if needed
  - [ ] Optimize asset delivery

## Troubleshooting Checklist

If things don't work:

- [ ] **Server won't start**
  - [ ] Check Python version: `python --version` (3.8+)
  - [ ] Check dependencies: `pip list | grep -i flask`
  - [ ] Check port 8002 is available
  - [ ] Check for syntax errors

- [ ] **Database connection fails**
  - [ ] Check DATABASE_URL in .env
  - [ ] Test connection: Verify URL format
  - [ ] Check Supabase project is active
  - [ ] Check network connectivity

- [ ] **Psychologist not appearing**
  - [ ] Run: `curl http://localhost:8002/api/debug/psychologists`
  - [ ] Check registration email
  - [ ] Verify `user_type='psychologist'` in database
  - [ ] Check for case sensitivity in email

- [ ] **Messages not saving**
  - [ ] Check `local_db.json` exists
  - [ ] Run: `curl http://localhost:8002/api/debug/users`
  - [ ] Verify Supabase tables exist
  - [ ] Check database permissions

- [ ] **Chat requests not working**
  - [ ] Verify both users registered
  - [ ] Check psychologist email format
  - [ ] Look in browser console for errors
  - [ ] Test with manual curl request

- [ ] **Real-time updates not working**
  - [ ] Polling: Check fetch frequency
  - [ ] WebSocket: Check socket connections
  - [ ] Check browser console for errors

## Success Indicators

You'll know everything is working when:

- ✅ Users can register (both regular and psychologist)
- ✅ Users can login and get tokens
- ✅ Psychologists appear in available list
- ✅ Chat requests can be sent
- ✅ Psychologists receive pending requests
- ✅ Requests can be accepted/rejected
- ✅ Direct messages sync properly
- ✅ Messages show in both directions
- ✅ No errors in console

## File Structure Reference

```
Mental-health-chatbot/
├── app.py                          # Flask app (✓ Complete)
├── db.py                          # Database layer (✓ Complete)
├── supabase_client.py            # Supabase integration (✓ Complete)
├── tts_service.py                # Text-to-speech (✓ Complete)
├── requirements.txt              # Dependencies (✓ Updated)
├── .env                          # Configuration (Need to create)
├── .env.example                  # Template (✓ Provided)
├── local_db.json                 # Fallback DB (Auto-created)
├── SETUP_GUIDE.md               # Detailed guide (✓ Created)
├── IMPLEMENTATION_SUMMARY.md     # What was done (✓ Created)
├── quickstart_test.py            # Test script (✓ Created)
├── GETTING_STARTED_CHECKLIST.md  # This file
├── templates/
│   ├── register.html             # (✓ Has psychologist toggle)
│   ├── login.html                # (✓ Complete)
│   ├── psychologist-dashboard.html  # (Needs real-time updates)
│   ├── psychologist-chat.html    # (Needs implementation)
│   └── ...
└── static/
    ├── css/
    │   └── style.css             # (✓ Complete)
    └── js/
        └── chat.js               # (Needs update for psychologist)
```

## Quick Start Commands

```bash
# Install
pip install -r requirements.txt

# Setup .env
cp .env.example .env
# Edit .env with your Supabase URL

# Run
python app.py

# Test (in another terminal)
python quickstart_test.py

# View local database
cat local_db.json

# Check Supabase (dashboard)
# Go to: https://app.supabase.com/project/[id]/editor
```

## Support Resources

- **Supabase Docs**: https://supabase.com/docs
- **Flask Docs**: https://flask.palletsprojects.com/
- **Groq API**: https://console.groq.com/
- **Project Issues**: Check `SETUP_GUIDE.md` Troubleshooting section

## Estimated Timeline

- **Phase 1**: 15 minutes (Installation)
- **Phase 2**: 5 minutes (Database setup - auto)
- **Phase 3**: 10 minutes (Testing)
- **Phase 4**: 30-60 minutes (Frontend integration)
- **Phase 5**: 30 minutes (Real-time features)
- **Phase 6**: 1-2 hours (Production deployment)
- **Phase 7**: Ongoing (Monitoring)

**Total**: 2-3 hours to full deployment

---

**You're all set! Follow this checklist and you'll have a fully functional Mental Health Chatbot with Supabase integration and psychologist support.**

Good luck! 🚀
