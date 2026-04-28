-- ============================================
-- SUPABASE DATABASE SETUP QUERIES
-- Mental Health Chatbot with Psychologist Feature
-- ============================================
-- Copy and paste these queries into Supabase SQL Editor
-- Run them in order (or all at once)
-- ============================================

-- 1. ALTER EXISTING USERS TABLE - Add user_type column
-- This adds the role distinction for users vs psychologists
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    user_type VARCHAR(50) DEFAULT 'user',
    specialization VARCHAR(255),
    license_number VARCHAR(255),
    bio TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(50) DEFAULT 'user';

CREATE TABLE IF NOT EXISTS psychologist_users (
    id SERIAL PRIMARY KEY,
    psychologist_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(psychologist_id, user_id)
);

-- 3. CREATE CHAT_LOGS TABLE
-- Stores the main conversation history for each user session
CREATE TABLE IF NOT EXISTS chat_logs (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    ts TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_session
ON chat_logs (user_id, session_id);

-- 4. CREATE COMMUNITY_POSTS TABLE
-- Stores community support posts
CREATE TABLE IF NOT EXISTS community_posts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    name VARCHAR(255),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    likes INT DEFAULT 0
);

-- 5. CREATE CHAT_REQUESTS TABLE
-- Tracks pending and accepted psychologist connection requests
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

CREATE INDEX IF NOT EXISTS idx_chat_requests_status
ON chat_requests (psychologist_id, status);

-- 6. CREATE DIRECT_MESSAGES TABLE
-- Stores direct messages between psychologists and users
CREATE TABLE IF NOT EXISTS direct_messages (
    id SERIAL PRIMARY KEY,
    sender_id VARCHAR(255) NOT NULL,
    receiver_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. CREATE INDEXES for better performance
CREATE INDEX IF NOT EXISTS idx_direct_messages
ON direct_messages (sender_id, receiver_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_psychologist_users
ON psychologist_users (psychologist_id, status);

CREATE INDEX IF NOT EXISTS idx_messages_by_sender
ON direct_messages (sender_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_by_receiver
ON direct_messages (receiver_id, created_at DESC);

-- ============================================
-- OPTIONAL: View for easy querying
-- ============================================

-- Create a view to see psychologist-user relationships with names
CREATE OR REPLACE VIEW psychologist_clients AS
SELECT 
    pu.id,
    pu.psychologist_id,
    p.name AS psychologist_name,
    p.email AS psychologist_email,
    pu.user_id,
    u.name AS client_name,
    u.email AS client_email,
    pu.status,
    pu.created_at
FROM psychologist_users pu
LEFT JOIN users p ON pu.psychologist_id = p.id
LEFT JOIN users u ON pu.user_id = u.id;

-- ============================================
-- OPTIONAL: Statistics functions
-- ============================================

-- Get total messages between two users
CREATE OR REPLACE FUNCTION get_message_count(p_user1 VARCHAR, p_user2 VARCHAR)
RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*) FROM direct_messages
        WHERE (sender_id = p_user1 AND receiver_id = p_user2)
           OR (sender_id = p_user2 AND receiver_id = p_user1)
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- OPTIONAL: Sample data for testing
-- ============================================

-- Insert a sample psychologist user
-- INSERT INTO users (email, password_hash, name, user_type, created_at)
-- VALUES ('doctor@example.com', 'hashed_password_here', 'Dr. John Doe', 'psychologist', NOW());

-- Insert a sample regular user
-- INSERT INTO users (email, password_hash, name, user_type, created_at)
-- VALUES ('patient@example.com', 'hashed_password_here', 'Jane Smith', 'user', NOW());

-- ============================================
-- VERIFICATION QUERIES (Run these to verify setup)
-- ============================================

-- Check if user_type column exists
SELECT column_name FROM information_schema.columns 
WHERE table_name='users' AND column_name='user_type';

-- Count tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema='public' 
AND table_name IN ('users', 'chat_logs', 'community_posts', 'chat_requests', 'psychologist_users', 'direct_messages');

-- Count all required tables
SELECT table_name FROM information_schema.tables
WHERE table_schema='public'
AND table_name IN ('chat_logs', 'community_posts', 'chat_requests', 'psychologist_users', 'direct_messages');

-- Check all indexes created
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('chat_logs', 'chat_requests', 'psychologist_users', 'direct_messages');

-- ============================================
-- CLEANUP (Run if you need to reset - BE CAREFUL!)
-- ============================================

-- Drop all psychologist-related tables and views
-- DROP VIEW IF EXISTS psychologist_clients CASCADE;
-- DROP FUNCTION IF EXISTS get_message_count(VARCHAR, VARCHAR) CASCADE;
-- DROP TABLE IF EXISTS direct_messages CASCADE;
-- DROP TABLE IF EXISTS psychologist_users CASCADE;
-- ALTER TABLE users DROP COLUMN IF EXISTS user_type;
