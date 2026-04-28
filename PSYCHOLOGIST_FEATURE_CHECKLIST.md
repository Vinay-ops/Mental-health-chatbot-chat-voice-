# Psychologist Feature - Setup Checklist

## ✅ What You Need to Do

### Phase 1: Local Setup
- [ ] Copy `.env.example` to `.env`
  ```bash
  cp .env.example .env
  ```
- [ ] Edit `.env` and fill in your values:
  - [ ] `DATABASE_URL` - Get from Supabase
  - [ ] `JWT_SECRET` - Generate a strong secret
  - [ ] API Keys (Gemini, XAI, etc.) - Only if you'll use them
  - [ ] Other configuration as needed

### Phase 2: Supabase Setup
- [ ] Create a Supabase project (https://supabase.com)
- [ ] Get your Database URL from Project Settings → Database → Connection String
- [ ] Copy the SQL queries from `SUPABASE_SETUP.sql`
- [ ] In Supabase SQL Editor:
  - [ ] Create new query
  - [ ] Paste all SQL from `SUPABASE_SETUP.sql`
  - [ ] Click Run
- [ ] Verify tables were created:
  - [ ] `users` table has `user_type` column
  - [ ] `psychologist_users` table exists
  - [ ] `direct_messages` table exists

### Phase 3: Test Locally
- [ ] Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Run the application:
  ```bash
  python app.py
  ```
- [ ] Test in browser:
  - [ ] Go to `http://localhost:8002/role-selection.html`
  - [ ] Click "User" - should go to login
  - [ ] Click "Psychologist" - should go to psychologist login
- [ ] Test Registration:
  - [ ] Register as user
  - [ ] Register as psychologist
  - [ ] Both should create accounts and redirect to their dashboards

### Phase 4: Test Features
- [ ] User Dashboard:
  - [ ] User can login
  - [ ] User can chat with AI
  - [ ] User can access community features
  
- [ ] Psychologist Dashboard:
  - [ ] Psychologist can login
  - [ ] Psychologist can see assigned users
  - [ ] Psychologist can send/receive messages
  - [ ] Messages persist in database

### Phase 5: Production Deployment
- [ ] Update `.env` with production values
- [ ] Set `FLASK_ENV=production`
- [ ] Set `FLASK_DEBUG=False`
- [ ] Deploy to your hosting (Vercel, Render, etc.)
- [ ] Add environment variables in deployment dashboard
- [ ] Verify all features work on production

---

## 📁 Files Created/Modified

### New Files Created:
- ✅ `role-selection.html` - Role selection page
- ✅ `psychologist-login.html` - Psychologist auth page
- ✅ `psychologist-dashboard.html` - Psychologist workspace
- ✅ `.env` - Your local configuration (NOT on GitHub)
- ✅ `.env.example` - Template for others
- ✅ `ENV_SETUP_GUIDE.md` - Detailed env variables guide
- ✅ `SUPABASE_SETUP.sql` - Database setup queries
- ✅ `PSYCHOLOGIST_FEATURE_CHECKLIST.md` - This file

### Files Modified:
- ✅ `app.py` - Added psychologist API endpoints
- ✅ `db.py` - Added psychologist database functions
- ✅ `.gitignore` - Already has `.env` (won't commit secrets)

---

## 🔑 Important Environment Variables

Minimum required for basic functionality:
```env
DATABASE_URL=postgresql://postgres:PASSWORD@PROJECT.supabase.co:5432/postgres
JWT_SECRET=generate-a-strong-secret-key
```

All variables are documented in `ENV_SETUP_GUIDE.md`

---

## 🚀 Quick Start Command

```bash
# 1. Setup env file
cp .env.example .env

# 2. Edit .env with your DATABASE_URL and JWT_SECRET

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run Supabase setup queries in your Supabase SQL Editor
# (Copy from SUPABASE_SETUP.sql)

# 5. Start the application
python app.py

# 6. Visit in browser
# http://localhost:8002/role-selection.html
```

---

## 🔒 Security Reminder

⚠️ **CRITICAL - DO NOT commit `.env` to GitHub!**

The `.gitignore` file already prevents this, but:
- ✅ `.env` is protected (not committed)
- ✅ `.env.example` is safe (no secrets)
- ✅ All secrets stored locally only

---

## 📞 Troubleshooting

### Cannot connect to database?
- [ ] Check `DATABASE_URL` format
- [ ] Verify Supabase project is active
- [ ] Test connection: `psql <DATABASE_URL>`

### Authentication errors?
- [ ] Check `JWT_SECRET` is set
- [ ] Clear browser localStorage
- [ ] Check browser console for errors

### Tables not found in Supabase?
- [ ] Run `SUPABASE_SETUP.sql` queries again
- [ ] Verify in Supabase SQL Editor they executed
- [ ] Check table browser in Supabase dashboard

### Features not working?
- [ ] Check `ENABLE_PSYCHOLOGIST_FEATURE=True` in `.env`
- [ ] Restart the Flask application
- [ ] Clear browser cache

---

## 📚 Documentation Files

1. **ENV_SETUP_GUIDE.md** - Complete environment variables reference
2. **SUPABASE_SETUP.sql** - Database queries for setup
3. **PSYCHOLOGIST_FEATURE_CHECKLIST.md** - This file (setup checklist)

---

## ✨ Next Steps After Setup

Once everything is working:

1. **Customize Configuration** - Adjust settings in `.env`
2. **Add Admin Panel** - To assign users to psychologists
3. **Add Notifications** - Email alerts for new messages
4. **Add Scheduling** - Calendar integration for appointments
5. **Add Analytics** - Track user-psychologist interactions

See the main README for feature ideas!

---

## Questions or Issues?

- Check `ENV_SETUP_GUIDE.md` for variable explanations
- Review `SUPABASE_SETUP.sql` for database setup
- Check browser console for client-side errors
- Check Flask logs for server-side errors

Good luck with your setup! 🚀
