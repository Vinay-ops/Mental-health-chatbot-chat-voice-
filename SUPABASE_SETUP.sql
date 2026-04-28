-- ============================================
-- SUPABASE DATABASE SETUP QUERIES
-- Mental Health Chatbot with Psychologist Feature
-- ============================================
-- Copy and paste these queries into Supabase SQL Editor
-- Run them in order (or all at once)
-- ============================================

-- 1. ALTER EXISTING USERS TABLE - Add user_type column
-- This adds the role distinction for users vs psychologists
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(50) DEFAULT 'user';

-- 2. CREATE PSYCHOLOGIST_USERS TABLE
-- Tracks which users are connected to which psychologists
CREATE TABLE IF NOT EXISTS psychologist_users (
    id SERIAL PRIMARY KEY,
    psychologist_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(psychologist_id, user_id)
);

-- 3. CREATE DIRECT_MESSAGES TABLE
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
AND table_name IN ('psychologist_users', 'direct_messages');

-- Check all indexes created
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('psychologist_users', 'direct_messages');

-- ============================================
-- CLEANUP (Run if you need to reset - BE CAREFUL!)
-- ============================================

-- Drop all psychologist-related tables and views
-- DROP VIEW IF EXISTS psychologist_clients CASCADE;
-- DROP FUNCTION IF EXISTS get_message_count(VARCHAR, VARCHAR) CASCADE;
-- DROP TABLE IF EXISTS direct_messages CASCADE;
-- DROP TABLE IF EXISTS psychologist_users CASCADE;
-- ALTER TABLE users DROP COLUMN IF EXISTS user_type;
