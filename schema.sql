-- ====================================================================
-- UNIVERSAL LEARNING GAME — TELEGRAM USER MANAGEMENT SCHEMA
-- Compatible with Supabase PostgreSQL, Neon, Render, or any standard Postgres.
-- ====================================================================

CREATE TABLE IF NOT EXISTS telegram_users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_interaction_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_start_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    start_count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked'))
);

-- Indexes for lightning-fast queries and admin dashboard statistics
CREATE INDEX IF NOT EXISTS idx_telegram_users_status ON telegram_users(status);
CREATE INDEX IF NOT EXISTS idx_telegram_users_last_interaction ON telegram_users(last_interaction_at);
CREATE INDEX IF NOT EXISTS idx_telegram_users_registered_at ON telegram_users(registered_at);

-- Comments documenting column specifications
COMMENT ON TABLE telegram_users IS 'Stores registered Telegram bot users, engagement metrics, and status for Universal Learning Game.';
COMMENT ON COLUMN telegram_users.user_id IS 'Unique Telegram ID of the user (Primary Key).';
COMMENT ON COLUMN telegram_users.username IS 'Telegram handle (without @). Can be NULL if user has no username.';
COMMENT ON COLUMN telegram_users.first_name IS 'User first name as provided by Telegram.';
COMMENT ON COLUMN telegram_users.registered_at IS 'Timestamp of the first time user pressed /start.';
COMMENT ON COLUMN telegram_users.last_interaction_at IS 'Timestamp of the most recent interaction with the bot.';
COMMENT ON COLUMN telegram_users.last_start_at IS 'Timestamp of the most recent /start command invocation.';
COMMENT ON COLUMN telegram_users.start_count IS 'Total count of times the user has pressed /start (Daily START system).';
COMMENT ON COLUMN telegram_users.status IS 'Delivery status: active or blocked (if user blocks the bot).';
