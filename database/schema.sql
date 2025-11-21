-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discord_id BIGINT UNIQUE NOT NULL,
    discord_username TEXT NOT NULL,
    journal_channel_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Journal entries table
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    discord_id BIGINT NOT NULL,
    discord_username TEXT NOT NULL,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    message_id BIGINT UNIQUE NOT NULL,
    channel_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily stats table
CREATE TABLE IF NOT EXISTS daily_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    discord_id BIGINT NOT NULL,
    date DATE NOT NULL,
    total_words INTEGER DEFAULT 0,
    has_access BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_id ON journal_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_discord_id ON journal_entries(discord_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_created_at ON journal_entries(created_at);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);

-- Enable real-time for tables
ALTER TABLE users REPLICA IDENTITY FULL;
ALTER TABLE journal_entries REPLICA IDENTITY FULL;
ALTER TABLE daily_stats REPLICA IDENTITY FULL;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
