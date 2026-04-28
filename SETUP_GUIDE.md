# Mental Health Chatbot - Setup & Testing Guide

## Project Status
✅ **Supabase Integration Complete**
✅ **Real-time Database Sync**
✅ **Psychologist Registration Fixed**
✅ **Direct Messaging System Ready**
✅ **Chat Request System Ready**

## Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Supabase
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your Supabase credentials
# Get these from: https://app.supabase.com/project/[your-project-id]/settings/database
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
```

### 3. Setup Supabase Schema
Run these SQL queries in Supabase SQL Editor:

```sql
-- Users table with psychologist support
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(50) DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS specialization VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS license_number VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT;

-- Psychologist-User connections
CREATE TABLE IF NOT EXISTS psychologist_users (
    id SERIAL PRIMARY KEY,
    psychologist_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(psychologist_id, user_id)
);

-- Direct Messages
CREATE TABLE IF NOT EXISTS direct_messages (
    id SERIAL PRIMARY KEY,
    sender_id VARCHAR(255) NOT NULL,
    receiver_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_direct_messages
ON direct_messages (sender_id, receiver_id, created_at DESC);

-- Chat Requests
CREATE TABLE IF NOT EXISTS chat_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    psychologist_id VARCHAR(255) NOT NULL,
    message TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_requests_status
ON chat_requests (psychologist_id, status);
```

### 4. Run the Application
```bash
python app.py
```

Visit: http://localhost:8002

## Testing API Endpoints

### Debug Endpoints (No Auth Required)
```bash
# Check all users
curl http://localhost:8002/api/debug/users

# Check all psychologists
curl http://localhost:8002/api/debug/psychologists
```

### User Registration
```bash
# Register as User
curl -X POST http://localhost:8002/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "password123",
    "user_type": "user"
  }'

# Register as Psychologist
curl -X POST http://localhost:8002/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dr. Jane Smith",
    "email": "jane@example.com",
    "password": "password123",
    "user_type": "psychologist"
  }'
```

### User Login
```bash
curl -X POST http://localhost:8002/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "password123"
  }'

# Response includes: token, name, user_type
# Use token in Authorization header: Bearer <token>
```

### Get Available Psychologists (Requires Auth)
```bash
curl -X GET http://localhost:8002/api/psychologists/available \
  -H "Authorization: Bearer <USER_TOKEN>"
```

### Send Chat Request
```bash
curl -X POST http://localhost:8002/api/chat-request/send \
  -H "Authorization: Bearer <USER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "psychologist_id": "jane@example.com",
    "message": "I would like to chat with you about my anxiety"
  }'

# Response: { "success": true, "request_id": "uuid" }
```

### Get Pending Requests (Psychologist)
```bash
curl -X GET http://localhost:8002/api/psychologist/<PSYCHOLOGIST_EMAIL>/pending-requests \
  -H "Authorization: Bearer <PSYCHOLOGIST_TOKEN>"
```

### Accept Chat Request (Psychologist)
```bash
curl -X POST http://localhost:8002/api/chat-request/<REQUEST_ID>/accept \
  -H "Authorization: Bearer <PSYCHOLOGIST_TOKEN>"
```

### Send Direct Message
```bash
curl -X POST http://localhost:8002/api/messages/send \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "receiver_id": "jane@example.com",
    "message": "Hi, I wanted to follow up on our chat request"
  }'
```

### Get Direct Messages
```bash
curl -X GET http://localhost:8002/api/messages/<OTHER_USER_EMAIL> \
  -H "Authorization: Bearer <TOKEN>"
```

## Real-Time Features

### Message Sync
- Messages are saved to both **Supabase** and **Local JSON** simultaneously
- If Supabase is down, messages are queued in local JSON
- When Supabase comes back online, messages sync automatically

### Fallback System
```
Supabase (Primary) 
    ↓
Local JSON Fallback
    ↓
In-Memory Cache
```

## Database Schema Overview

### users
- `id` (PK): User ID
- `email` (UNIQUE): User email
- `password_hash`: Hashed password
- `name`: User's name
- `user_type`: 'user' or 'psychologist'
- `specialization`: Optional (psychologist field)
- `license_number`: Optional (psychologist field)
- `bio`: Optional profile bio
- `created_at`: Timestamp

### chat_requests
- `request_id` (UNIQUE): Request UUID
- `user_id`: User email
- `psychologist_id`: Psychologist email
- `message`: Initial message from user
- `status`: 'pending', 'accepted', 'rejected', 'cancelled'
- `created_at`: When request was made
- `updated_at`: Last status change

### direct_messages
- `id` (PK): Message ID
- `sender_id`: Sender email
- `receiver_id`: Receiver email
- `message`: Message content
- `is_read`: Read status
- `created_at`: When sent

## File Structure

```
app.py                          # Main Flask application
db.py                          # Database abstraction layer
supabase_client.py            # Supabase client with sync logic
tts_service.py                # Text-to-speech service
requirements.txt              # Python dependencies
local_db.json                 # Local JSON fallback (auto-created)
templates/
  ├── register.html           # Registration page (with psychologist option)
  ├── login.html              # Login page
  ├── psychologist-dashboard.html  # Psychologist dashboard
  ├── psychologist-chat.html   # Chat interface
  └── ...
static/
  ├── css/
  │   └── style.css
  └── js/
      └── chat.js
```

## Troubleshooting

### Psychologist not appearing in list
1. Check `/api/debug/users` to see all users
2. Verify `user_type` is 'psychologist' in database
3. Check `resolve_user_identifier()` in db.py

### Messages not syncing
1. Check Supabase connection: `DATABASE_URL` in .env
2. Verify `direct_messages` table exists in Supabase
3. Check browser console for errors
4. See `local_db.json` for local-only messages

### Chat requests not appearing
1. Run `/api/debug/psychologists` to check psychologist exists
2. Verify `chat_requests` table in Supabase
3. Check `resolve_user_identifier()` is normalizing emails correctly

### Login fails
1. Verify email is registered in Supabase
2. Check password is correct
3. Look for JWT_SECRET in .env

## Key Functions

### supabase_client.py
- `get_db_connection()`: Get Supabase connection
- `create_user()`: Register new user
- `get_user_by_email()`: Fetch user by email
- `save_direct_message()`: Save message to DB + JSON
- `get_direct_messages()`: Fetch conversation history
- `save_chat_request()`: Create chat request
- `get_pending_requests()`: Get pending for psychologist

### db.py
- `resolve_user_identifier()`: Convert ID to email (normalized)
- `get_available_psychologists()`: List all psychologists
- `create_chat_request()`: Create request with unique ID
- `update_chat_request_status()`: Accept/reject/cancel
- `get_accepted_chat_users()`: Get users for psychologist

## Performance Notes

1. **Message Caching**: In-memory session storage for active chats
2. **Database Indexing**: Indexes on `(sender_id, receiver_id, created_at)` for fast queries
3. **Pagination**: Limit results to prevent large transfers
4. **Connection Pooling**: Reuse database connections

## Security Considerations

1. **Passwords**: Hashed with bcrypt
2. **JWT**: 120-minute expiration (configurable)
3. **Email Normalization**: All emails lowercased to prevent duplicates
4. **User Isolation**: Users can only see own data

## Next Steps

1. **Frontend Implementation**:
   - Implement psychologist dashboard UI
   - Real-time message updates with polling or WebSockets
   - Chat request notifications

2. **Production Deployment**:
   - Use environment-based configuration
   - Set up proper error logging
   - Implement rate limiting
   - Add HTTPS/SSL
   - Use production database

3. **Advanced Features**:
   - Video chat integration (Twilio/Agora)
   - Message encryption
   - Read receipts
   - Typing indicators
   - User presence status
