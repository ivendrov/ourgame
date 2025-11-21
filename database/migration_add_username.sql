-- Migration: Add discord_username to journal_entries table
-- This migration is for existing databases that need to be updated

-- Add the column (will be NULL for existing entries)
ALTER TABLE journal_entries
ADD COLUMN IF NOT EXISTS discord_username TEXT;

-- Backfill username from users table for existing entries
UPDATE journal_entries je
SET discord_username = u.discord_username
FROM users u
WHERE je.user_id = u.id
AND je.discord_username IS NULL;

-- Make the column NOT NULL after backfilling
ALTER TABLE journal_entries
ALTER COLUMN discord_username SET NOT NULL;
